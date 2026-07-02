"""
Exit Research — Runner principal.

Ejecuta el pipeline completo:
  Fase 1: Backtest para cada variante (5k / 10k / 15k / 20k velas)
  Fase 2: Walk-Forward (usando WalkForwardTester existente)
  Fase 3: Monte Carlo (usando MonteCarlo existente)
  Fase 4: Stability Score compuesto
  Fase 5: Informe comparativo

Diseño de aislamiento:
  - La señal de entrada es detectada por EURUSDStrategy.detect_setup()
    SIN modificar la estrategia original.
  - Solo se sobreescribe el cálculo de SL/TP y la simulación de cierre.
  - No se toca rules_config.json ni ningún archivo de producción.
"""

from __future__ import annotations

import logging
import os
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import pandas as pd

from .variants import ALL_VARIANTS, ExitVariant, VARIANT_BY_NAME
from .metrics  import ExtendedMetrics, compute_metrics, monthly_consistency

logger = logging.getLogger(__name__)

# ── Configuración de los niveles de backtest ─────────────────────────────────
BACKTEST_LEVELS = [5_000, 10_000, 15_000, 20_000]

# ── Walk-Forward: ventanas fijas sobre el dataset de 20k velas ───────────────
WF_TRAIN      = 6_667   # velas de entrenamiento por ventana
WF_TEST       = 4_000   # velas de test por ventana
WF_STEP       = 4_000   # desplazamiento entre ventanas
WF_WINDOWS    = 4       # total de ventanas
WF_MIN_TRADES = 10      # mínimo de trades en TEST para que la ventana sea válida

# Severidad para determinar la "peor" clasificación:
#   OVERFITTED (peor) > UNSTABLE > MARGINAL > STABLE (mejor)
_WF_SEVERITY = {"OVERFITTED": 3, "UNSTABLE": 2, "MARGINAL": 1, "STABLE": 0}

# Configuración base de la estrategia de entrada (idéntica a producción)
ENTRY_CONFIG = {
    "ema_fast": 20,
    "ema_slow": 50,
    "ema_trend": 200,
    "ema_min_separation": 0.0001,
    "rsi_period": 14,
    "rsi_min": 38,
    "rsi_max": 62,
    "atr_period": 14,
    "price_ema_distance": 0.003,
    # sl_atr_multiplier y tp_atr_multiplier serán sobreescritos por cada variante
    "expires_minutes": 90,
}

RESULTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "backtest_results", "exit_research"
)

# ── Path isolation (Requirement 1.3) ─────────────────────────────────────────
ALLOWED_WRITE_ROOTS = [
    "core/exit_research/",
    "backtest_results/exit_research/",
]


def _assert_safe_path(path: str) -> None:
    """Raise PermissionError if *path* is outside the allowed write roots."""
    abs_path = os.path.abspath(path)
    if not any(abs_path.startswith(os.path.abspath(r)) for r in ALLOWED_WRITE_ROOTS):
        raise PermissionError(
            f"[ExitResearch] Write outside allowed paths attempted: {abs_path}"
        )


# ── Estructuras de resultado ──────────────────────────────────────────────────

@dataclass
class VariantResult:
    """Resultados de una variante a un nivel de velas."""
    variant_name:  str
    variant_label: str
    n_bars:        int
    metrics:       Optional[ExtendedMetrics] = None
    error:         Optional[str] = None


