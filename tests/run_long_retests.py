"""
run_long_retests.py — Retests largos con logging persistente

Ejecuta las estrategias supervivientes con múltiples tamaños de velas
(10k, 15k, 20k) y guarda resultados en backtest_results/retests/.

Diseñado para correr sin supervisión durante horas.
Si una estrategia falla, continúa con las demás.

Uso:
    python tests/run_long_retests.py                    # todas las estrategias, 10k/15k/20k
    python tests/run_long_retests.py --bars 10000       # solo 10k velas
    python tests/run_long_retests.py --strategy eurusd_asian_breakout
    python tests/run_long_retests.py --bars 10000 15000 --no-cb

Resultados en:
    backtest_results/retests/retest_YYYYMMDD_HHMMSS/
        summary.json          <- resumen de todas las estrategias
        <strategy>_<bars>.csv <- señales detalladas
        run.log               <- log completo de la sesión
"""

import sys
import os
import json
import time
import logging
import argparse
import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ── Estrategias supervivientes (post-optimización mayo 2026) ──────────────────
SURVIVOR_STRATEGIES = [
    {'symbol': 'EURUSD', 'strategy': 'eurusd_asian_breakout'},
    {'symbol': 'EURUSD', 'strategy': 'eurusd_simple'},
    {'symbol': 'XAUUSD', 'strategy': 'xauusd_simple'},       # ya validada, incluir como referencia
    {'symbol': 'XAUUSD', 'strategy': 'xauusd_momentum'},
    {'symbol': 'BTCEUR', 'strategy': 'btceur_simple'},        # ya validada, incluir como referencia
]

# Parámetros óptimos encontrados en grid search (mayo 2026)
OPTIMAL_PARAMS = {
    'eurusd_asian_breakout': {'tp_multiplier': 1.5, 'min_range_pips': 4.0},
    'eurusd_simple':         {'sl_atr_multiplier': 1.5, 'tp_atr_multiplier': 6.0},
    'xauusd_momentum':       {'sl_atr_multiplier': 2.0, 'tp_atr_multiplier': 6.5},
    # Las ya validadas usan sus parámetros por defecto
}

# CB óptimo por estrategia (0/0 = sin CB para ver el edge real)
OPTIMAL_CB = {
    'eurusd_asian_breakout': (0, 0),    # funciona sin CB — más honesto
    'eurusd_simple':         (3, 72),   # requiere CB para ser positiva
    'xauusd_simple':         (4, 168),
    'xauusd_momentum':       (3, 72),
    'btceur_simple':         (4, 168),
}

DEFAULT_BARS_LIST = [10000, 15000, 20000]


# ── Logging ───────────────────────────────────────────────────────────────────

def setup_logging(log_path: str) -> logging.Logger:
    logger = logging.getLogger('retest')
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')

    # Consola
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Archivo persistente
    fh = logging.FileHandler(log_path, encoding='utf-8')
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# ── Métricas ──────────────────────────────────────────────────────────────────

def compute_metrics(signals) -> dict:
    wins   = [s for s in signals if s.result == 'WIN']
    losses = [s for s in signals if s.result == 'LOSS']
    closed = len(wins) + len(losses)
    gp = sum(s.profit_pips or 0 for s in wins)
    gl = abs(sum(s.profit_pips or 0 for s in losses))
    pf = gp / gl if gl > 0 else (float('inf') if gp > 0 else 0.0)

    # Max drawdown
    equity = peak = dd = 0.0
    for s in signals:
        if s.result in ('WIN', 'LOSS'):
            equity += s.profit_pips or 0
            if equity > peak:
                peak = equity
            dd = max(dd, peak - equity)

    # Racha máxima de pérdidas
    max_streak = cur = 0
    for s in signals:
        if s.result == 'LOSS': cur += 1; max_streak = max(max_streak, cur)
        elif s.result == 'WIN': cur = 0

    return {
        'signals_total': len(signals),
        'signals_closed': closed,
        'wins': len(wins),
        'losses': len(losses),
        'winrate': wins.__len__() / closed * 100 if closed > 0 else 0.0,
        'profit_factor': round(pf, 4) if pf != float('inf') else 9999.0,
        'net_pips': round(gp - gl, 2),
        'max_drawdown_pips': round(dd, 2),
        'max_loss_streak': max_streak,
    }


