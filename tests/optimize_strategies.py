"""
Optimización de estrategias por debajo de break-even.

Prueba grids de TP/SL y circuit breaker; guarda el mejor combo por estrategia.
Uso:
  python tests/optimize_strategies.py --bars 5000
  python tests/optimize_strategies.py --strategy eurusd_asian_breakout --bars 10000
"""

import sys
import os
import json
import itertools
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from tests.backtest_runner import get_replay_params, compute_extra_metrics, init_mt5

BARS_DEFAULT = 5000
MIN_SIGNALS = 8
MIN_PF = 1.0

# Estrategias que ya superaron break-even en backtest 10k (no optimizar)
SKIP = frozenset({
    'eurusd_advanced', 'xauusd_simple', 'btceur_simple',
    'btc_trend_pullback_v1', 'btceur_weekly_breakout',
})

# Grids por estrategia (solo parámetros de gestión / filtros ligeros)
OPTIMIZATION_PLANS = {
    'eurusd_asian_breakout': {
        'symbol': 'EURUSD',
        'param_grid': {
            'tp_multiplier': [1.5, 2.0, 2.5, 3.0],
            'min_range_pips': [4.0, 5.0, 6.0],
        },
    },
    'eurusd_simple': {
        'symbol': 'EURUSD',
        'param_grid': {
            'sl_atr_multiplier': [1.5, 2.0, 2.5],
            'tp_atr_multiplier': [4.0, 5.0, 6.0, 7.0],
        },
    },
    'eurusd_mtf': {
        'symbol': 'EURUSD',
        'param_grid': {
            'sl_atr_multiplier': [2.0, 2.5, 3.0],
            'tp_atr_multiplier': [5.0, 6.0, 7.0, 8.0],
        },
    },
    'xauusd_momentum': {
        'symbol': 'XAUUSD',
        'param_grid': {
            'sl_atr_multiplier': [1.5, 2.0, 2.5],
            'tp_atr_multiplier': [3.6, 4.5, 5.5, 6.5],
        },
    },
    'xauusd_psychological': {
        'symbol': 'XAUUSD',
        'param_grid': {
            'tp_multiplier': [1.5, 2.0, 2.5, 3.0],
            'sl_buffer': [1.5, 2.0, 3.0],
        },
    },
    'xauusd_reversal': {
        'symbol': 'XAUUSD',
        'param_grid': {
            'sl_atr_multiplier': [2.0, 2.5],
            'tp_atr_multiplier': [4.0, 5.0, 6.0],
            'rsi_oversold': [25, 28],
            'rsi_overbought': [72, 75],
        },
    },
    'btceur_regime_momentum': {
        'symbol': 'BTCEUR',
        'param_grid': {
            'adx_threshold': [15, 18, 20],
            'sl_atr_multiplier': [2.0, 2.5, 3.0],
            'tp_atr_multiplier': [3.5, 4.0, 5.0, 6.0],
            'donchian_length': [15, 20],
        },
    },
}

CB_GRID = [
    (0, 0),
    (4, 168),
    (3, 72),
]


def run_metrics(symbol: str, strategy: str, bars: int, config: dict,
                cb_losses: int, cb_pause: int) -> dict:
    from core.replay_engine import ReplayEngine
    from core.engine import get_trading_engine

    lookback, forward, timeframe = get_replay_params(strategy)
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
        config=config,
        timeframe=timeframe,
        skip_duplicate_filter=True,
    )
    signals = engine.get_signals()
    closed = [s for s in signals if s.result in ('WIN', 'LOSS')]
    if len(closed) < MIN_SIGNALS:
        return {
            'signals': len(closed),
            'pf': 0.0,
            'net_pips': -99999.0,
            'winrate': 0.0,
            'valid': False,
        }
    extra = compute_extra_metrics(signals)
    return {
        'signals': stats.signals_final,
        'pf': extra['profit_factor'],
        'net_pips': stats.total_pips,
        'winrate': stats.winrate,
        'valid': True,
    }


def expand_grid(param_grid: dict) -> list:
    keys = list(param_grid.keys())
    values = [param_grid[k] for k in keys]
    combos = []
    for vals in itertools.product(*values):
        combos.append(dict(zip(keys, vals)))
    return combos


