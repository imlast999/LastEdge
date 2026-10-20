@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title LastEdge — Clonador y Sincronizador de Repositorios

echo ===============================================================================
echo                LastEdge — Sincronizador y Clonador de Repositorios
echo ===============================================================================
echo.

:: 1. Comprobar que Git está instalado y disponible en PATH
where git >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Git no está instalado o no se encuentra en el PATH de Windows.
    echo Por favor instala Git desde https://git-scm.com/ y vuelve a intentarlo.
    echo.
    pause
    exit /b 1
)

:: URLs oficiales de los sub-repositorios del ecosistema LastEdge
set "REPO_ENGINE=https://github.com/imlast999/lastedge-trading-engine.git"
set "REPO_LAB=https://github.com/imlast999/lastedge-strategy-lab.git"
set "REPO_APP=https://github.com/imlast999/lastedge-app.git"

set "DIR_ENGINE=LastEdge Trading Engine"
set "DIR_LAB=LastEdge Strategy Lab"
set "DIR_APP=LastEdge App"

echo [*] Verificando e integrando repositorios en la carpeta de trabajo...
echo.

:: ── 1. LastEdge Trading Engine ──────────────────────────────────────────────
echo -------------------------------------------------------------------------------
echo [1/3] LastEdge Trading Engine
echo -------------------------------------------------------------------------------
if exist "%DIR_ENGINE%\.git" (
    echo [OK] El repositorio "%DIR_ENGINE%" ya existe.
    echo [*] Sincronizando ultimos cambios (git pull)...
    git -C "%DIR_ENGINE%" pull --ff-only
) else (
    echo [*] Clonando "%DIR_ENGINE%" desde:
    echo     %REPO_ENGINE%
    git clone %REPO_ENGINE% "%DIR_ENGINE%"
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] No se pudo clonar "%DIR_ENGINE%". Verifica tu conexion a internet.
    ) else (
        echo [OK] "%DIR_ENGINE%" clonado exitosamente.
        if not exist "%DIR_ENGINE%\.env" (
            if exist "%DIR_ENGINE%\.env.example" (
                copy "%DIR_ENGINE%\.env.example" "%DIR_ENGINE%\.env" >nul
                echo [*] Creado archivo .env base para Trading Engine.
            )
        )
    )
)
echo.

:: ── 2. LastEdge Strategy Lab ────────────────────────────────────────────────
echo -------------------------------------------------------------------------------
echo [2/3] LastEdge Strategy Lab
echo -------------------------------------------------------------------------------
if exist "%DIR_LAB%\.git" (
    echo [OK] El repositorio "%DIR_LAB%" ya existe.
    echo [*] Sincronizando ultimos cambios (git pull)...
    git -C "%DIR_LAB%" pull --ff-only
) else (
    echo [*] Clonando "%DIR_LAB%" desde:
    echo     %REPO_LAB%
    git clone %REPO_LAB% "%DIR_LAB%"
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] No se pudo clonar "%DIR_LAB%". Verifica tu conexion a internet.
    ) else (
        echo [OK] "%DIR_LAB%" clonado exitosamente.
        if not exist "%DIR_LAB%\.env" (
            if exist "%DIR_LAB%\.env.example" (
                copy "%DIR_LAB%\.env.example" "%DIR_LAB%\.env" >nul
                echo [*] Creado archivo .env base para Strategy Lab.
            )
        )
    )
)
echo.

:: ── 3. LastEdge App ─────────────────────────────────────────────────────────
echo -------------------------------------------------------------------------------
echo [3/3] LastEdge App (Web Dashboard, Bots ^& Mobile)
echo -------------------------------------------------------------------------------
if exist "%DIR_APP%\.git" (
    echo [OK] El repositorio "%DIR_APP%" ya existe.
    echo [*] Sincronizando ultimos cambios (git pull)...
    git -C "%DIR_APP%" pull --ff-only
) else (
    echo [*] Clonando "%DIR_APP%" desde:
    echo     %REPO_APP%
    git clone %REPO_APP% "%DIR_APP%"
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] No se pudo clonar "%DIR_APP%". Verifica tu conexion a internet.
    ) else (
        echo [OK] "%DIR_APP%" clonado exitosamente.
        if not exist "%DIR_APP%\.env" (
            if exist "%DIR_APP%\.env.example" (
                copy "%DIR_APP%\.env.example" "%DIR_APP%\.env" >nul
                echo [*] Creado archivo .env base para LastEdge App.
            )
        )
        if not exist "%DIR_APP%\mobile-app\artifacts\mobile\.env" (
            if exist "%DIR_APP%\mobile-app\artifacts\mobile\.env.example" (
                copy "%DIR_APP%\mobile-app\artifacts\mobile\.env.example" "%DIR_APP%\mobile-app\artifacts\mobile\.env" >nul
                echo [*] Creado archivo .env base para la app movil.
            )
        )
    )
)
echo.

echo ===============================================================================
echo [EXITO] Todo el ecosistema LastEdge ha sido sincronizado en esta carpeta.
echo.
echo Siguientes pasos:
echo   1. Revisa o personaliza tus credenciales en los archivos .env si es necesario.
echo   2. Ejecuta el entorno completo con:
echo          .\lastedge.bat
echo ===============================================================================
echo.
pause