# ── Guardar CSV de señales ────────────────────────────────────────────────────

def save_signals_csv(signals, path: str):
    import csv
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'symbol', 'signal_type', 'entry', 'sl', 'tp',
                         'confidence', 'score', 'result', 'exit_price', 'profit_pips'])
        for s in signals:
            writer.writerow([
                s.timestamp.isoformat() if s.timestamp else '',
                s.symbol, s.signal_type,
                s.entry, s.sl, s.tp,
                s.confidence, s.score,
                s.result or 'PENDING',
                s.exit_price or '',
                s.profit_pips or '',
            ])


# ── Ejecutar un retest individual ─────────────────────────────────────────────

def run_one(symbol: str, strategy: str, bars: int,
            cb_losses: int, cb_pause: int,
            config: dict, out_dir: str, logger: logging.Logger) -> dict:
    from tests.backtest_runner import get_replay_params
    from core.replay_engine import ReplayEngine
    from core.engine import get_trading_engine

    lookback, forward, timeframe = get_replay_params(strategy)
    logger.info(f"  Iniciando {strategy} | {bars} velas {timeframe} | CB={cb_losses}/{cb_pause}")

    t0 = time.time()
    try:
        get_trading_engine().reset_replay_state(symbol)
        engine = ReplayEngine(
            lookback_window=lookback,
            max_forward_bars=forward,
            cb_consecutive_losses=cb_losses,
            cb_pause_bars=cb_pause,
        )
        stats = engine.run_replay(
            symbol=symbol,
            bars=bars,
            strategy=strategy,
            config=config or None,
            timeframe=timeframe,
            skip_duplicate_filter=True,
        )
        signals = engine.get_signals()
        elapsed = time.time() - t0

        metrics = compute_metrics(signals)
        metrics['elapsed_s'] = round(elapsed, 1)
        metrics['bars'] = bars
        metrics['strategy'] = strategy
        metrics['symbol'] = symbol
        metrics['cb_losses'] = cb_losses
        metrics['cb_pause'] = cb_pause
        metrics['params'] = config or {}
        metrics['status'] = 'OK'

        # Guardar CSV de señales
        csv_name = f"{strategy}_{bars}bars.csv"
        save_signals_csv(signals, os.path.join(out_dir, csv_name))

        pf_str = f"{metrics['profit_factor']:.2f}" if metrics['profit_factor'] < 9999 else "inf"
        logger.info(
            f"  OK  {strategy} {bars}v | PF={pf_str} | "
            f"pips={metrics['net_pips']:+.0f} | WR={metrics['winrate']:.1f}% | "
            f"sig={metrics['signals_closed']} | {elapsed:.0f}s"
        )
        return metrics

    except Exception as e:
        elapsed = time.time() - t0
        logger.error(f"  FAIL {strategy} {bars}v | {e}")
        return {
            'strategy': strategy, 'symbol': symbol, 'bars': bars,
            'status': 'ERROR', 'error': str(e), 'elapsed_s': round(elapsed, 1),
        }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Retests largos con logging persistente')
    parser.add_argument('--bars', type=int, nargs='+', default=DEFAULT_BARS_LIST,
                        help='Tamaños de velas a probar (default: 10000 15000 20000)')
    parser.add_argument('--strategy', type=str, default=None,
                        help='Estrategia específica (default: todas las supervivientes)')
    parser.add_argument('--no-cb', action='store_true',
                        help='Forzar sin circuit breaker en todas las estrategias')
    args = parser.parse_args()

    # ── Preparar directorio de salida ─────────────────────────────────────────
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    out_dir = os.path.join('backtest_results', 'retests', f'retest_{ts}')
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    log_path = os.path.join(out_dir, 'run.log')
    logger = setup_logging(log_path)

    # ── Conectar MT5 ──────────────────────────────────────────────────────────
    from tests.backtest_runner import init_mt5
    logger.info('Conectando a MT5...')
    if not init_mt5():
        logger.error('No se pudo conectar a MT5. Abortando.')
        sys.exit(1)

    # ── Seleccionar estrategias ───────────────────────────────────────────────
    targets = SURVIVOR_STRATEGIES
    if args.strategy:
        targets = [s for s in SURVIVOR_STRATEGIES if s['strategy'] == args.strategy]
        if not targets:
            logger.error(f'Estrategia no encontrada: {args.strategy}')
            sys.exit(1)

    bars_list = sorted(set(args.bars))
    total_jobs = len(targets) * len(bars_list)

    logger.info('=' * 60)
    logger.info(f'RETEST LARGO — {ts}')
    logger.info(f'Estrategias: {[t["strategy"] for t in targets]}')
    logger.info(f'Velas: {bars_list}')
    logger.info(f'Total jobs: {total_jobs}')
    logger.info(f'Resultados en: {out_dir}')
    logger.info('=' * 60)

    # ── Ejecutar todos los jobs ───────────────────────────────────────────────
    all_results = []
    job_n = 0
    session_start = time.time()

    for entry in targets:
        symbol   = entry['symbol']
        strategy = entry['strategy']
        config   = OPTIMAL_PARAMS.get(strategy, {})
        cb_l, cb_p = (0, 0) if args.no_cb else OPTIMAL_CB.get(strategy, (4, 168))

        for bars in bars_list:
            job_n += 1
            elapsed_total = time.time() - session_start
            eta_per_job = elapsed_total / job_n if job_n > 1 else 120
            remaining = (total_jobs - job_n) * eta_per_job
            eta_str = f"{int(remaining // 60)}m {int(remaining % 60)}s"

            logger.info(f'\n[{job_n}/{total_jobs}] {strategy} | {bars} velas | ETA restante: ~{eta_str}')

            result = run_one(symbol, strategy, bars, cb_l, cb_p, config, out_dir, logger)
            all_results.append(result)

    # ── Guardar summary.json ──────────────────────────────────────────────────
    total_elapsed = time.time() - session_start
    summary = {
        'timestamp': ts,
        'total_elapsed_s': round(total_elapsed, 1),
        'bars_tested': bars_list,
        'strategies_tested': [t['strategy'] for t in targets],
        'no_cb': args.no_cb,
        'results': all_results,
    }

    # Limpiar infinitos para JSON
    def clean(obj):
        if isinstance(obj, dict): return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, list): return [clean(x) for x in obj]
        if isinstance(obj, float) and (obj == float('inf') or obj != obj): return 9999.0
        return obj

    summary_path = os.path.join(out_dir, 'summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(clean(summary), f, indent=2)

    # ── Resumen final en consola ──────────────────────────────────────────────
    logger.info('\n' + '=' * 60)
    logger.info('RESUMEN FINAL')
    logger.info('=' * 60)

    ok_results = [r for r in all_results if r.get('status') == 'OK']
    fail_results = [r for r in all_results if r.get('status') != 'OK']

    # Tabla por estrategia y tamaño
    logger.info(f'\n{"Estrategia":<30} {"Velas":>7} {"PF":>6} {"Pips":>10} {"WR%":>6} {"Sig":>5}')
    logger.info('-' * 65)
    for r in ok_results:
        pf_str = f"{r['profit_factor']:.2f}" if r['profit_factor'] < 9999 else "inf"
        logger.info(
            f"{r['strategy']:<30} {r['bars']:>7} {pf_str:>6} "
            f"{r['net_pips']:>+10.0f} {r['winrate']:>5.1f}% {r['signals_closed']:>5}"
        )

    if fail_results:
        logger.warning(f'\nFallaron {len(fail_results)} jobs:')
        for r in fail_results:
            logger.warning(f"  {r['strategy']} {r.get('bars', '?')}v — {r.get('error', 'unknown')}")

    logger.info(f'\nTiempo total: {int(total_elapsed // 60)}m {int(total_elapsed % 60)}s')
    logger.info(f'Summary: {summary_path}')
    logger.info(f'Log: {log_path}')


if __name__ == '__main__':
    main()
