@echo off
setlocal
echo ============================================================
echo   BACKTEST COMPLETO + WALK-FORWARD
echo   Velas: 10000 H1 (~14 meses)
echo   CB: 4 perdidas / pausa 168 velas
echo ============================================================
echo.

set PYTHON=python
set SCRIPT=tests\backtest_runner.py
set BARS=10000
set CB_LOSSES=4
set CB_PAUSE=168
set WF_TRAIN=4320
set WF_TEST=720
set WF_STEP=720

REM Verificar Python
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado en el PATH.
    pause
    exit /b 1
)

REM Verificar script
if not exist "%SCRIPT%" (
    echo ERROR: %SCRIPT% no encontrado. Ejecuta desde la raiz del proyecto.
    pause
    exit /b 1
)

REM Limpiar resultados anteriores
echo Limpiando backtest_results\ ...
if exist "backtest_results" (
    del /q "backtest_results\*.csv" 2>nul
    echo OK - Carpeta limpiada
) else (
    mkdir backtest_results
    echo OK - Carpeta creada
)
echo.

REM ── WALK-FORWARD de las 3 estrategias activas ─────────────────────────────
echo ============================================================
echo   WALK-FORWARD — Estrategias activas
echo   Train=%WF_TRAIN% velas / Test=%WF_TEST% velas / Step=%WF_STEP% velas
echo ============================================================
echo.

echo [WF 1/3] EURUSD - eurusd_asian_breakout
%PYTHON% %SCRIPT% --symbol EURUSD --strategy eurusd_asian_breakout --bars %BARS% --walkforward --wf-train %WF_TRAIN% --wf-test %WF_TEST% --wf-step %WF_STEP% --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE% --save
echo.

echo [WF 2/3] XAUUSD - xauusd_simple
%PYTHON% %SCRIPT% --symbol XAUUSD --strategy xauusd_simple --bars %BARS% --walkforward --wf-train %WF_TRAIN% --wf-test %WF_TEST% --wf-step %WF_STEP% --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE% --save
echo.

echo [WF 3/3] BTCEUR - btceur_simple
%PYTHON% %SCRIPT% --symbol BTCEUR --strategy btceur_simple --bars %BARS% --walkforward --wf-train %WF_TRAIN% --wf-test %WF_TEST% --wf-step %WF_STEP% --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE% --save
echo.

REM ── BACKTESTS INDIVIDUALES — Todas las estrategias ────────────────────────
echo ============================================================
echo   BACKTESTS INDIVIDUALES — Todas las estrategias
echo ============================================================
echo.

echo [1/11] EURUSD - eurusd_asian_breakout (activa)
%PYTHON% %SCRIPT% --symbol EURUSD --strategy eurusd_asian_breakout --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%
echo.

echo [2/11] EURUSD - eurusd_simple (fallback)
%PYTHON% %SCRIPT% --symbol EURUSD --strategy eurusd_simple --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%
echo.

echo [3/11] EURUSD - eurusd_advanced
%PYTHON% %SCRIPT% --symbol EURUSD --strategy eurusd_advanced --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%
echo.

echo [4/11] EURUSD - eurusd_mtf
%PYTHON% %SCRIPT% --symbol EURUSD --strategy eurusd_mtf --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%
echo.

echo [5/11] XAUUSD - xauusd_simple (activa)
%PYTHON% %SCRIPT% --symbol XAUUSD --strategy xauusd_simple --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%
echo.

echo [6/11] XAUUSD - xauusd_reversal
%PYTHON% %SCRIPT% --symbol XAUUSD --strategy xauusd_reversal --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%
echo.

echo [7/11] XAUUSD - xauusd_momentum
%PYTHON% %SCRIPT% --symbol XAUUSD --strategy xauusd_momentum --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%
echo.

echo [8/11] XAUUSD - xauusd_psychological
%PYTHON% %SCRIPT% --symbol XAUUSD --strategy xauusd_psychological --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%
echo.

echo [9/11] BTCEUR - btceur_simple (activa)
%PYTHON% %SCRIPT% --symbol BTCEUR --strategy btceur_simple --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%
echo.

echo [10/11] BTCEUR - btc_trend_pullback_v1
%PYTHON% %SCRIPT% --symbol BTCEUR --strategy btc_trend_pullback_v1 --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%
echo.

echo [11/11] BTCEUR - btceur_weekly_breakout
%PYTHON% %SCRIPT% --symbol BTCEUR --strategy btceur_weekly_breakout --bars %BARS% --save --cb-losses %CB_LOSSES% --cb-pause %CB_PAUSE%
echo.

echo ============================================================
echo   COMPLETADO — Revisa backtest_results\
echo ============================================================
echo.
pause
endlocal
