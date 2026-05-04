@echo off
setlocal
echo ========================================
echo    BOT MT5 - Trading Automatizado
echo ========================================
echo.

set PYTHON_CMD=python
set BOT_SCRIPT=bot.py

REM Crear directorio de logs si no existe
if not exist "logs" mkdir logs

REM Verificar Python
echo Verificando Python...
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado. Instala Python y añadelo al PATH.
    pause
    exit /b 1
)
echo OK - Python encontrado

REM Verificar bot.py
if not exist "%BOT_SCRIPT%" (
    echo ERROR: %BOT_SCRIPT% no encontrado
    pause
    exit /b 1
)

REM Instalar dependencias
echo Instalando dependencias...
if exist "requirements.txt" (
    %PYTHON_CMD% -m pip install -r requirements.txt --quiet
    echo OK - Dependencias instaladas
) else (
    echo AVISO: requirements.txt no encontrado
)

REM Verificar .env
if not exist ".env" (
    echo AVISO: Archivo .env no encontrado
    echo Crea .env con DISCORD_TOKEN, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER
    echo.
)

REM Leer puerto del dashboard desde .env (default 5000)
set DASHBOARD_PORT=5000
for /f "tokens=2 delims==" %%a in ('findstr /i "DASHBOARD_PORT" .env 2^>nul') do set DASHBOARD_PORT=%%a

REM Obtener IP local
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    for /f "tokens=1" %%b in ("%%a") do set LOCAL_IP=%%b
)
if "%LOCAL_IP%"=="" set LOCAL_IP=localhost

echo.
echo Dashboard disponible en:
echo   Local:  http://localhost:%DASHBOARD_PORT%
echo   Movil:  http://%LOCAL_IP%:%DASHBOARD_PORT%
echo.
echo Presiona Ctrl+C para detener el bot
echo ========================================
echo.

REM Ejecutar bot sin pipe para evitar bloqueos de buffer
set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8
%PYTHON_CMD% -u %BOT_SCRIPT%

endlocal

echo.
echo ========================================
echo BOT DETENIDO
echo ========================================
echo Revisa la carpeta 'logs' para diagnosticar problemas.
echo.
timeout /t 3 /nobreak >nul 2>&1
