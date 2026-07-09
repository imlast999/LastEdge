"""
run_exit_research.py — Exit Research para estrategias EURUSD activas

Uso:
    python run_exit_research.py
    python run_exit_research.py --bars 10000    # análisis rápido
    python run_exit_research.py --bars 20000    # completo (recomendado)

NO modifica ninguna estrategia, parámetro ni configuración.
Solo produce evidencia cuantitativa en backtest_results/exit_research/
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────
RULES_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "rules_config.json")
RESULTS_BASE      = os.path.join(os.path.dirname(__file__), "backtest_results", "exit_research")

# Estrategias EURUSD descartadas — se excluyen automáticamente
DISCARDED_EURUSD = {
    "eurusd_asian_breakout": "PF < 1.0 en 10k/15k/20k (retest progresivo jun 2026)",
    "eurusd_mtf":            "PF máximo 0.42 (grid search may 2026)",
    "eurusd_advanced":       "Fallback no activo en producción",
}


# ── Detectar estrategias EURUSD activas ──────────────────────────────────────

def get_active_eurusd_strategies() -> List[Dict[str, Any]]:
    """
    Lee rules_config.json y devuelve la lista de estrategias EURUSD activas,
    excluyendo descartadas/experimentales.

    Returns:
        Lista de dicts con keys: name, sl_mult, tp_mult, label, source
    """
    try:
        with open(RULES_CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        logger.error("No se pudo leer rules_config.json: %s", e)
        sys.exit(1)

    eurusd_cfg = cfg.get("EURUSD", {})
    if not eurusd_cfg.get("enabled", True):
        logger.warning("EURUSD está desactivado en rules_config.json")
        return []

    primary   = eurusd_cfg.get("strategy", "eurusd_simple")
    sl_mult   = eurusd_cfg.get("sl_atr_multiplier", 1.5)
    tp_mult   = eurusd_cfg.get("tp_atr_multiplier", 6.0)

    strategies = []

    # Estrategia principal
    if primary not in DISCARDED_EURUSD:
        strategies.append({
            "name":    primary,
            "sl_mult": sl_mult,
            "tp_mult": tp_mult,
            "label":   f"{primary} (producción)",
            "source":  "rules_config.json › EURUSD.strategy",
        })
    else:
        logger.warning("Estrategia principal EURUSD '%s' marcada como descartada: %s",
                       primary, DISCARDED_EURUSD[primary])

    return strategies


def print_strategy_audit(strategies: List[Dict], discarded: Dict) -> None:
    """Imprime el audit de estrategias incluidas y excluidas."""
    print()
    print("=" * 72)
    print("  AUDIT DE ESTRATEGIAS EURUSD")
    print("=" * 72)
    print()
    print("  INCLUIDAS:")
    for s in strategies:
        rr = s["tp_mult"] / s["sl_mult"] if s["sl_mult"] > 0 else 0
        print(f"    OK  {s['name']:<30} SL={s['sl_mult']}xATR  TP={s['tp_mult']}xATR  (RR~1:{rr:.1f})")
        print(f"        Fuente: {s['source']}")
    print()
    print("  EXCLUIDAS (descartadas / no activas en producción):")
    for name, reason in discarded.items():
        print(f"    NO  {name:<30} {reason}")
    print()


# ── Crear variante "Current Production Exit" ─────────────────────────────────

def build_production_variant(sl_mult: float, tp_mult: float):
    """
    Construye una variante RR fijo que replica exactamente los parámetros
    de producción de rules_config.json.
    Aparece en los resultados como 'current_production'.
    """
    from core.exit_research.variants import ExitVariant, ExitResult, _net_pips, _calc_mae_mfe
    from typing import Optional, Tuple
    import pandas as pd

    PIP = 0.0001

    class CurrentProductionExit(ExitVariant):
        name  = "current_production"
        label = "Current Production Exit"

        def compute_levels(self, entry, direction, atr, df_window):
            sl_dist = atr * sl_mult
            tp_dist = atr * tp_mult
            if direction == "BUY":
                return entry - sl_dist, entry + tp_dist
            return entry + sl_dist, entry - tp_dist

    return CurrentProductionExit()


# ── Runner principal ──────────────────────────────────────────────────────────

def run_research_for_strategy(
    strategy_info: Dict,
    bars: int,
    verbose: bool,
) -> Dict:
    """
    Ejecuta el pipeline completo de Exit Research para una estrategia.
    Devuelve el report_dict con todos los resultados.
    """
    from core.exit_research.runner      import ExitResearchRunner
    from core.exit_research.variants    import ALL_VARIANTS
    from core.exit_research.strategy_adapter import StrategyAdapter

    strategy_name = strategy_info["name"]
    sl_mult       = strategy_info["sl_mult"]
    tp_mult       = strategy_info["tp_mult"]

    logger.info("Cargando estrategia: %s", strategy_name)
    try:
        from strategies.eurusd import EURUSDStrategy
        base_strategy = EURUSDStrategy()
    except Exception as e:
        logger.error("No se pudo instanciar %s: %s", strategy_name, e)
        raise

    # Leer config de producción pero dejar que las variantes sobreescriban sl/tp
    prod_config = base_strategy._get_default_config()
    # Actualizar con los valores reales de rules_config.json
    prod_config["sl_atr_multiplier"] = sl_mult
    prod_config["tp_atr_multiplier"] = tp_mult

    adapter = StrategyAdapter(base_strategy, config=prod_config)

    # Construir lista de variantes: primero la de producción, luego todas las demás
    prod_variant = build_production_variant(sl_mult, tp_mult)
    all_variants = [prod_variant] + list(ALL_VARIANTS)

    runner = ExitResearchRunner(
        symbol="EURUSD",
        strategy=adapter,
        variants=all_variants,
    )

    logger.info(
        "Iniciando Exit Research: strategy=%s  bars=%d  variantes=%d",
        strategy_name, bars, len(all_variants),
    )
    report = runner.run_all(bars=bars, save=True, verbose=verbose)
    return report


# ── Análisis cuantitativo ─────────────────────────────────────────────────────

def analyze_report(report: Dict, strategy_info: Dict) -> str:
    """
    Genera el análisis interpretativo de dos niveles a partir del report_dict.
    Devuelve un string markdown listo para imprimir o guardar.
    """
    strategy_name = strategy_info["name"]
    sl_mult       = strategy_info["sl_mult"]
    tp_mult       = strategy_info["tp_mult"]
    prod_rr       = tp_mult / sl_mult if sl_mult > 0 else 0

    results   = report.get("results", {})
    comp      = report.get("comparison_table", [])
    concl     = report.get("conclusions", {})
    run_id    = report.get("run_id", "unknown")
    generated = report.get("generated_at", "")

    # Máximo nivel disponible
    max_level = "20000"
    for row in comp:
        v = row.get("variant")
        for lv in results.get(v, {}):
            if int(lv) > int(max_level):
                max_level = lv

    def metrics(variant_name: str) -> Dict:
        r = results.get(variant_name, {}).get(max_level, {})
        return (r.get("metrics") or {}) if r else {}

    def fmt(v, d=2):
        if v is None: return "—"
        try: return f"{float(v):.{d}f}"
        except: return "—"

    prod_m = metrics("current_production")

    lines = []
    lines.append(f"# Análisis Exit Research — {strategy_name}")
    lines.append(f"")
    lines.append(f"**Run ID:** `{run_id}` | **Generado:** {generated}")
    lines.append(f"**Estrategia:** `{strategy_name}` | **Config actual:** "
                 f"SL={sl_mult}×ATR  TP={tp_mult}×ATR  (RR≈1:{prod_rr:.1f})")
    lines.append(f"**Dataset:** {max_level} velas H1")
    lines.append(f"")

    # ── NIVEL 1: Resumen ejecutivo ────────────────────────────────────────────
    lines.append("---")
    lines.append("## NIVEL 1 — Resumen Ejecutivo")
    lines.append("")

    if not comp:
        lines.append("_Sin datos suficientes para generar el resumen._")
    else:
        recommended = concl.get("recommended_for_live", "—")
        most_robust = concl.get("most_robust", "—")
        best_wf     = concl.get("best_walk_forward") or "ninguna con WF STABLE"
        lowest_ruin = concl.get("lowest_ruin_probability", "—")
        highest_pf  = concl.get("highest_profit", "—")

        # Decisión de alto nivel basada en datos
        prod_stability = prod_m.get("stability_score", 0) or 0
        best_row = comp[0] if comp else {}
        best_stability = best_row.get("stability_score", 0) or 0
        best_variant   = best_row.get("variant", "—")

        improvement_pct = ((best_stability - prod_stability) / prod_stability * 100
                           if prod_stability > 0 else 0)

        if best_variant == "current_production" or improvement_pct < 5:
            decision = "**MANTENER salida actual** — no se observa mejora significativa."
        elif improvement_pct < 15:
            decision = f"**CONSIDERAR** `{best_variant}` — mejora moderada (+{improvement_pct:.1f}% stability)."
        else:
            decision = f"**INVESTIGAR** `{best_variant}` — mejora relevante (+{improvement_pct:.1f}% stability)."

        lines.append(f"### `{strategy_name}` → {decision}")
        lines.append(f"")
        lines.append(f"| Criterio | Valor |")
        lines.append(f"|---------|-------|")
        lines.append(f"| Salida actual (producción) | PF={fmt(prod_m.get('profit_factor'))}  "
                     f"WR={fmt(prod_m.get('winrate'),1)}%  Stability={fmt(prod_stability,1)} |")
        lines.append(f"| Mejor variante (Stability) | `{best_variant}` — {fmt(best_stability,1)} pts |")
        lines.append(f"| Más rentable (total pips) | `{highest_pf}` |")
        lines.append(f"| Mejor Walk-Forward | `{best_wf}` |")
        lines.append(f"| Menor prob. ruina | `{lowest_ruin}` |")
        lines.append(f"| Recomendada para operar | `{recommended}` |")
        lines.append(f"")

    return "\n".join(lines)


def analyze_report_level2(report: Dict, strategy_info: Dict) -> str:
    """Genera el Nivel 2: análisis completo con todas las métricas e interpretación."""
    strategy_name = strategy_info["name"]
    sl_mult       = strategy_info["sl_mult"]
    tp_mult       = strategy_info["tp_mult"]

    results  = report.get("results", {})
    comp     = report.get("comparison_table", [])

    max_level = max(
        (int(lv) for v in results.values() for lv, r in v.items() if r.get("metrics")),
        default=20000,
    )
    max_level_str = str(max_level)

    def m(variant_name: str) -> Dict:
        r = results.get(variant_name, {}).get(max_level_str, {})
        return (r.get("metrics") or {}) if r else {}

    def fmt(v, d=2, pct=False):
        if v is None: return "—"
        try:
            s = f"{float(v):.{d}f}"
            return s + "%" if pct else s
        except: return "—"

    prod_m    = m("current_production")
    prod_pf   = float(prod_m.get("profit_factor") or 0)
    prod_wr   = float(prod_m.get("winrate") or 0)
    prod_mfe  = float(prod_m.get("mfe_winners") or 0)
    prod_cap  = float(prod_m.get("profit_captured_pct") or 0)
    prod_mae  = float(prod_m.get("mae_losers") or 0)
    prod_dur  = float(prod_m.get("avg_duration_bars") or 0)

    lines = []
    lines.append("---")
    lines.append("## NIVEL 2 — Análisis Completo")
    lines.append("")

    # Tabla comparativa completa
    lines.append("### Tabla comparativa (todas las variantes)")
    lines.append("")
    lines.append("| # | Variante | PF | WR% | Pips | MaxDD | MAE | MFE | Cap% | Sharpe | WF | Stability |")
    lines.append("|--:|---------|---:|----:|-----:|------:|----:|----:|-----:|-------:|----:|----------:|")

    for row in comp:
        vn  = row.get("variant", "")
        mi  = m(vn)
        wf  = mi.get("wf_stability") or "—"
        tag = " ◄ producción" if vn == "current_production" else ""
        lines.append(
            f"| {row.get('rank','')} "
            f"| `{vn}`{tag} "
            f"| {fmt(row.get('profit_factor'))} "
            f"| {fmt(row.get('winrate'),1)} "
            f"| {fmt(row.get('total_pips'),1)} "
            f"| {fmt(row.get('max_drawdown'),1)} "
            f"| {fmt(mi.get('mae_mean'),1)} "
            f"| {fmt(mi.get('mfe_mean'),1)} "
            f"| {fmt(mi.get('profit_captured_pct'),1)} "
            f"| {fmt(row.get('sharpe'),3)} "
            f"| {wf} "
            f"| **{fmt(row.get('stability_score'),2)}** |"
        )

    lines.append("")

    # MAE / MFE detallado
    lines.append("### Análisis MAE / MFE (calidad de salida)")
    lines.append("")
    lines.append("| Variante | MAE gan. | MAE perd. | MFE gan. | MFE perd. | Cap% | Avg Win | Avg Loss |")
    lines.append("|---------|----------:|----------:|----------:|----------:|-----:|--------:|---------:|")
    for row in comp:
        vn = row.get("variant", "")
        mi = m(vn)
        lines.append(
            f"| `{vn}` "
            f"| {fmt(mi.get('mae_winners'),1)} "
            f"| {fmt(mi.get('mae_losers'),1)} "
            f"| {fmt(mi.get('mfe_winners'),1)} "
            f"| {fmt(mi.get('mfe_losers'),1)} "
            f"| {fmt(mi.get('profit_captured_pct'),1)} "
            f"| {fmt(mi.get('avg_win'),1)} "
            f"| {fmt(mi.get('avg_loss'),1)} |"
        )
    lines.append("")

    # Interpretación cuantitativa
    lines.append("### Interpretación cuantitativa")
    lines.append("")

    # TP demasiado ambicioso
    if prod_cap < 40:
        lines.append(f"- **TP demasiado ambicioso:** `profit_captured_pct={prod_cap:.1f}%`. "
                     "Las operaciones ganadoras cierran capturando menos del 40% del movimiento "
                     "máximo observado. El precio suele retroceder antes de alcanzar el TP actual.")
    elif prod_cap < 60:
        lines.append(f"- **TP moderadamente ajustado:** `profit_captured_pct={prod_cap:.1f}%`. "
                     "Se captura entre el 40% y 60% del MFE en trades ganadores.")
    else:
        lines.append(f"- **TP bien calibrado:** `profit_captured_pct={prod_cap:.1f}%`. "
                     "Las salidas capturan más del 60% del movimiento favorable.")

    # MAE en perdedoras — ¿SL demasiado amplio?
    if prod_mae > 0 and sl_mult > 0:
        sl_pips_est = sl_mult * 10  # estimación aproximada en pips (ATR ≈ 10 pips H1 EURUSD)
        if prod_mae < sl_pips_est * 0.5:
            lines.append(f"- **SL posiblemente amplio:** El MAE medio en operaciones perdedoras "
                         f"({prod_mae:.1f} pips) es notablemente menor que el SL inicial estimado "
                         f"({sl_pips_est:.0f} pips). Las pérdidas se materializan antes de que "
                         "el precio llegue al SL completo — podría reducirse el SL.")
        else:
            lines.append(f"- **SL utilizado eficientemente:** MAE medio en perdedoras ({prod_mae:.1f} pips) "
                         "cercano al SL configurado — el precio tiende a alcanzar el stop antes de cerrar.")

    # Duración media
    if prod_dur > 0:
        hours = prod_dur * 1  # H1
        if hours > 72:
            lines.append(f"- **Trades de larga duración:** duración media {prod_dur:.0f} velas H1 "
                         f"(≈ {hours/24:.1f} días). Considerar un `time_exit` para limitar "
                         "exposición en trades sin momentum.")
        elif hours < 8:
            lines.append(f"- **Trades muy cortos:** duración media {prod_dur:.0f} velas H1 "
                         f"(≈ {hours:.0f}h). El sistema cierra rápido — los trailings podrían "
                         "no tener suficiente tiempo para seguir la tendencia.")
        else:
            lines.append(f"- **Duración normal:** {prod_dur:.0f} velas H1 (≈ {hours:.0f}h).")

    # Win rate y RR
    if prod_wr < 30:
        lines.append(f"- **Win Rate bajo ({prod_wr:.1f}%):** el sistema depende de un RR alto "
                     f"para ser rentable. Con RR={tp_mult/sl_mult:.1f} teórico, necesita WR > "
                     f"{1/(1+tp_mult/sl_mult)*100:.0f}% para breakeven. Reducir el RR podría "
                     "mejorar el WR y hacer el sistema más consistente.")
    elif prod_wr > 55:
        lines.append(f"- **Win Rate alto ({prod_wr:.1f}%):** el sistema gana frecuentemente. "
                     "Un trailing podría capturar más de los grandes movimientos ganadores.")
    else:
        lines.append(f"- **Win Rate equilibrado ({prod_wr:.1f}%):** compatible con el RR actual.")

    lines.append("")

    return "\n".join(lines)


def potential_improvements(report: Dict, strategy_info: Dict) -> str:
    """Genera el apartado Potential Improvements basado exclusivamente en datos."""
    results  = report.get("results", {})
    comp     = report.get("comparison_table", [])
    sl_mult  = strategy_info["sl_mult"]
    tp_mult  = strategy_info["tp_mult"]

    max_level_str = str(max(
        (int(lv) for v in results.values() for lv, r in v.items() if r.get("metrics")),
        default=20000,
    ))

    def m(vn): 
        r = results.get(vn, {}).get(max_level_str, {})
        return (r.get("metrics") or {}) if r else {}

    def stab(vn):
        for row in comp:
            if row.get("variant") == vn:
                return float(row.get("stability_score") or 0)
        return 0.0

    prod_stab = stab("current_production")
    prod_m    = m("current_production")
    prod_cap  = float(prod_m.get("profit_captured_pct") or 0)
    prod_pf   = float(prod_m.get("profit_factor") or 0)

    lines = ["---", "### Potential Improvements", ""]
    lines.append("_Solo mejoras respaldadas por datos cuantitativos de esta ejecución._")
    lines.append("")

    improvements_found = 0

    # Comparar cada variante contra la producción
    rr_variants   = [r for r in comp if r.get("variant", "").startswith("rr_")]
    trail_variants = [r for r in comp if "trail" in r.get("variant","") or "donchian" in r.get("variant","")]

    # 1. Reducir RR
    better_rr = [r for r in rr_variants
                 if float(r.get("stability_score") or 0) > prod_stab + 3
                 and r.get("variant") != "current_production"]
    if better_rr:
        best = better_rr[0]
        diff = float(best.get("stability_score") or 0) - prod_stab
        vn   = best.get("variant")
        bm   = m(vn)
        lines.append(f"1. **Reducir RR → `{vn}`**  "
                     f"_(Stability +{diff:.1f} pts vs producción)_  ")
        lines.append(f"   PF={fmt_n(best.get('profit_factor'))}  "
                     f"WR={fmt_n(best.get('winrate'),1)}%  "
                     f"Cap%={fmt_n(bm.get('profit_captured_pct'),1)}%  "
                     f"MaxDD={fmt_n(best.get('max_drawdown'),1)}")
        lines.append(f"   → El mercado tiende a alcanzar un TP más cercano antes de revertir.")
        lines.append("")
        improvements_found += 1

    # 2. Trailing ATR
    atr_row = next((r for r in comp if r.get("variant") == "trailing_atr"), None)
    if atr_row and float(atr_row.get("stability_score") or 0) > prod_stab + 3:
        diff = float(atr_row.get("stability_score") or 0) - prod_stab
        bm   = m("trailing_atr")
        lines.append(f"2. **Trailing ATR**  _(Stability +{diff:.1f} pts vs producción)_  ")
        lines.append(f"   PF={fmt_n(atr_row.get('profit_factor'))}  "
                     f"Cap%={fmt_n(bm.get('profit_captured_pct'),1)}%  "
                     f"MaxDD={fmt_n(atr_row.get('max_drawdown'),1)}")
        lines.append(f"   → Permite capturar tendencias extendidas sin un TP fijo limitante.")
        lines.append("")
        improvements_found += 1

    # 3. Break Even
    be_row = next((r for r in comp if r.get("variant") == "break_even"), None)
    if be_row:
        be_m = m("break_even")
        be_mae_l = float(be_m.get("mae_losers") or 0)
        prod_mae_l = float(prod_m.get("mae_losers") or 0)
        if be_mae_l < prod_mae_l * 0.8:
            lines.append(f"3. **Break Even automático**  "
                         f"_(MAE perdedoras: {be_mae_l:.1f} vs {prod_mae_l:.1f} pips actual)_  ")
            lines.append(f"   → Reduce la pérdida media al eliminar operaciones que rebotan "
                         "contra entrada antes de alcanzar el SL completo.")
            lines.append("")
            improvements_found += 1

    # 4. Time Exit
    te_row = next((r for r in comp if r.get("variant") == "time_exit"), None)
    if te_row:
        te_dur = float(m("time_exit").get("avg_duration_bars") or 0)
        prod_dur = float(prod_m.get("avg_duration_bars") or 0)
        te_stab  = float(te_row.get("stability_score") or 0)
        if te_stab > prod_stab + 2 and prod_dur > 40:
            lines.append(f"4. **Time Exit (48h)**  _(Stability +{te_stab-prod_stab:.1f} pts)_  ")
            lines.append(f"   → Operaciones con duración media actual de {prod_dur:.0f} velas H1. "
                         "Limitar a 48h elimina trades zombi sin momentum.")
            lines.append("")
            improvements_found += 1

    # 5. Mantener salida actual
    if improvements_found == 0:
        lines.append("**Mantener la salida actual.**  ")
        lines.append(f"Ninguna variante supera la producción en más de 3 puntos de Stability Score "
                     f"(base: {prod_stab:.1f}). La evidencia actual no justifica un cambio.")
    elif prod_stab > 0:
        best_overall = comp[0].get("variant") if comp else "—"
        if best_overall == "current_production":
            lines.append("**La salida actual sigue siendo la más robusta según Stability Score.**  ")
            lines.append("Las mejoras sugeridas pueden investigarse en una segunda fase.")

    lines.append("")
    return "\n".join(lines)


def fmt_n(v, d=2):
    """Helper de formateo para cadenas fuera de clase."""
    if v is None: return "—"
    try: return f"{float(v):.{d}f}"
    except: return "—"


# ── Guardar análisis ──────────────────────────────────────────────────────────

def save_analysis(report: Dict, strategy_info: Dict) -> None:
    """
    Guarda el análisis interpretativo en la misma carpeta de sesión
    del report_dict (backtest_results/exit_research/{run_id}/).
    """
    run_id = report.get("run_id", "unknown")
    session_dir = os.path.join(RESULTS_BASE, run_id)
    os.makedirs(session_dir, exist_ok=True)

    level1 = analyze_report(report, strategy_info)
    level2 = analyze_report_level2(report, strategy_info)
    improv = potential_improvements(report, strategy_info)

    full_analysis = "\n".join([level1, level2, improv])

    path = os.path.join(session_dir, "analysis.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(full_analysis)
    logger.info("Análisis guardado: %s", path)

    # Mostrar por consola también
    print()
    print(full_analysis)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Exit Research — análisis cuantitativo de salidas EURUSD"
    )
    parser.add_argument(
        "--bars", type=int, default=20_000,
        help="Número de velas H1 para el backtest (default: 20000)"
    )
    parser.add_argument(
        "--verbose", action="store_true", default=True,
        help="Logging detallado durante la ejecución"
    )
    parser.add_argument(
        "--no-verbose", dest="verbose", action="store_false",
        help="Reducir logging"
    )
    args = parser.parse_args()

    bars = args.bars
    if bars < 5000:
        logger.error("--bars debe ser >= 5000")
        sys.exit(1)

    print()
    print("=" * 72)
    print("  EXIT RESEARCH — EURUSD")
    print(f"  Dataset: {bars:,} velas H1  |  Variantes: 12 + Current Production")
    print(f"  Inicio: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 72)

    # Detectar estrategias activas
    strategies = get_active_eurusd_strategies()
    print_strategy_audit(strategies, DISCARDED_EURUSD)

    if not strategies:
        logger.error("No hay estrategias EURUSD activas para analizar.")
        sys.exit(1)

    # Ejecutar investigación para cada estrategia activa
    all_reports = {}
    for strategy_info in strategies:
        name = strategy_info["name"]
        print()
        print(f"  >> Ejecutando: {name}")
        print(f"    SL={strategy_info['sl_mult']}xATR  TP={strategy_info['tp_mult']}xATR")
        print()
        try:
            report = run_research_for_strategy(strategy_info, bars=bars, verbose=args.verbose)
            all_reports[name] = report
            save_analysis(report, strategy_info)
            run_id = report.get("run_id", "unknown")
            session_dir = os.path.join(RESULTS_BASE, run_id)
            print()
            print(f"  OK Completado. Resultados en: {session_dir}")
        except Exception as e:
            logger.error("Error ejecutando Exit Research para %s: %s", name, e, exc_info=True)
            print(f"  ERROR: {e}")

    # Resumen final
    print()
    print("=" * 72)
    print("  RESUMEN FINAL")
    print("=" * 72)
    for name, report in all_reports.items():
        run_id = report.get("run_id", "unknown")
        comp   = report.get("comparison_table", [])
        best   = comp[0] if comp else {}
        rec    = report.get("conclusions", {}).get("recommended_for_live", "—")
        print(f"  {name}:")
        print(f"    Mejor variante (Stability): {best.get('variant','—')} "
              f"({fmt_n(best.get('stability_score'),1)} pts)")
        print(f"    Recomendada para operar:    {rec}")
        print(f"    Run ID: {run_id}")
        print()
    print("  Archivos generados en: backtest_results/exit_research/")
    print("  >> summary.json, comparison.csv, trades.csv, mae_mfe.csv,")
    print("    report.md, analysis.md")
    print()


if __name__ == "__main__":
    main()
