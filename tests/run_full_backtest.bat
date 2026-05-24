@echo off
echo ============================================================
echo   BACKTEST COMPLETO + WALK-FORWARD
echo   Velas: 10000 H1  CB: 4 perdidas / 168 velas pausa
echo ============================================================
echo.

set PYTHON=python

REM Verificar Python
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado en el PATH.
    pause
    exit /b 1
)

REM Verificar que estamos en la raiz del proyecto
if not exist "tests\backtest_runner.py" (
    echo ERROR: Ejecuta este script desde la raiz del proyecto.
    echo        cd C:\ruta\al\proyecto
    echo        tests\run_full_backtest.bat
    pause
    exit /b 1
)

REM Ejecutar el logger — captura salida en consola Y en .txt
%PYTHON% tests\run_backtest_logger.py

echo.
pause
