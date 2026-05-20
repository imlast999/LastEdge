@echo off
setlocal EnableDelayedExpansion

REM ── Timestamp para el log ─────────────────────────────────────────────────
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "TS=!dt:~0,4!!dt:~4,2!!dt:~6,2!_!dt:~8,2!!dt:~10,2!!dt:~12,2!"
set "LOGFILE=backtest_results\backtest_log_%TS%.txt"

set PYTHON=python
set SCRIPT=tests\backtest_runner.py
set BARS=10000
set CB_LOSSES=4
set CB_PAUSE=168
set WF_TRAIN=4320
set WF_TEST=720
set WF_STEP=720

REM ── Crear carpeta si no existe ─────────────────────────────────────────────
if not exist "backtest_results" mkdir backtest_results

REM ── Limpiar CSVs anteriores ───────────────────────────────────────────────
del /q "backtest_results\*.csv" 2>nul

REM ── Verificaciones ────────────────────────────────────────────────────────
%PYTHON% --version >nul 2>&1
if errorlevel 1 ( echo ERROR: Python no encontrado. & pause & exit /b 1 )
if not exist "%SCRIPT%" ( echo ERROR: %SCRIPT% no encontrado. & pause & exit /b 1 )

echo Iniciando backtest completo...
echo Log: %LOGFILE%
echo.

REM ── Ejecutar todo via Python tee (captura Y muestra en consola) ───────────
%PYTHON% -c "
import subprocess, sys, os, datetime

log_path = r'%LOGFILE%'
os.makedirs('backtest_results', exist_ok=True)

commands = [
    ('WALK-FORWARD EURUSD eurusd_asian_breakout',
     r'%PYTHON% %SCRIPT% --symbol EURUSD --strategy eurusd_asian_breakout --bars %BARS% --walkforward --wf-train %WF_TRAIN% --wf-test %WF_TEST% --wf-step %WF_STEP% --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE% --save'),
    ('WALK-FORWARD XAUUSD xauusd_simple',
     r'%PYTHON% %SCRIPT% --symbol XAUUSD --strategy xauusd_simple --bars %BARS% --walkforward --wf-train %WF_TRAIN% --wf-test %WF_TEST% --wf-step %WF_STEP% --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE% --save'),
    ('WALK-FORWARD BTCEUR btceur_simple',
     r'%PYTHON% %SCRIPT% --symbol BTCEUR --strategy btceur_simple --bars %BARS% --walkforward --wf-train %WF_TRAIN% --wf-test %WF_TEST% --wf-step %WF_STEP% --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE% --save'),
    ('EURUSD eurusd_asian_breakout',
     r'%PYTHON% %SCRIPT% --symbol EURUSD --strategy eurusd_asian_breakout --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%'),
    ('EURUSD eurusd_simple',
     r'%PYTHON% %SCRIPT% --symbol EURUSD --strategy eurusd_simple --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%'),
    ('EURUSD eurusd_advanced',
     r'%PYTHON% %SCRIPT% --symbol EURUSD --strategy eurusd_advanced --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%'),
    ('EURUSD eurusd_mtf',
     r'%PYTHON% %SCRIPT% --symbol EURUSD --strategy eurusd_mtf --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%'),
    ('XAUUSD xauusd_simple',
     r'%PYTHON% %SCRIPT% --symbol XAUUSD --strategy xauusd_simple --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%'),
    ('XAUUSD xauusd_reversal',
     r'%PYTHON% %SCRIPT% --symbol XAUUSD --strategy xauusd_reversal --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%'),
    ('XAUUSD xauusd_momentum',
     r'%PYTHON% %SCRIPT% --symbol XAUUSD --strategy xauusd_momentum --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%'),
    ('XAUUSD xauusd_psychological',
     r'%PYTHON% %SCRIPT% --symbol XAUUSD --strategy xauusd_psychological --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%'),
    ('BTCEUR btceur_simple',
     r'%PYTHON% %SCRIPT% --symbol BTCEUR --strategy btceur_simple --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%'),
    ('BTCEUR btc_trend_pullback_v1',
     r'%PYTHON% %SCRIPT% --symbol BTCEUR --strategy btc_trend_pullback_v1 --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%'),
    ('BTCEUR btceur_weekly_breakout',
     r'%PYTHON% %SCRIPT% --symbol BTCEUR --strategy btceur_weekly_breakout --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%'),
    ('BTCEUR btceur_regime_momentum',
     r'%PYTHON% %SCRIPT% --symbol BTCEUR --strategy btceur_regime_momentum --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%'),
]

def tee(line, f):
    print(line, end='', flush=True)
    f.write(line)

with open(log_path, 'w', encoding='utf-8') as log:
    header = f'BACKTEST LOG — {datetime.datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}\n' + '='*65 + '\n\n'
    tee(header, log)

    for idx, (label, cmd) in enumerate(commands, 1):
        sep = f'\n[{idx}/{len(commands)}] {label}\n' + '-'*50 + '\n'
        tee(sep, log)
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        for line in proc.stdout:
            tee(line, log)
        proc.wait()

    footer = '\n' + '='*65 + '\nCOMPLETADO\n'
    tee(footer, log)

print(f'\nLog guardado en: {log_path}')
"

echo.
echo ============================================================
echo  Log guardado en: %LOGFILE%
echo ============================================================
pause
endlocal
