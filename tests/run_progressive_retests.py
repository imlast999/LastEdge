"""
run_progressive_retests.py — Validación multi-horizonte progresiva

Ejecuta cada estrategia superviviente con 10k, 15k y 20k velas de forma
secuencial, detecta degradación automáticamente y clasifica cada estrategia.

Filosofía: no buscar el PF más alto, sino identificar qué estrategias
sobreviven cuando el horizonte temporal aumenta.

Uso:
    python tests/run_progressive_retests.py
    python tests/run_progressive_retests.py --bars 10000 15000 20000
    python tests/run_progressive_retests.py --strategy eurusd_asian_breakout
    python tests/run_progressive_retests.py --no-cb

Resultados en:
    backtest_results/progressive_retests/session_YYYYMMDD_HHMMSS/
        <strategy>/
            10k/  signals.csv  metrics.json
            15k/  signals.csv  metrics.json
            20k/  signals.csv  metrics.json
            comparison.json   <- degradación 10k→15k→20k
        session_summary.json  <- resumen global con clasificaciones
        session.log           <- log completo
"""

import sys
import os
import json
import time
import logging
import argparse
import datetime
import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ── Estrategias supervivientes (post-optimizacion mayo 2026) ──────────────────
SURVIVOR_STRATEGIES = [
    {'symbol': 'EURUSD', 'strategy': 'eurusd_asian_breakout'},
    {'symbol': 'EURUSD', 'strategy': 'eurusd_simple'},
    {'symbol': 'XAUUSD', 'strategy': 'xauusd_simple'},
    {'symbol': 'XAUUSD', 'strategy': 'xauusd_momentum'},
    {'symbol': 'BTCEUR', 'strategy': 'btceur_simple'},
]

# Parametros optimos del grid search (mayo 2026)
OPTIMAL_PARAMS = {
    'eurusd_asian_breakout': {'tp_multiplier': 1.5, 'min_range_pips': 4.0},
    'eurusd_simple':         {'sl_atr_multiplier': 1.5, 'tp_atr_multiplier': 6.0},
    'xauusd_momentum':       {'sl_atr_multiplier': 2.0, 'tp_atr_multiplier': 6.5},
}

# CB optimo por estrategia
OPTIMAL_CB = {
    'eurusd_asian_breakout': (0, 0),
    'eurusd_simple':         (3, 72),
    'xauusd_simple':         (4, 168),
    'xauusd_momentum':       (3, 72),
    'btceur_simple':         (4, 168),
}

DEFAULT_BARS = [10000, 15000, 20000]

# ── Umbrales de clasificacion ─────────────────────────────────────────────────
MIN_SIGNALS_FOR_VALID = 15       # minimo de trades cerrados para ser valido
PF_ROBUST_MIN        = 1.10     # PF minimo para considerar robusto
PF_STABLE_MIN        = 1.05     # PF minimo para considerar estable
DEGRADATION_WARN     = 0.15     # caida de PF que activa warning
DEGRADATION_FAIL     = 0.30     # caida de PF que clasifica como DEGRADING
DD_GROWTH_WARN       = 0.50     # crecimiento del drawdown >50% entre horizontes


# ── Logging ───────────────────────────────────────────────────────────────────

def setup_logging(log_path: str) -> logging.Logger:
    logger = logging.getLogger('progressive_retest')
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    fh = logging.FileHandler(log_path, encoding='utf-8')
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


# ── Metricas ──────────────────────────────────────────────────────────────────

