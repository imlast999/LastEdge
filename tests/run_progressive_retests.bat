@echo off
echo ============================================================
echo   PROGRESSIVE RETESTS — Validacion multi-horizonte
echo   10k / 15k / 20k velas por estrategia
echo   Detecta degradacion y clasifica automaticamente
echo ============================================================
echo.

set PYTHON=python

%PYTHON% --version >nul 2>&1
if errorlevel 1 ( echo ERROR: Python no encontrado. & pause & exit /b 1 )
if not exist "tests\run_progressive_retests.py" ( echo ERROR: Ejecuta desde la raiz del proyecto. & pause & exit /b 1 )

if not exist "backtest_results\progressive_retests" mkdir "backtest_results\progressive_retests"

echo Iniciando retests progresivos (puede tardar 2-4 horas)...
echo Resultados en: backtest_results\progressive_retests\
echo.

%PYTHON% -u tests\run_progressive_retests.py

echo.
echo ============================================================
echo  Retests completados.
echo  Revisa backtest_results\progressive_retests\
echo ============================================================
echo.
pause
