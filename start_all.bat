@echo off
setlocal EnableDelayedExpansion

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "API_DIR=%ROOT%\mobile-app\Pasted-Rol-Objective\artifacts\api-server"
set "WORKSPACE=%ROOT%\mobile-app\Pasted-Rol-Objective"

echo ========================================
echo    BOT-MT5 - Arranque completo
echo    Bot Python + API movil
echo ========================================
echo.

REM ── Detectar IP LAN (primera IPv4 que no sea VirtualBox/VMware) ─────────────
set "LOCAL_IP="
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    for /f "tokens=1" %%b in ("%%a") do (
        set "CAND=%%b"
        set "CAND=!CAND: =!"
        if not defined LOCAL_IP (
            echo !CAND! | findstr /r "^192\.168\.56\." >nul && (
                rem ignorar adaptador VirtualBox
            ) || (
                if not "!CAND!"=="127.0.0.1" set "LOCAL_IP=!CAND!"
            )
        )
    )
)
if not defined LOCAL_IP set "LOCAL_IP=localhost"

echo IP LAN detectada: %LOCAL_IP%
echo.

REM ── Comprobar .env del api-server ───────────────────────────────────────────
if not exist "%API_DIR%\.env" (
    echo ERROR: Falta %API_DIR%\.env
    echo Copia .env.example y configura API_SECRET y BOT_DB_PATH.
    pause
    exit /b 1
)

findstr /r "^API_SECRET=.\+" "%API_DIR%\.env" >nul 2>&1
if errorlevel 1 (
    echo AVISO: API_SECRET vacio en api-server\.env
    echo Genera uno: node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
    echo y copialo tambien en artifacts\mobile\.env como EXPO_PUBLIC_API_SECRET
    echo.
)

REM ── Comprobar Node / pnpm ───────────────────────────────────────────────────
where node >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js no encontrado en PATH
    pause
    exit /b 1
)
where pnpm >nul 2>&1
if errorlevel 1 (
    echo ERROR: pnpm no encontrado. Instala con: npm install -g pnpm
    pause
    exit /b 1
)

REM ── Compilar api-server (siempre, para incluir cambios recientes) ───────────
echo [1/3] Compilando API server...
pushd "%API_DIR%"
call pnpm run build
if errorlevel 1 (
    echo ERROR: Fallo la compilacion del api-server
    popd
    pause
    exit /b 1
)
popd
echo     OK
echo.

REM ── Arrancar API server (ventana separada) ──────────────────────────────────
echo [2/3] Iniciando API movil (puerto 5000)...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5000.*LISTENING"') do (
    echo     AVISO: Puerto 5000 ocupado por PID %%p — cerrando proceso previo...
    taskkill /PID %%p /F >nul 2>&1
)
start "BOT-MT5 API" cmd /k "cd /d "%API_DIR%" && set NODE_ENV=development && pnpm run start"

REM Breve pausa para que el API arranque
timeout /t 2 /nobreak >nul

REM ── Arrancar bot Python (ventana separada) ──────────────────────────────────
echo [3/3] Iniciando bot Python (dashboard en puerto 8080)...
start "BOT-MT5 Bot" cmd /k "cd /d "%ROOT%" && set DASHBOARD_PORT=8080 && call start_bot.bat"

echo.
echo ========================================
echo  Sistema iniciado en dos ventanas:
echo.
echo  API movil (puerto 5000):
echo    Local:  http://localhost:5000/api/healthz
echo    Movil:  http://%LOCAL_IP%:5000/api/healthz
echo.
echo  Dashboard web legacy (puerto 8080 por defecto):
echo    http://localhost:8080
echo.
echo  Bot Python: ventana "BOT-MT5 Bot"
echo.
echo  Config movil (.env):
echo    EXPO_PUBLIC_API_URL=http://%LOCAL_IP%:5000
echo    EXPO_PUBLIC_API_SECRET = mismo que API_SECRET del servidor
echo.
echo  Si cambias IP o token, recompila el APK:
echo    mobile-app\Pasted-Rol-Objective\scripts\build-apk.bat
echo ========================================
echo.
pause

endlocal
