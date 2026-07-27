@echo off
echo ========================================
echo    Deteniendo BOT-MT5 y API Server
echo ========================================
echo.

REM Cerrar procesos de Node en puerto 5000
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5000.*LISTENING"') do (
    echo Cerrando API Server (PID %%p)...
    taskkill /PID %%p /F >nul 2>&1
)

REM Cerrar bot.py
for /f "tokens=2" %%p in ('tasklist /fi "imagename eq python.exe" /fo list ^| findstr /i "PID:"') do (
    echo Cerrando Bot Python (PID %%p)...
    taskkill /PID %%p /F >nul 2>&1
)

echo.
echo OK - Todos los procesos deteniéndose/cerrados.
timeout /t 2 >nul
exit /b 0