@dataclass
class ExitResearchReport:
    """Informe completo de todas las variantes."""
    run_id:    str
    timestamp: str
    symbol:    str = "EURUSD"
    results:   Dict[str, Dict[int, VariantResult]] = field(default_factory=dict)
    # {variant_name: {n_bars: VariantResult}}

    def best_by_stability(self) -> Optional[str]:
        """Devuelve el nombre de la variante con mayor Stability Score a 20k."""
        best_name  = None
        best_score = -1.0
        for name, levels in self.results.items():
            r = levels.get(20_000)
            if r and r.metrics and r.metrics.stability_score > best_score:
                best_score = r.metrics.stability_score
                best_name  = name
        return best_name

    def summary(self) -> str:
        """Genera el informe comparativo en texto."""
        lines = [
            "═" * 80,
            f"  EXIT RESEARCH — EURUSD Simple · {self.timestamp}",
            "═" * 80,
            "",
        ]

        # ── Tabla comparativa a 20k ───────────────────────────────────────────
        lines.append("  COMPARATIVA A 20.000 VELAS")
        lines.append("  " + "-" * 78)
        hdr = f"  {'Variante':<40} {'PF':>6} {'WR%':>6} {'Pips':>8} {'MaxDD':>8} {'Sharpe':>7} {'Stab':>6}"
        lines.append(hdr)
        lines.append("  " + "-" * 78)

        rows = []
        for name, levels in self.results.items():
            r = levels.get(20_000)
            if r and r.metrics:
                m = r.metrics
                rows.append((m.stability_score, m, r.variant_label))

        rows.sort(key=lambda x: x[0], reverse=True)

        for rank, (score, m, label) in enumerate(rows, 1):
            pf_str = f"{m.profit_factor:.2f}" if m.profit_factor != float("inf") else "∞"
            lines.append(
                f"  {rank:>2}. {label:<38} {pf_str:>6} {m.winrate:>5.1f}% "
                f"{m.total_pips:>8.1f} {m.max_drawdown:>8.1f} "
                f"{m.sharpe:>7.2f} {score:>5.1f}"
            )

        lines.append("")

        # ── Degradación entre niveles ─────────────────────────────────────────
        lines.append("  DEGRADACIÓN PF: 5k → 10k → 15k → 20k")
        lines.append("  " + "-" * 78)
        for name, levels in self.results.items():
            pfs = []
            for nb in BACKTEST_LEVELS:
                r = levels.get(nb)
                pf = r.metrics.profit_factor if (r and r.metrics) else None
                pf_str = f"{pf:.2f}" if pf and pf != float("inf") else ("∞" if pf == float("inf") else "—")
                pfs.append(pf_str)
            label = VARIANT_BY_NAME[name].label if name in VARIANT_BY_NAME else name
            lines.append(f"  {label:<40} {' → '.join(pfs)}")

        lines.append("")

        # ── Preguntas clave ───────────────────────────────────────────────────
        best = self.best_by_stability()
        if best and best in self.results:
            bm = self.results[best].get(20_000)
            if bm and bm.metrics:
                m = bm.metrics
                pf_str = f"{m.profit_factor:.2f}" if m.profit_factor != float("inf") else "∞"
                lines += [
                    "  VEREDICTO",
                    "  " + "-" * 78,
                    f"  • Más rentable:        {max(rows, key=lambda x: x[1].total_pips)[2]}",
                    f"  • Menor drawdown:      {min((r for _, r, _ in rows), key=lambda m: m.max_drawdown).variant_label}",
                    f"  • Más robusta (Stab):  {bm.variant_label}",
                    f"    PF={pf_str} | WR={m.winrate:.1f}% | MaxDD={m.max_drawdown:.0f}p | Sharpe={m.sharpe:.2f}",
                    f"    Stability Score: {m.stability_score:.1f}/100",
                    "",
                    "  Para operar durante años: la variante con mayor Stability Score,",
                    "  no necesariamente la de mayor PF.",
                ]

        lines.append("═" * 80)
        return "\n".join(lines)

    def to_dict(self) -> Dict:
        out: Dict = {"run_id": self.run_id, "timestamp": self.timestamp, "symbol": self.symbol, "results": {}}
        for name, levels in self.results.items():
            out["results"][name] = {}
            for nb, r in levels.items():
                out["results"][name][str(nb)] = {
                    "variant_name":  r.variant_name,
                    "variant_label": r.variant_label,
                    "n_bars":        r.n_bars,
                    "metrics":       r.metrics.to_dict() if r.metrics else None,
                    "error":         r.error,
                }
        return out


# ── Motor principal ───────────────────────────────────────────────────────────