def compute_metrics(signals, bars: int, strategy: str, symbol: str,
                    cb_losses: int, cb_pause: int, config: dict,
                    elapsed: float) -> dict:
    wins   = [s for s in signals if s.result == 'WIN']
    losses = [s for s in signals if s.result == 'LOSS']
    closed = len(wins) + len(losses)

    gp = sum(s.profit_pips or 0 for s in wins)
    gl = abs(sum(s.profit_pips or 0 for s in losses))
    pf = gp / gl if gl > 0 else (9999.0 if gp > 0 else 0.0)
    net_pips = gp - gl

    # Expectancy por trade (en pips)
    expectancy = net_pips / closed if closed > 0 else 0.0

    # Max drawdown
    equity = peak = dd = 0.0
    equity_curve = []
    for s in signals:
        if s.result in ('WIN', 'LOSS'):
            equity += s.profit_pips or 0
            equity_curve.append(round(equity, 2))
            if equity > peak:
                peak = equity
            dd = max(dd, peak - equity)

    # Racha maxima de perdidas
    max_streak = cur = 0
    for s in signals:
        if s.result == 'LOSS': cur += 1; max_streak = max(max_streak, cur)
        elif s.result == 'WIN': cur = 0

    # Equity smoothness: desviacion estandar de los retornos por trade
    import statistics
    returns = []
    for s in signals:
        if s.result in ('WIN', 'LOSS'):
            returns.append(s.profit_pips or 0)
    equity_std = round(statistics.stdev(returns), 2) if len(returns) > 1 else 0.0

    # Consistency score: % de meses con PF > 1 (aproximado por bloques de 720 velas H1)
    block_size = 720
    block_pfs = []
    for i in range(0, len(signals), max(1, len(signals) // max(1, bars // block_size))):
        block = signals[i:i + max(1, len(signals) // max(1, bars // block_size))]
        bw = sum(s.profit_pips or 0 for s in block if s.result == 'WIN')
        bl = abs(sum(s.profit_pips or 0 for s in block if s.result == 'LOSS'))
        block_pfs.append(bw / bl if bl > 0 else (1.0 if bw > 0 else 0.0))
    consistency = sum(1 for p in block_pfs if p >= 1.0) / len(block_pfs) if block_pfs else 0.0

    return {
        'strategy':        strategy,
        'symbol':          symbol,
        'bars':            bars,
        'cb_losses':       cb_losses,
        'cb_pause':        cb_pause,
        'params':          config,
        'signals_total':   len(signals),
        'signals_closed':  closed,
        'wins':            len(wins),
        'losses':          len(losses),
        'winrate':         round(len(wins) / closed * 100, 2) if closed > 0 else 0.0,
        'profit_factor':   round(min(pf, 9999.0), 4),
        'net_pips':        round(net_pips, 2),
        'expectancy_pips': round(expectancy, 2),
        'max_drawdown':    round(dd, 2),
        'max_loss_streak': max_streak,
        'equity_std':      equity_std,
        'consistency':     round(consistency, 3),
        'equity_curve':    equity_curve[-50:],  # ultimos 50 puntos para graficos futuros
        'elapsed_s':       round(elapsed, 1),
        'valid':           closed >= MIN_SIGNALS_FOR_VALID,
    }


# ── Guardar CSV de senales ────────────────────────────────────────────────────

def save_signals_csv(signals, path: str):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'symbol', 'signal_type', 'entry', 'sl', 'tp',
                         'confidence', 'score', 'result', 'exit_price', 'profit_pips'])
        for s in signals:
            writer.writerow([
                s.timestamp.isoformat() if s.timestamp else '',
                s.symbol, s.signal_type, s.entry, s.sl, s.tp,
                s.confidence, s.score,
                s.result or 'PENDING', s.exit_price or '', s.profit_pips or '',
            ])


# ── Ejecutar un retest individual ─────────────────────────────────────────────

def run_one(symbol: str, strategy: str, bars: int,
            cb_losses: int, cb_pause: int, config: dict,
            out_dir: str, logger: logging.Logger) -> Optional[dict]:
    from tests.backtest_runner import get_replay_params
    from core.replay_engine import ReplayEngine
    from core.engine import get_trading_engine

    lookback, forward, timeframe = get_replay_params(strategy)
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
            symbol=symbol, bars=bars, strategy=strategy,
            config=config or None, timeframe=timeframe,
            skip_duplicate_filter=True,
        )
        signals = engine.get_signals()
        elapsed = time.time() - t0

        metrics = compute_metrics(signals, bars, strategy, symbol,
                                  cb_losses, cb_pause, config, elapsed)

        # Guardar archivos
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        save_signals_csv(signals, os.path.join(out_dir, 'signals.csv'))
        with open(os.path.join(out_dir, 'metrics.json'), 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2)

        pf_str = f"{metrics['profit_factor']:.2f}" if metrics['profit_factor'] < 9999 else "inf"
        status = "OK" if metrics['valid'] else "WARN(pocas senales)"
        logger.info(
            f"    [{status}] {bars//1000}k | PF={pf_str} | "
            f"pips={metrics['net_pips']:+.0f} | WR={metrics['winrate']:.1f}% | "
            f"DD={metrics['max_drawdown']:.0f} | sig={metrics['signals_closed']} | {elapsed:.0f}s"
        )
        return metrics

    except Exception as e:
        elapsed = time.time() - t0
        logger.error(f"    FAIL {bars//1000}k | {e}")
        err = {'strategy': strategy, 'symbol': symbol, 'bars': bars,
               'status': 'ERROR', 'error': str(e), 'elapsed_s': round(elapsed, 1),
               'valid': False, 'profit_factor': 0.0, 'net_pips': 0.0,
               'winrate': 0.0, 'max_drawdown': 0.0, 'signals_closed': 0}
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        with open(os.path.join(out_dir, 'metrics.json'), 'w', encoding='utf-8') as f:
            json.dump(err, f, indent=2)
        return err


# ── Comparacion y clasificacion ───────────────────────────────────────────────

def compare_horizons(results: List[dict]) -> dict:
    """Compara metricas entre horizontes y calcula scores de degradacion."""
    valid = [r for r in results if r and r.get('valid') and r.get('profit_factor', 0) > 0]
    if len(valid) < 2:
        return {'classification': 'INSUFFICIENT_DATA', 'reason': 'Menos de 2 horizontes validos'}

    pfs  = [r['profit_factor'] for r in valid]
    wrs  = [r['winrate'] for r in valid]
    dds  = [r['max_drawdown'] for r in valid]
    bars = [r['bars'] for r in valid]

    # Cambio porcentual del PF entre primer y ultimo horizonte
    pf_change = (pfs[-1] - pfs[0]) / pfs[0] if pfs[0] > 0 else 0.0
    wr_change  = wrs[-1] - wrs[0]
    dd_growth  = (dds[-1] - dds[0]) / dds[0] if dds[0] > 0 else 0.0

    # Degradation score: 0 = sin degradacion, 1 = degradacion total
    degradation_score = max(0.0, -pf_change)  # solo cuenta caidas

    # Robustness score: PF minimo entre todos los horizontes
    robustness_score = min(pfs)

    # Consistency: cuantos horizontes tienen PF > 1.0
    profitable_horizons = sum(1 for p in pfs if p >= 1.0)
    consistency = profitable_horizons / len(valid)

    # Clasificacion automatica
    if len(valid) < 2:
        classification = 'INSUFFICIENT_DATA'
        reason = 'Datos insuficientes'
    elif not all(r.get('valid') for r in results):
        classification = 'INSUFFICIENT_DATA'
        reason = 'Algunos horizontes sin suficientes senales'
    elif min(pfs) >= PF_ROBUST_MIN and degradation_score < DEGRADATION_WARN:
        classification = 'ROBUST'
        reason = f'PF minimo {min(pfs):.2f} >= {PF_ROBUST_MIN}, degradacion {degradation_score:.1%} < {DEGRADATION_WARN:.0%}'
    elif min(pfs) >= PF_STABLE_MIN and degradation_score < DEGRADATION_FAIL:
        classification = 'STABLE'
        reason = f'PF minimo {min(pfs):.2f} >= {PF_STABLE_MIN}, degradacion moderada {degradation_score:.1%}'
    elif pfs[0] >= PF_STABLE_MIN and degradation_score >= DEGRADATION_FAIL:
        classification = 'DEGRADING'
        reason = f'PF cae de {pfs[0]:.2f} a {pfs[-1]:.2f} ({pf_change:.1%})'
    elif pfs[0] >= PF_ROBUST_MIN and pfs[-1] < 1.0:
        classification = 'OVERFITTED'
        reason = f'PF alto en corto ({pfs[0]:.2f}) pero negativo en largo ({pfs[-1]:.2f})'
    elif all(p < 1.0 for p in pfs):
        classification = 'FAILED'
        reason = f'PF siempre por debajo de 1.0 (max: {max(pfs):.2f})'
    else:
        classification = 'INCONCLUSIVE'
        reason = f'Patron mixto: PFs = {[round(p,2) for p in pfs]}'

    # Comparativas entre pares de horizontes
    comparisons = []
    for i in range(len(valid) - 1):
        a, b = valid[i], valid[i + 1]
        comparisons.append({
            'from_bars': a['bars'],
            'to_bars':   b['bars'],
            'pf_change':  round((b['profit_factor'] - a['profit_factor']) / a['profit_factor'] * 100, 1) if a['profit_factor'] > 0 else 0,
            'wr_change':  round(b['winrate'] - a['winrate'], 1),
            'dd_change':  round((b['max_drawdown'] - a['max_drawdown']) / a['max_drawdown'] * 100, 1) if a['max_drawdown'] > 0 else 0,
            'net_pips_change': round(b['net_pips'] - a['net_pips'], 1),
        })

    return {
        'classification':   classification,
        'reason':           reason,
        'pf_by_horizon':    {str(r['bars']): round(r['profit_factor'], 3) for r in valid},
        'wr_by_horizon':    {str(r['bars']): round(r['winrate'], 1) for r in valid},
        'dd_by_horizon':    {str(r['bars']): round(r['max_drawdown'], 1) for r in valid},
        'pf_change_total':  round(pf_change * 100, 1),
        'wr_change_total':  round(wr_change, 1),
        'dd_growth_total':  round(dd_growth * 100, 1),
        'degradation_score': round(degradation_score, 3),
        'robustness_score':  round(robustness_score, 3),
        'consistency':       round(consistency, 3),
        'comparisons':       comparisons,
        'horizons_valid':    len(valid),
        'horizons_total':    len(results),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Validacion multi-horizonte progresiva')
    parser.add_argument('--bars', type=int, nargs='+', default=DEFAULT_BARS)
    parser.add_argument('--strategy', type=str, default=None)
    parser.add_argument('--no-cb', action='store_true')
    args = parser.parse_args()

    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    session_dir = os.path.join('backtest_results', 'progressive_retests', f'session_{ts}')
    Path(session_dir).mkdir(parents=True, exist_ok=True)

    log_path = os.path.join(session_dir, 'session.log')
    logger = setup_logging(log_path)

    from tests.backtest_runner import init_mt5
    logger.info('Conectando a MT5...')
    if not init_mt5():
        logger.error('No se pudo conectar a MT5. Abortando.')
        sys.exit(1)

    targets = SURVIVOR_STRATEGIES
    if args.strategy:
        targets = [s for s in SURVIVOR_STRATEGIES if s['strategy'] == args.strategy]
        if not targets:
            logger.error(f'Estrategia no encontrada: {args.strategy}')
            sys.exit(1)

    bars_list = sorted(set(args.bars))
    total_jobs = len(targets) * len(bars_list)

    logger.info('=' * 65)
    logger.info(f'PROGRESSIVE RETEST SESSION — {ts}')
    logger.info(f'Estrategias: {[t["strategy"] for t in targets]}')
    logger.info(f'Horizontes:  {bars_list} velas')
    logger.info(f'Total jobs:  {total_jobs}')
    logger.info(f'Session dir: {session_dir}')
    logger.info('=' * 65)

    session_results = {}
    job_n = 0
    session_start = time.time()

    for entry in targets:
        symbol   = entry['symbol']
        strategy = entry['strategy']
        config   = OPTIMAL_PARAMS.get(strategy, {})
        cb_l, cb_p = (0, 0) if args.no_cb else OPTIMAL_CB.get(strategy, (4, 168))

        logger.info(f'\n{"─"*65}')
        logger.info(f'  {strategy} ({symbol}) | CB={cb_l}/{cb_p} | params={config or "default"}')
        logger.info(f'{"─"*65}')

        strategy_results = []

        for bars in bars_list:
            job_n += 1
            elapsed_total = time.time() - session_start
            eta_per_job = elapsed_total / job_n if job_n > 1 else 180
            remaining = (total_jobs - job_n) * eta_per_job
            eta_str = f"{int(remaining // 60)}m {int(remaining % 60)}s"
            logger.info(f'  [{job_n}/{total_jobs}] {bars//1000}k velas | ETA restante: ~{eta_str}')

            out_dir = os.path.join(session_dir, strategy, f'{bars//1000}k')
            result = run_one(symbol, strategy, bars, cb_l, cb_p, config, out_dir, logger)
            strategy_results.append(result)

        # Comparacion y clasificacion de esta estrategia
        comparison = compare_horizons(strategy_results)
        comp_path = os.path.join(session_dir, strategy, 'comparison.json')
        Path(os.path.join(session_dir, strategy)).mkdir(parents=True, exist_ok=True)
        with open(comp_path, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2)

        session_results[strategy] = {
            'symbol':     symbol,
            'results':    strategy_results,
            'comparison': comparison,
        }

        # Log de clasificacion inmediata
        cls = comparison['classification']
        cls_icons = {
            'ROBUST': '✅', 'STABLE': '🟡', 'DEGRADING': '⚠️',
            'OVERFITTED': '🔴', 'FAILED': '❌', 'INCONCLUSIVE': '❓',
            'INSUFFICIENT_DATA': '⬜',
        }
        icon = cls_icons.get(cls, '?')
        pf_str = ' → '.join(f"{v:.2f}" for v in comparison.get('pf_by_horizon', {}).values())
        logger.info(f'  {icon} {strategy}: {cls} | PF: {pf_str} | {comparison["reason"]}')

    # ── Summary global ────────────────────────────────────────────────────────
    total_elapsed = time.time() - session_start

    def clean(obj):
        if isinstance(obj, dict): return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, list): return [clean(x) for x in obj]
        if isinstance(obj, float) and (obj != obj or abs(obj) > 1e10): return 9999.0
        return obj

    summary = {
        'timestamp':       ts,
        'total_elapsed_s': round(total_elapsed, 1),
        'bars_tested':     bars_list,
        'no_cb':           args.no_cb,
        'strategies':      clean(session_results),
        'metadata': {
            'optimal_params': OPTIMAL_PARAMS,
            'optimal_cb':     OPTIMAL_CB,
            'thresholds': {
                'pf_robust_min':     PF_ROBUST_MIN,
                'pf_stable_min':     PF_STABLE_MIN,
                'degradation_warn':  DEGRADATION_WARN,
                'degradation_fail':  DEGRADATION_FAIL,
                'min_signals':       MIN_SIGNALS_FOR_VALID,
            },
        },
    }

    summary_path = os.path.join(session_dir, 'session_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    # ── Resumen final en consola ──────────────────────────────────────────────
    logger.info('\n' + '=' * 65)
    logger.info('PROGRESSIVE RETEST SUMMARY')
    logger.info('=' * 65)

    cls_icons = {
        'ROBUST': '✅ ROBUST', 'STABLE': '🟡 STABLE', 'DEGRADING': '⚠️  DEGRADING',
        'OVERFITTED': '🔴 OVERFITTED', 'FAILED': '❌ FAILED',
        'INCONCLUSIVE': '❓ INCONCLUSIVE', 'INSUFFICIENT_DATA': '⬜ INSUF_DATA',
    }

    for strategy, data in session_results.items():
        comp = data['comparison']
        cls  = comp['classification']
        pfs  = comp.get('pf_by_horizon', {})
        label = cls_icons.get(cls, cls)

        pf_line = '  '.join(f"{k//1000 if k.isdigit() else k}k={v:.2f}" for k, v in pfs.items())
        logger.info(f'\n  {strategy}')
        logger.info(f'    PF: {pf_line}')
        logger.info(f'    Degradacion total: {comp.get("pf_change_total", 0):+.1f}%')
        logger.info(f'    Robustness score:  {comp.get("robustness_score", 0):.2f}')
        logger.info(f'    Consistency:       {comp.get("consistency", 0):.0%}')
        logger.info(f'    Status: {label}')

    logger.info(f'\nTiempo total: {int(total_elapsed // 60)}m {int(total_elapsed % 60)}s')
    logger.info(f'Summary:      {summary_path}')
    logger.info(f'Log:          {log_path}')
    logger.info('=' * 65)


if __name__ == '__main__':
    main()