def score_result(m: dict) -> float:
    """Mayor = mejor. Prioriza PF, luego pips, luego winrate."""
    if not m.get('valid'):
        return -1e9
    pf = m['pf']
    if pf < MIN_PF or m['net_pips'] < 0:
        return m['net_pips'] - 1000  # por debajo de BE pero ordena por menos malo
    return pf * 1000 + m['net_pips'] + m['winrate'] * 0.1


def optimize_one(strategy: str, bars: int) -> dict:
    plan = OPTIMIZATION_PLANS[strategy]
    symbol = plan['symbol']
    param_combos = expand_grid(plan['param_grid'])
    results = []
    total = len(param_combos) * len(CB_GRID)
    n = 0

    print(f'\n{"="*60}', flush=True)
    print(f'  Optimizando: {strategy} ({symbol}) — {total} combinaciones', flush=True)
    print(f'{"="*60}', flush=True)

    best = None
    best_score = -1e18

    for params in param_combos:
        for cb_l, cb_p in CB_GRID:
            n += 1
            m = run_metrics(symbol, strategy, bars, params, cb_l, cb_p)
            row = {
                'params': params,
                'cb_losses': cb_l,
                'cb_pause': cb_p,
                **m,
            }
            results.append(row)
            sc = score_result(m)
            tag = 'OK' if m['valid'] and m['pf'] >= MIN_PF and m['net_pips'] >= 0 else '--'
            if n % 5 == 0 or tag == 'OK':
                print(f'  [{n}/{total}] {tag} PF={m["pf"]:.2f} pips={m["net_pips"]:.0f} '
                      f'WR={m["winrate"]:.1f}% sig={m["signals"]} '
                      f'params={params} CB={cb_l}/{cb_p}', flush=True)

            if sc > best_score:
                best_score = sc
                best = row

    passed = best and best.get('valid') and best['pf'] >= MIN_PF and best['net_pips'] >= 0
    return {
        'strategy': strategy,
        'symbol': symbol,
        'bars': bars,
        'passed_break_even': passed,
        'best': best,
        'top5': sorted(results, key=score_result, reverse=True)[:5],
        'combos_tested': total,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--bars', type=int, default=BARS_DEFAULT)
    parser.add_argument('--strategy', type=str, default='all',
                        help='Nombre estrategia o "all"')
    args = parser.parse_args()

    if not init_mt5():
        sys.exit(1)

    targets = list(OPTIMIZATION_PLANS.keys())
    if args.strategy != 'all':
        if args.strategy not in OPTIMIZATION_PLANS:
            print(f'Estrategia desconocida: {args.strategy}')
            sys.exit(1)
        targets = [args.strategy]

    report = {
        'timestamp': datetime.now().isoformat(),
        'bars': args.bars,
        'min_pf': MIN_PF,
        'strategies': {},
    }

    for strat in targets:
        if strat in SKIP:
            print(f'  (skip) {strat} — ya validada')
            continue
        report['strategies'][strat] = optimize_one(strat, args.bars)

    out_dir = 'backtest_results'
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join(out_dir, f'optimization_{ts}.json')

    # JSON-serializable
    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [clean(x) for x in obj]
        if isinstance(obj, float) and obj == float('inf'):
            return 9999.0
        return obj

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(clean(report), f, indent=2)

    print(f'\n{"="*60}')
    print('  RESUMEN')
    print(f'{"="*60}')
    passed_list = []
    failed_list = []
    for name, data in report['strategies'].items():
        b = data.get('best') or {}
        ok = data.get('passed_break_even')
        if ok:
            passed_list.append(name)
            print(f'  OK  {name}: PF={b["pf"]:.2f} pips={b["net_pips"]:.0f} '
                  f'CB={b["cb_losses"]}/{b["cb_pause"]} params={b["params"]}')
        else:
            failed_list.append(name)
            print(f'  FAIL {name}: mejor PF={b.get("pf", 0):.2f} pips={b.get("net_pips", 0):.0f}')

    print(f'\n  Superan break-even: {passed_list or "(ninguna)"}')
    print(f'  Candidatas a eliminar: {failed_list or "(ninguna)"}')
    print(f'\n  Guardado: {out_path}')
    return passed_list, failed_list, report


if __name__ == '__main__':
    main()
