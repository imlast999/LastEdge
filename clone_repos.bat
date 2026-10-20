@echo off
setlocal enabledelayedexpansion

title LastEdge - Clonador y Sincronizador de Repositorios

echo ===============================================================================
echo                LastEdge - Sincronizador y Clonador de Repositorios
echo ===============================================================================
echo.

REM 1. Comprobar que Git esta instalado y disponible en PATH
where git >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Git no esta instalado o no se encuentra en el PATH de Windows.
    echo Por favor instala Git desde https://git-scm.com/ y vuelve a intentarlo.
    echo.
    if "%1"=="" pause
    exit /b 1
)

REM URLs oficiales de los sub-repositorios del ecosistema LastEdge
set "REPO_ENGINE=https://github.com/imlast999/lastedge-trading-engine.git"
set "REPO_LAB=https://github.com/imlast999/lastedge-strategy-lab.git"
set "REPO_APP=https://github.com/imlast999/lastedge-app.git"

set "DIR_ENGINE=LastEdge Trading Engine"
set "DIR_LAB=LastEdge Strategy Lab"
set "DIR_APP=LastEdge App"

echo [*] Verificando e integrando repositorios en la carpeta de trabajo...
echo.

call :process_repo "1/3" "LastEdge Trading Engine" "%DIR_ENGINE%" "%REPO_ENGINE%"
call :process_repo "2/3" "LastEdge Strategy Lab" "%DIR_LAB%" "%REPO_LAB%"
call :process_repo "3/3" "LastEdge App [Web Dashboard, Bots, Mobile]" "%DIR_APP%" "%REPO_APP%"

REM Configurar archivos .env si no existen
if exist "%DIR_ENGINE%\.env.example" (
    if not exist "%DIR_ENGINE%\.env" (
        copy "%DIR_ENGINE%\.env.example" "%DIR_ENGINE%\.env" >nul
        echo [*] Creado archivo .env base para Trading Engine.
    )
)
if exist "%DIR_LAB%\.env.example" (
    if not exist "%DIR_LAB%\.env" (
        copy "%DIR_LAB%\.env.example" "%DIR_LAB%\.env" >nul
        echo [*] Creado archivo .env base para Strategy Lab.
    )
)
if exist "%DIR_APP%\.env.example" (
    if not exist "%DIR_APP%\.env" (
        copy "%DIR_APP%\.env.example" "%DIR_APP%\.env" >nul
        echo [*] Creado archivo .env base para LastEdge App.
    )
)
if exist "%DIR_APP%\mobile-app\artifacts\mobile\.env.example" (
    if not exist "%DIR_APP%\mobile-app\artifacts\mobile\.env" (
        copy "%DIR_APP%\mobile-app\artifacts\mobile\.env.example" "%DIR_APP%\mobile-app\artifacts\mobile\.env" >nul
        echo [*] Creado archivo .env base para la app movil.
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
if "%1"=="" pause
exit /b 0

:process_repo
set "STEP=%~1"
set "TITLE=%~2"
set "TARGET_DIR=%~3"
set "REMOTE_URL=%~4"

echo -------------------------------------------------------------------------------
echo [%STEP%] %TITLE%
echo -------------------------------------------------------------------------------
if exist "%TARGET_DIR%\.git" (
    echo [OK] El repositorio "%TARGET_DIR%" ya existe.
    echo [*] Sincronizando ultimos cambios con git pull...
    git -C "%TARGET_DIR%" pull --ff-only
) else (
    echo [*] Clonando "%TARGET_DIR%" desde:
    echo     %REMOTE_URL%
    git clone %REMOTE_URL% "%TARGET_DIR%"
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] No se pudo clonar "%TARGET_DIR%". Verifica tu conexion a internet.
    ) else (
        echo [OK] "%TARGET_DIR%" clonado exitosamente.
    )
)
echo.
goto :eof
