"""
run_backtest_logger.py

Script auxiliar que ejecuta todos los backtests, muestra la salida
en consola en tiempo real Y la guarda en un archivo .txt en backtest_results/.

Uso (llamado desde run_full_backtest.bat):
    python tests/run_backtest_logger.py
"""

import subprocess
import sys
import os
import datetime

# ── Configuración ─────────────────────────────────────────────────────────────
PYTHON   = sys.executable          # mismo Python que ejecuta este script
SCRIPT   = os.path.join('tests', 'backtest_runner.py')
BARS     = '10000'
CB_L     = '4'
CB_P     = '168'
WF_TRAIN = '4320'
WF_TEST  = '720'
WF_STEP  = '720'

# ── Lista de backtests a ejecutar ─────────────────────────────────────────────
JOBS = [
    # (etiqueta, argumentos extra)
    ('WF EURUSD eurusd_asian_breakout',
     ['--symbol', 'EURUSD', '--strategy', 'eurusd_asian_breakout',
      '--bars', BARS, '--walkforward',
      '--wf-train', WF_TRAIN, '--wf-test', WF_TEST, '--wf-step', WF_STEP,
      '--cb-losses', CB_L, '--cb-pause', CB_P, '--save']),

    ('WF XAUUSD xauusd_simple',
     ['--symbol', 'XAUUSD', '--strategy', 'xauusd_simple',
      '--bars', BARS, '--walkforward',
      '--wf-train', WF_TRAIN, '--wf-test', WF_TEST, '--wf-step', WF_STEP,
      '--cb-losses', CB_L, '--cb-pause', CB_P, '--save']),

    ('WF BTCEUR btceur_simple',
     ['--symbol', 'BTCEUR', '--strategy', 'btceur_simple',
      '--bars', BARS, '--walkforward',
      '--wf-train', WF_TRAIN, '--wf-test', WF_TEST, '--wf-step', WF_STEP,
      '--cb-losses', CB_L, '--cb-pause', CB_P, '--save']),

    ('EURUSD eurusd_asian_breakout',
     ['--symbol', 'EURUSD', '--strategy', 'eurusd_asian_breakout',
      '--bars', BARS, '--save', '--cb-losses', CB_L, '--cb-pause', CB_P]),

    ('EURUSD eurusd_simple',
     ['--symbol', 'EURUSD', '--strategy', 'eurusd_simple',
      '--bars', BARS, '--save', '--cb-losses', CB_L, '--cb-pause', CB_P]),

    ('EURUSD eurusd_advanced',
     ['--symbol', 'EURUSD', '--strategy', 'eurusd_advanced',
      '--bars', BARS, '--save', '--cb-losses', CB_L, '--cb-pause', CB_P]),

    ('EURUSD eurusd_mtf',
     ['--symbol', 'EURUSD', '--strategy', 'eurusd_mtf',
      '--bars', BARS, '--save', '--cb-losses', CB_L, '--cb-pause', CB_P]),

    ('XAUUSD xauusd_simple',
     ['--symbol', 'XAUUSD', '--strategy', 'xauusd_simple',
      '--bars', BARS, '--save', '--cb-losses', CB_L, '--cb-pause', CB_P]),

    ('XAUUSD xauusd_reversal',
     ['--symbol', 'XAUUSD', '--strategy', 'xauusd_reversal',
      '--bars', BARS, '--save', '--cb-losses', CB_L, '--cb-pause', CB_P]),

    ('XAUUSD xauusd_momentum',
     ['--symbol', 'XAUUSD', '--strategy', 'xauusd_momentum',
      '--bars', BARS, '--save', '--cb-losses', CB_L, '--cb-pause', CB_P]),

    ('XAUUSD xauusd_psychological',
     ['--symbol', 'XAUUSD', '--strategy', 'xauusd_psychological',
      '--bars', BARS, '--save', '--cb-losses', CB_L, '--cb-pause', CB_P]),

    ('BTCEUR btceur_simple',
     ['--symbol', 'BTCEUR', '--strategy', 'btceur_simple',
      '--bars', BARS, '--save', '--cb-losses', CB_L, '--cb-pause', CB_P]),

    ('BTCEUR btc_trend_pullback_v1',
     ['--symbol', 'BTCEUR', '--strategy', 'btc_trend_pullback_v1',
      '--bars', BARS, '--save', '--cb-losses', CB_L, '--cb-pause', CB_P]),

    ('BTCEUR btceur_weekly_breakout',
     ['--symbol', 'BTCEUR', '--strategy', 'btceur_weekly_breakout',
      '--bars', BARS, '--save', '--cb-losses', CB_L, '--cb-pause', CB_P]),

    ('BTCEUR btceur_regime_momentum',
     ['--symbol', 'BTCEUR', '--strategy', 'btceur_regime_momentum',
      '--bars', BARS, '--save', '--cb-losses', CB_L, '--cb-pause', CB_P]),
]


def tee(text: str, f):
    """Escribe en consola y en archivo simultáneamente."""
    print(text, end='', flush=True)
    f.write(text)


def main():
    os.makedirs('backtest_results', exist_ok=True)

    # Limpiar CSVs anteriores
    for fname in os.listdir('backtest_results'):
        if fname.endswith('.csv'):
            try:
                os.remove(os.path.join('backtest_results', fname))
            except Exception:
                pass

    ts       = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join('backtest_results', f'backtest_log_{ts}.txt')

    print(f'\nLog: {log_path}\n')

    with open(log_path, 'w', encoding='utf-8') as log:
        header = (
            f'BACKTEST LOG — {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
            f'Velas: {BARS} H1  |  CB: {CB_L}L/{CB_P}v  |  '
            f'WF: train={WF_TRAIN}/test={WF_TEST}/step={WF_STEP}\n'
            + '=' * 65 + '\n\n'
        )
        tee(header, log)

        total = len(JOBS)
        for idx, (label, args) in enumerate(JOBS, 1):
            sep = f'\n[{idx}/{total}] {label}\n' + '-' * 50 + '\n'
            tee(sep, log)

            cmd = [PYTHON, SCRIPT] + args
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                )
                for line in proc.stdout:
                    tee(line, log)
                proc.wait()
            except Exception as e:
                tee(f'ERROR ejecutando {label}: {e}\n', log)

        footer = '\n' + '=' * 65 + '\nCOMPLETADO\n'
        tee(footer, log)

    print(f'\nLog guardado en: {log_path}')


if __name__ == '__main__':
    main()
