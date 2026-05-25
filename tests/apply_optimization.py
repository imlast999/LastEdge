"""
Aplica parámetros óptimos del JSON de optimize_strategies.py a los archivos de estrategia.

Uso:
  python tests/apply_optimization.py backtest_results/optimization_YYYYMMDD_HHMMSS.json
"""

import sys
import os
import json
import re

STRATEGY_FILES = {
    'eurusd_asian_breakout': 'strategies/eurusd_asian_breakout.py',
    'eurusd_simple': 'strategies/eurusd.py',  # EURUSDStrategy defaults
    'eurusd_mtf': 'strategies/eurusd_mtf.py',
    'xauusd_momentum': 'strategies/xauusd.py',
    'xauusd_psychological': 'strategies/xauusd_psychological.py',
    'xauusd_reversal': 'strategies/xauusd.py',
    'btceur_regime_momentum': 'strategies/btceur_regime_momentum.py',
}

# eurusd_simple / xauusd_reversal / momentum live in shared files — patch by key in _get_default_config
SIMPLE_CLASS_MARKER = {
    'eurusd_simple': 'class EURUSDStrategy',
    'xauusd_momentum': 'class XAUUSDMomentumStrategy',
    'xauusd_reversal': 'class XAUUSDReversalStrategy',
}


def patch_config_in_file(path: str, updates: dict, class_marker: str = None) -> bool:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    start = 0
    if class_marker and class_marker in content:
        start = content.index(class_marker)

    section = content[start:]
    changed = False
    for key, val in updates.items():
        pattern = rf"('{key}':\s*)[\d.]+"
        repl = rf"\g<1>{val}" if isinstance(val, (int, float)) else rf"\g<1>{val!r}"
        new_section, n = re.subn(pattern, repl, section, count=1)
        if n:
            section = new_section
            changed = True

    if not changed:
        return False

    new_content = content[:start] + section
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True


def main():
    if len(sys.argv) < 2:
        print('Uso: python tests/apply_optimization.py <optimization.json>')
        sys.exit(1)

    path = sys.argv[1]
    with open(path, encoding='utf-8') as f:
        report = json.load(f)

    for name, data in report.get('strategies', {}).items():
        if not data.get('passed_break_even'):
            print(f'  skip {name} (no break-even)')
            continue
        best = data['best']
        params = best['params']
        rel = STRATEGY_FILES.get(name)
        if not rel:
            print(f'  skip {name} (sin archivo)')
            continue
        marker = SIMPLE_CLASS_MARKER.get(name)
        ok = patch_config_in_file(rel, params, marker)
        print(f'  {"OK" if ok else "FAIL"} {name} -> {rel} {params}')


if __name__ == '__main__':
    main()
