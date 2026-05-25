@echo off
echo ============================================================
echo   OPTIMIZACION DE ESTRATEGIAS
echo   Prueba grids de TP/SL para estrategias bajo break-even
echo   Resultado: backtest_results/optimization_YYYYMMDD_HHMMSS.json
echo ============================================================
echo.

set PYTHON=python

%PYTHON% --version >nul 2>&1
if errorlevel 1 ( echo ERROR: Python no encontrado. & pause & exit /b 1 )
if not exist "tests\optimize_strategies.py" ( echo ERROR: Ejecuta desde la raiz del proyecto. & pause & exit /b 1 )

REM Crear carpeta si no existe
if not exist "backtest_results" mkdir backtest_results

REM Ejecutar optimizacion de todas las estrategias con 5000 velas
REM Para una sola estrategia: --strategy eurusd_asian_breakout
REM Para mas velas: --bars 10000
%PYTHON% -u tests\optimize_strategies.py --bars 5000

echo.
echo ============================================================
echo  Optimizacion completada.
echo  Revisa backtest_results\optimization_*.json
echo  Para aplicar los mejores parametros:
echo    python tests\apply_optimization.py backtest_results\optimization_YYYYMMDD_HHMMSS.json
echo ============================================================
echo.
pause