class ExitResearchRunner:
    """
    Ejecuta el pipeline completo de investigación de salidas.

    Uso:
        runner = ExitResearchRunner()
        report = runner.run_all(bars=20000, save=True)
        print(report["symbol"])

    Parámetros:
        symbol:     Par a analizar (por defecto EURUSD)
        lookback:   Ventana de indicadores (velas)
        max_fwd:    Máximo de velas hacia adelante para simular cierre
        variants:   Lista de variantes (None = todas)
        levels:     Niveles de velas (None = [5k, 10k, 15k, 20k])
    """

    def __init__(
        self,
        symbol:   str  = "EURUSD",
        lookback: int  = 200,
        max_fwd:  int  = 300,
        variants: Optional[List[ExitVariant]] = None,
        levels:   Optional[List[int]] = None,
    ):
        self.symbol   = symbol
        self.lookback = lookback
        self.max_fwd  = max_fwd
        self.variants = variants or ALL_VARIANTS
        self.levels   = levels   or BACKTEST_LEVELS
        self._df_cache: Dict[int, pd.DataFrame] = {}

    # ── API pública ───────────────────────────────────────────────────────────

    def run_all(
        self,
        bars:    int  = 20_000,
        save:    bool = True,
        verbose: bool = True,
    ) -> dict:
        """
        Ejecuta todas las fases para todos los niveles.

        Si bars < max(levels), usa bars como nivel máximo.
        Retorna el diccionario del Research_Report.
        """
        run_id    = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        timestamp = datetime.now(timezone.utc).isoformat()
        report    = ExitResearchReport(run_id=run_id, timestamp=timestamp, symbol=self.symbol)

        # ── Phase 1: Download ─────────────────────────────────────────────────
        max_bars = max(self.levels)
        try:
            if verbose:
                logger.info(f"[ExitResearch] Descargando {self.lookback + max_bars} velas para {self.symbol}…")
            df_full = self._download_data(self.lookback + max_bars)
            if df_full is None:
                logger.error("[ExitResearch] No se pudo descargar datos. Abortando.")
                raise RuntimeError(
                    f"[ExitResearch] Data download failed for {self.symbol} at "
                    f"{datetime.now(timezone.utc).isoformat()}Z — no data returned."
                )

            # Req 3.3: verify minimum 20,200 bars before executing any level
            if len(df_full) < 20_200:
                msg = (
                    f"[ExitResearch] Insufficient data: {len(df_full)} bars "
                    f"(need >= 20,200). Aborting."
                )
                logger.error(msg)
                raise RuntimeError(msg)

            if verbose:
                logger.info(f"[ExitResearch] {len(df_full)} velas descargadas. Iniciando análisis…")
        except Exception as e:
            logger.error("[ExitResearch] Phase 'download' failed: %s", e, exc_info=True)
            raise

        # ── Phase 2: Backtest (per-variant/level errors stored, do NOT abort) ──
        # variant_trades almacena la lista cruda de trades del nivel máximo (20k)
        # para reutilizarla en Walk-Forward y Monte Carlo sin re-ejecutar variantes.
        variant_trades: Dict[str, List[_Trade]] = {}

        try:
            for variant in self.variants:
                report.results[variant.name] = {}
                for n_bars in self.levels:
                    # Req 3.8: skip level if insufficient bars for this level + lookback
                    available_bars = len(df_full)
                    if available_bars < n_bars + self.lookback:
                        logger.warning(
                            f"[ExitResearch] Skipping level {n_bars} for {variant.label}: "
                            f"only {available_bars} bars available (need {n_bars + self.lookback})."
                        )
                        continue
                    if verbose:
                        logger.info(f"[ExitResearch] Variante={variant.label} | bars={n_bars}")
                    try:
                        r, trades = self._run_variant(variant, df_full, n_bars, verbose=verbose)
                        report.results[variant.name][n_bars] = r
                        # Guardar lista de trades del nivel máximo para WF/MC
                        if n_bars == max(self.levels):
                            variant_trades[variant.name] = trades
                    except Exception as e:
                        logger.error(f"[ExitResearch] Error en {variant.name} / {n_bars}: {e}", exc_info=True)
                        report.results[variant.name][n_bars] = VariantResult(
                            variant_name=variant.name,
                            variant_label=variant.label,
                            n_bars=n_bars,
                            error=str(e),
                        )
        except Exception as e:
            logger.error("[ExitResearch] Phase 'backtest' failed: %s", e, exc_info=True)
            raise

        # ── Phase 3: Walk-Forward ────────────────────────────────────────────
        try:
            if verbose:
                logger.info("[ExitResearch] Ejecutando Walk-Forward…")
            self._run_walkforward(report, df_full, variant_trades, verbose=verbose)
        except Exception as e:
            logger.error("[ExitResearch] Phase 'walk_forward' failed: %s", e, exc_info=True)
            raise

        # ── Phase 4: Monte Carlo ─────────────────────────────────────────────
        try:
            if verbose:
                logger.info("[ExitResearch] Ejecutando Monte Carlo…")
            self._run_montecarlo(report, variant_trades, verbose=verbose)
        except Exception as e:
            logger.error("[ExitResearch] Phase 'monte_carlo' failed: %s", e, exc_info=True)
            raise

        # ── Phase 5: Stability Score + Report ───────────────────────────────
        try:
            self._update_stability_scores(report)
            report_dict = self._build_report_dict(report, run_id)
        except Exception as e:
            logger.error("[ExitResearch] Phase 'stability_report' failed: %s", e, exc_info=True)
            raise

        # ── Guardar ───────────────────────────────────────────────────────────
        if save:
            try:
                self._save(report_dict, run_id)
            except (OSError, PermissionError) as e:
                logger.error(f"[ExitResearch] JSON export failed: {e}")

        return report_dict

    # ── Hot-reload helper (Requirement 1.4) ──────────────────────────────────

    def _get_eurusd_strategy(self):
        """
        Reimports strategies.eurusd on every call so that external edits to
        strategies/eurusd.py are picked up without restarting the process.

        On ImportError or SyntaxError: logs the exception with the file path
        and re-raises so the caller receives a non-zero exit (Req 1.4).
        """
        import importlib, sys
        try:
            if "strategies.eurusd" in sys.modules:
                importlib.reload(sys.modules["strategies.eurusd"])
            from strategies.eurusd import EURUSDStrategy
            return EURUSDStrategy()
        except (ImportError, SyntaxError) as e:
            import inspect
            try:
                mod = sys.modules.get("strategies.eurusd")
                fpath = inspect.getfile(mod) if mod else "strategies/eurusd.py"
            except Exception:
                fpath = "strategies/eurusd.py"
            logger.error(
                f"[ExitResearch] Failed to import strategies.eurusd ({fpath}): {e}",
                exc_info=True,
            )
            raise

    # ── Backtest de una variante ──────────────────────────────────────────────

    def _run_variant(
        self,
        variant: ExitVariant,
        df_full: pd.DataFrame,
        n_bars:  int,
        verbose: bool = False,
    ) -> tuple[VariantResult, List["_Trade"]]:
        """
        Detecta señales con EURUSDStrategy (sin modificarla) y simula
        el cierre con la variante de salida.

        Returns:
            (VariantResult, list[_Trade]) — el resultado y la lista cruda de
            trades para uso en Walk-Forward y Monte Carlo.
        """
        strategy = self._get_eurusd_strategy()

        df_full = df_full.reset_index(drop=True)
        total   = len(df_full)
        max_idx = min(self.lookback + n_bars, total)

        trades = []
        t0 = time.time()

        for i in range(self.lookback, max_idx):
            window = df_full.iloc[max(0, i - self.lookback): i].copy()
            if len(window) < 50:
                continue

            try:
                window = strategy.add_indicators(window, ENTRY_CONFIG)
                signal = strategy.detect_setup(window, ENTRY_CONFIG)
            except Exception:
                continue

            if not signal:
                continue

            entry     = float(signal["entry"])
            direction = str(signal["type"])
            last_row  = window.iloc[-1]
            atr       = float(last_row.get("atr", 0.0010))

            # Calcular niveles con la variante
            sl, tp = variant.compute_levels(entry, direction, atr, window)

            # Simular cierre
            exit_res = variant.simulate_exit(
                entry=entry,
                sl=sl,
                tp=tp,
                direction=direction,
                df_full=df_full,
                start_index=i,
                atr_at_entry=atr,
            )

            # partial_close returns list[ExitResult] (two records per signal);
            # all other variants return a single ExitResult.
            if isinstance(exit_res, list):
                for res in exit_res:
                    trades.append(_Trade(
                        result=res.result,
                        profit_pips=res.profit_pips,
                        bar_index=i,
                        exit_bar=res.exit_bar,
                    ))
            else:
                trades.append(_Trade(
                    result=exit_res.result,
                    profit_pips=exit_res.profit_pips,
                    bar_index=i,
                    exit_bar=exit_res.exit_bar,
                ))

        elapsed = time.time() - t0
        if verbose:
            logger.info(
                f"  → {len(trades)} trades en {elapsed:.1f}s | "
                f"WIN={sum(1 for t in trades if t.result=='WIN')} "
                f"LOSS={sum(1 for t in trades if t.result=='LOSS')}"
            )

        metrics = compute_metrics(
            variant_name=variant.name,
            variant_label=variant.label,
            n_bars=n_bars,
            trades=trades,
        )

        # Consistencia mensual
        mc_data = monthly_consistency(trades, n_bars)
        metrics.monthly_pf_std = mc_data.get("pf_std")

        return VariantResult(
            variant_name=variant.name,
            variant_label=variant.label,
            n_bars=n_bars,
            metrics=metrics,
        ), trades

    # ── Walk-Forward ──────────────────────────────────────────────────────────

    @staticmethod
    def _compute_pf(trades: "List[_Trade]") -> float:
        """
        Compute Profit Factor from a list of _Trade objects.

        Returns float('inf') if there are winning trades but no losses,
        0.0 if there are no winning trades, or the ratio gross_win/gross_loss.
        PENDING trades are excluded automatically (profit_pips == 0 from PENDING
        results are not a win so they fall through to gross_loss = 0 edge case,
        but we filter them explicitly to match the spec).
        """
        closed = [t for t in trades if t.result in ("WIN", "LOSS")]
        gross_win  = sum(t.profit_pips for t in closed if t.profit_pips > 0)
        gross_loss = abs(sum(t.profit_pips for t in closed if t.profit_pips <= 0))
        if gross_loss == 0:
            return float("inf") if gross_win > 0 else 0.0
        return gross_win / gross_loss

    def _run_walkforward(
        self,
        report:         ExitResearchReport,
        df_full:        pd.DataFrame,
        variant_trades: dict,
        verbose:        bool = False,
    ):
        """
        Walk-Forward with 4 fixed windows over the 20k-bar dataset.

        Window layout (bar indices into the 20k dataset, i.e. excluding lookback):
          Window 0: TRAIN [0,    6667)  TEST [6667,  10667)
          Window 1: TRAIN [4000, 10667) TEST [10667, 14667)
          Window 2: TRAIN [8000, 14667) TEST [14667, 18667)
          Window 3: TRAIN [12000,18667) TEST [18667, end)

        Trades are sliced by bar_index from the pre-computed variant_trades dict.
        No re-execution of _run_variant is needed.

        wf_stability is the WORST classification across all valid windows,
        using severity: OVERFITTED (3) > UNSTABLE (2) > MARGINAL (1) > STABLE (0).
        """
        # Fixed window boundaries (bar indices into the 20k-bar slice, NOT df_full)
        # The 20k slice starts at self.lookback inside df_full.
        # bar_index values stored in _Trade are absolute indices into df_full,
        # so we offset them by self.lookback when comparing.
        lookback = self.lookback

        # Window definitions as (train_start, train_end, test_start, test_end)
        # expressed as offsets within the 20k dataset (0-based, bar_index - lookback)
        windows = [
            (0,      WF_TRAIN,             WF_TRAIN,              WF_TRAIN + WF_TEST),   # 0
            (WF_STEP,     WF_STEP + WF_TRAIN,   WF_STEP + WF_TRAIN,    WF_STEP + WF_TRAIN + WF_TEST),  # 1
            (2*WF_STEP,   2*WF_STEP + WF_TRAIN, 2*WF_STEP + WF_TRAIN,  2*WF_STEP + WF_TRAIN + WF_TEST),  # 2
            (3*WF_STEP,   3*WF_STEP + WF_TRAIN, 3*WF_STEP + WF_TRAIN,  None),  # 3: test end = dataset end
        ]
        # Verify the hard-coded values match the spec:
        # Window 0: TRAIN [0,6667)  TEST [6667,10667)
        # Window 1: TRAIN [4000,10667)  TEST [10667,14667)
        # Window 2: TRAIN [8000,14667)  TEST [14667,18667)
        # Window 3: TRAIN [12000,18667) TEST [18667, end)
        # With WF_TRAIN=6667, WF_TEST=4000, WF_STEP=4000 these hold exactly.

        max_bars = max(self.levels)

        for variant in self.variants:
            r = report.results.get(variant.name, {}).get(max_bars)
            if not r or r.error or not r.metrics:
                continue

            trades_all = variant_trades.get(variant.name)
            if not trades_all:
                continue

            try:
                window_classifications = []
                valid_pf_tests = []

                for w_idx, (tr_s, tr_e, te_s, te_e) in enumerate(windows):
                    # Convert dataset-relative offsets to absolute bar_index values
                    abs_tr_s = lookback + tr_s
                    abs_tr_e = lookback + tr_e
                    abs_te_s = lookback + te_s
                    abs_te_e = (lookback + te_e) if te_e is not None else None

                    # Slice trades by bar_index
                    train_trades = [
                        t for t in trades_all
                        if abs_tr_s <= t.bar_index < abs_tr_e
                    ]
                    if abs_te_e is not None:
                        test_trades = [
                            t for t in trades_all
                            if abs_te_s <= t.bar_index < abs_te_e
                        ]
                    else:
                        test_trades = [
                            t for t in trades_all
                            if t.bar_index >= abs_te_s
                        ]

                    # Count only closed TEST trades for WF_MIN_TRADES check
                    closed_test = [t for t in test_trades if t.result in ("WIN", "LOSS")]
                    if len(closed_test) < WF_MIN_TRADES:
                        if verbose:
                            logger.info(
                                f"  WF {variant.label} window {w_idx}: "
                                f"INSUFFICIENT ({len(closed_test)} test trades < {WF_MIN_TRADES})"
                            )
                        continue  # skip this window (don't include in valid set)

                    pf_train = self._compute_pf(train_trades)
                    pf_test  = self._compute_pf(test_trades)
                    degradation = pf_train - pf_test

                    # Classification priority order (bug fix): OVERFITTED checked first
                    if pf_train >= 1.3 and pf_test < 1.0:
                        classification = "OVERFITTED"
                    elif pf_test >= 1.2 and degradation < 0.3:
                        classification = "STABLE"
                    elif pf_test >= 1.0 and degradation < 0.6:
                        classification = "MARGINAL"
                    else:
                        classification = "UNSTABLE"

                    window_classifications.append(classification)
                    valid_pf_tests.append(pf_test)

                    if verbose:
                        logger.info(
                            f"  WF {variant.label} window {w_idx}: {classification} "
                            f"(pf_train={pf_train:.2f} pf_test={pf_test:.2f} "
                            f"deg={degradation:.2f} test_trades={len(closed_test)})"
                        )

                # Determine overall wf_stability
                if not window_classifications:
                    # All windows insufficient
                    wf_stability = "UNSTABLE"
                else:
                    # Worst classification by severity
                    wf_stability = max(
                        window_classifications,
                        key=lambda c: _WF_SEVERITY[c],
                    )

                r.metrics.wf_stability = wf_stability

                if verbose:
                    avg_pf_test = (sum(valid_pf_tests) / len(valid_pf_tests)) if valid_pf_tests else 0.0
                    logger.info(
                        f"  WF {variant.label}: overall={wf_stability} "
                        f"valid_windows={len(window_classifications)} "
                        f"avg_pf_test={avg_pf_test:.2f}"
                    )

            except Exception as e:
                logger.warning(f"[WF] Error en {variant.name}: {e}", exc_info=True)

    # ── Monte Carlo ───────────────────────────────────────────────────────────

    def _run_montecarlo(
        self,
        report:         ExitResearchReport,
        variant_trades: dict,
        verbose:        bool = False,
    ):
        """Ejecuta Monte Carlo sobre los trades del nivel máximo.

        Para cada variante:
          - Usa bootstrap (with_replacement=True) con 2000 simulaciones y seed=42
          - Calcula un ruin_threshold variant-specific: -50% del total de profit_pips
            de la secuencia original
          - Escribe mc_prob_ruin y mc_prob_profit en ExtendedMetrics
        """
        try:
            from core.montecarlo import MonteCarlo, TradeRecord
        except ImportError:
            logger.warning("[MC] core.montecarlo no disponible — saltando MC")
            return

        max_bars = max(self.levels)

        for variant in self.variants:
            r = report.results.get(variant.name, {}).get(max_bars)
            if not r or r.error or not r.metrics:
                continue

            trades = variant_trades.get(variant.name)
            if not trades:
                # Variante sin trades: dejar los campos MC como None
                continue

            # Solo trades cerrados (excluir PENDING) para el cálculo MC
            closed_trades = [t for t in trades if t.result in ("WIN", "LOSS")]
            if not closed_trades:
                continue

            try:
                # Calcular umbral de ruina variant-specific: -50% del total pips original
                total_profit_pips_original = sum(t.profit_pips for t in closed_trades)
                ruin_threshold = -0.50 * abs(total_profit_pips_original)

                # Construir lista de TradeRecord para el motor MC
                trade_records = [
                    TradeRecord(
                        profit_pips=t.profit_pips,
                        result=t.result,
                        symbol=self.symbol,
                    )
                    for t in closed_trades
                ]

                # Instanciar MonteCarlo con seed=42 para reproducibilidad (Req 5.3)
                mc = MonteCarlo(
                    n_simulations=2000,
                    with_replacement=True,
                    ruin_threshold=ruin_threshold,
                    seed=42,
                )

                mc_report = mc.run(trade_records, symbol=self.symbol)

                # Escribir resultados en ExtendedMetrics (Req 5.2)
                r.metrics.mc_prob_ruin   = mc_report.prob_ruin
                r.metrics.mc_prob_profit = mc_report.prob_profitable

                if verbose:
                    logger.info(
                        f"  MC {variant.label}: "
                        f"prob_ruin={mc_report.prob_ruin:.1%} "
                        f"prob_profit={mc_report.prob_profitable:.1%} "
                        f"ruin_threshold={ruin_threshold:.1f} pips "
                        f"n_trades={len(closed_trades)}"
                    )

            except Exception as e:
                logger.warning(f"[MC] Error en {variant.name}: {e}", exc_info=True)

    # ── Actualizar Stability Score ────────────────────────────────────────────

    def _update_stability_scores(self, report: ExitResearchReport):
        """Recalcula el Stability Score con datos WF/MC ahora disponibles."""
        from .metrics import _stability_score
        max_bars = max(self.levels)
        for variant in self.variants:
            r = report.results.get(variant.name, {}).get(max_bars)
            if not r or r.error or not r.metrics:
                continue
            m = r.metrics
            # Recompute stability score with WF/MC data now available
            m.stability_score = _stability_score(m)  # includes MC penalty
            # Apply OVERFITTED penalty: -10 points, floor 0 (Requirement 7.4)
            if m.wf_stability == "OVERFITTED":
                m.stability_score = max(0.0, m.stability_score - 10.0)

    # ── Construir dict del informe ────────────────────────────────────────────

    @staticmethod
    def _sanitize_floats(obj: Any) -> Any:
        """
        Recursively replace non-JSON-compliant float values (inf, -inf, nan)
        with None so that json.dumps never emits bare ``Infinity`` / ``NaN``.
        """
        import math
        if isinstance(obj, float):
            if math.isinf(obj) or math.isnan(obj):
                return None
            return obj
        if isinstance(obj, dict):
            return {k: ExitResearchRunner._sanitize_floats(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [ExitResearchRunner._sanitize_floats(v) for v in obj]
        return obj

    def _build_report_dict(self, report: ExitResearchReport, run_id: str) -> dict:
        """
        Construye el diccionario del Research_Report según el esquema de la
        sección 3.4 del design.md (Requirements 8.1, 8.2, 8.3, 8.5, 10.3).

        Incluye: run_id, generated_at, symbol, validation_mode,
                 comparison_table, degradation_table, conclusions, results.

        JSON-safety: all non-finite float values (inf, -inf, nan) are
        converted to null so the output is always valid JSON.
        """
        max_bars = max(self.levels)
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # ── Métricas a nivel máximo para tablas de comparación/conclusiones ──
        metrics_at_max: Dict[str, ExtendedMetrics] = {}
        for name, levels in report.results.items():
            r = levels.get(max_bars)
            if r and r.metrics:
                metrics_at_max[name] = r.metrics

        # ── comparison_table ─────────────────────────────────────────────────
        comparison_rows = []
        for name, m in metrics_at_max.items():
            pf = m.profit_factor if m.profit_factor != float("inf") else None
            comparison_rows.append({
                "variant":         name,
                "profit_factor":   pf,
                "winrate":         round(m.winrate, 4),
                "total_pips":      round(m.total_pips, 4),
                "max_drawdown":    round(m.max_drawdown, 4),
                "sharpe":          round(m.sharpe, 4),
                "stability_score": m.stability_score,
            })

        # Sort: descending stability_score, tiebreak ascending max_drawdown
        comparison_rows.sort(
            key=lambda x: (-x["stability_score"], x["max_drawdown"])
        )
        for rank, row in enumerate(comparison_rows, 1):
            row["rank"] = rank
        # Reorder fields to match spec
        comparison_table = [
            {
                "rank":            r["rank"],
                "variant":         r["variant"],
                "profit_factor":   r["profit_factor"],
                "winrate":         r["winrate"],
                "total_pips":      r["total_pips"],
                "max_drawdown":    r["max_drawdown"],
                "sharpe":          r["sharpe"],
                "stability_score": r["stability_score"],
            }
            for r in comparison_rows
        ]

        # ── degradation_table ────────────────────────────────────────────────
        degradation_table: Dict[str, Dict[str, Any]] = {}
        for name, levels in report.results.items():
            degradation_table[name] = {}
            for nb in self.levels:
                r = levels.get(nb)
                if r and r.metrics:
                    pf = r.metrics.profit_factor
                    degradation_table[name][str(nb)] = pf if pf != float("inf") else None
                else:
                    degradation_table[name][str(nb)] = None

        # ── conclusions ──────────────────────────────────────────────────────
        conclusions: Dict[str, Optional[str]] = {
            "highest_profit":          None,
            "lowest_drawdown":         None,
            "most_robust":             None,
            "best_walk_forward":       None,
            "lowest_ruin_probability": None,
            "recommended_for_live":    None,
        }

        if metrics_at_max:
            # highest_profit: max total_pips; tiebreak max winrate
            conclusions["highest_profit"] = max(
                metrics_at_max,
                key=lambda n: (metrics_at_max[n].total_pips, metrics_at_max[n].winrate),
            )

            # lowest_drawdown: min max_drawdown; tiebreak max recovery_factor
            def _rf_key(n: str) -> float:
                rf = metrics_at_max[n].recovery_factor
                return rf if rf != float("inf") else 1e9

            conclusions["lowest_drawdown"] = min(
                metrics_at_max,
                key=lambda n: (metrics_at_max[n].max_drawdown, -_rf_key(n)),
            )

            # most_robust: max stability_score; tiebreak min max_drawdown
            conclusions["most_robust"] = max(
                metrics_at_max,
                key=lambda n: (metrics_at_max[n].stability_score, -metrics_at_max[n].max_drawdown),
            )

            # best_walk_forward: STABLE variants only → max stability_score; tiebreak min max_drawdown
            stable_names = [n for n, m in metrics_at_max.items() if m.wf_stability == "STABLE"]
            if stable_names:
                conclusions["best_walk_forward"] = max(
                    stable_names,
                    key=lambda n: (metrics_at_max[n].stability_score, -metrics_at_max[n].max_drawdown),
                )

            # lowest_ruin_probability: min mc_prob_ruin; tiebreak max mc_prob_profit
            ruin_names = [n for n, m in metrics_at_max.items() if m.mc_prob_ruin is not None]
            if ruin_names:
                conclusions["lowest_ruin_probability"] = min(
                    ruin_names,
                    key=lambda n: (
                        metrics_at_max[n].mc_prob_ruin,
                        -(metrics_at_max[n].mc_prob_profit or 0.0),
                    ),
                )

            # recommended_for_live: max stability_score among pf > 1.0; tiebreak min max_drawdown
            live_names = [
                n for n, m in metrics_at_max.items()
                if m.profit_factor is not None and m.profit_factor > 1.0
            ]
            if live_names:
                conclusions["recommended_for_live"] = max(
                    live_names,
                    key=lambda n: (metrics_at_max[n].stability_score, -metrics_at_max[n].max_drawdown),
                )

        # ── results section ──────────────────────────────────────────────────
        # Sanitize non-finite floats (inf, -inf, nan) → None for JSON compliance
        results_section: Dict[str, Dict[str, Any]] = {}
        for name, levels in report.results.items():
            results_section[name] = {}
            for nb, r in levels.items():
                raw_metrics = r.metrics.to_dict() if r.metrics else None
                results_section[name][str(nb)] = {
                    "metrics": self._sanitize_floats(raw_metrics),
                    "error":   r.error,
                }

        return self._sanitize_floats({
            "run_id":            run_id,
            "generated_at":      generated_at,
            "symbol":            report.symbol,
            "validation_mode":   "no_optimization",
            "comparison_table":  comparison_table,
            "degradation_table": degradation_table,
            "conclusions":       conclusions,
            "results":           results_section,
        })

    # ── Descarga de datos ────────────────────────────────────────────────────

    def _download_data(self, total_bars: int) -> Optional[pd.DataFrame]:
        try:
            from mt5_client import get_candles, initialize as mt5_init
            import MetaTrader5 as mt5
            mt5_init()
            df = get_candles(self.symbol, mt5.TIMEFRAME_H1, total_bars)
            if df is not None and len(df) > 0:
                return df.reset_index(drop=True)
        except Exception as e:
            logger.error(
                f"[ExitResearch] Download failed for {self.symbol} at "
                f"{datetime.now(timezone.utc).isoformat()}Z: {e}"
            )
            raise RuntimeError(
                f"[ExitResearch] Download failed for {self.symbol} at "
                f"{datetime.now(timezone.utc).isoformat()}Z: {e}"
            ) from e
        return None

    # ── Guardar resultados ────────────────────────────────────────────────────

    def _save(self, report_dict: dict, run_id: str) -> str:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        path = os.path.join(RESULTS_DIR, f"exit_research_{run_id}.json")
        # Task 9.3: guard against writes outside allowed directories (Req 1.3)
        _assert_safe_path(path)
        # Task 9.2: handle export failure gracefully — log error, do NOT re-raise (Req 8.6)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report_dict, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"[ExitResearch] Reporte guardado: {path}")
        except (OSError, PermissionError) as e:
            logger.error(f"[ExitResearch] JSON export failed at {path}: {e}")
        return path


# ── Trade auxiliar ─────────────────────────────────────────────────────────────

class _Trade:
    """Objeto mínimo compatible con compute_metrics."""
    __slots__ = ("result", "profit_pips", "bar_index", "exit_bar")

    def __init__(self, result, profit_pips, bar_index, exit_bar):
        self.result      = result
        self.profit_pips = profit_pips
        self.bar_index   = bar_index
        self.exit_bar    = exit_bar


# ── Nota: run_exit_research() se define en core/exit_research/__init__.py ──────
