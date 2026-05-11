@echo off
setlocal
echo ============================================================
echo   BACKTEST COMPLETO — Todos los pares y estrategias
echo   Maximo de velas: 10000 H1 (~14 meses de datos)
echo ============================================================
echo.

set PYTHON=python
set SCRIPT=tests\backtest_runner.py
set BARS=10000

REM Verificar que Python existe
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado en el PATH.
    pause
    exit /b 1
)

REM Verificar que el script existe
if not exist "%SCRIPT%" (
    echo ERROR: %SCRIPT% no encontrado. Ejecuta desde la raiz del proyecto.
    pause
    exit /b 1
)

echo Iniciando backtests con %BARS% velas H1 por estrategia...
echo Los resultados se guardaran en backtest_results\
echo.

REM ── EURUSD ────────────────────────────────────────────────────────────────
echo [1/11] EURUSD — eurusd_asian_breakout (estrategia activa)
%PYTHON% %SCRIPT% --symbol EURUSD --strategy eurusd_asian_breakout --bars %BARS% --save
echo.

echo [2/11] EURUSD — eurusd_simple (fallback)
%PYTHON% %SCRIPT% --symbol EURUSD --strategy eurusd_simple --bars %BARS% --save
echo.

echo [3/11] EURUSD — eurusd_advanced
%PYTHON% %SCRIPT% --symbol EURUSD --strategy eurusd_advanced --bars %BARS% --save
echo.

echo [4/11] EURUSD — eurusd_mtf (multi-timeframe H4)
%PYTHON% %SCRIPT% --symbol EURUSD --strategy eurusd_mtf --bars %BARS% --save
echo.

REM ── XAUUSD ────────────────────────────────────────────────────────────────
echo [5/11] XAUUSD — xauusd_simple (estrategia activa)
%PYTHON% %SCRIPT% --symbol XAUUSD --strategy xauusd_simple --bars %BARS% --save
echo.

echo [6/11] XAUUSD — xauusd_reversal
%PYTHON% %SCRIPT% --symbol XAUUSD --strategy xauusd_reversal --bars %BARS% --save
echo.

echo [7/11] XAUUSD — xauusd_momentum
%PYTHON% %SCRIPT% --symbol XAUUSD --strategy xauusd_momentum --bars %BARS% --save
echo.

echo [8/11] XAUUSD — xauusd_psychological
%PYTHON% %SCRIPT% --symbol XAUUSD --strategy xauusd_psychological --bars %BARS% --save
echo.

REM ── BTCEUR ────────────────────────────────────────────────────────────────
echo [9/11] BTCEUR — btceur_simple (estrategia activa)
%PYTHON% %SCRIPT% --symbol BTCEUR --strategy btceur_simple --bars %BARS% --save
echo.

echo [10/11] BTCEUR — btc_trend_pullback_v1
%PYTHON% %SCRIPT% --symbol BTCEUR --strategy btc_trend_pullback_v1 --bars %BARS% --save
echo.

echo [11/11] BTCEUR — btceur_weekly_breakout
%PYTHON% %SCRIPT% --symbol BTCEUR --strategy btceur_weekly_breakout --bars %BARS% --save
echo.

echo ============================================================
echo   BACKTEST COMPLETO TERMINADO
echo   Revisa los resultados en backtest_results\
echo ============================================================
echo.
pause
endlocal
