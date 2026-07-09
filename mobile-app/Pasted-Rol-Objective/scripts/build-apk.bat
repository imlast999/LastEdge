@echo off
:: ============================================================================
:: build-apk.bat — Ciclo completo: instalar deps, compilar APK, limpiar deps
::
:: Uso:
::   build-apk.bat           → APK de release (firmado con debug.keystore)
::   build-apk.bat debug     → APK de debug
::
:: El APK resultante queda en:
::   artifacts\mobile\android\app\build\outputs\apk\release\app-release.apk
::   artifacts\mobile\android\app\build\outputs\apk\debug\app-debug.apk
::
:: Requisitos:
::   - pnpm instalado (npm install -g pnpm)
::   - Java 17+ en el PATH
::   - Android SDK (si compilas localmente con Gradle)
::   - O bien: eas-cli instalado (npm install -g eas-cli) para build en la nube
:: ============================================================================

setlocal
set ROOT=%~dp0..
set MOBILE=%ROOT%\artifacts\mobile
set APIK_SERVER=%ROOT%\artifacts\api-server

:: Perfil: release por defecto, debug si se pasa argumento
set PROFILE=release
if "%1"=="debug" set PROFILE=debug

echo.
echo ================================================
echo  BOT-MT5 Mobile — Build APK [%PROFILE%]
echo ================================================
echo.

:: 1. Instalar dependencias de todo el workspace
echo [1/4] Instalando dependencias (pnpm install)...
cd /d "%ROOT%"
call pnpm install --ignore-scripts
if errorlevel 1 (
    echo ERROR: pnpm install fallo
    exit /b 1
)
echo     OK

:: 2. Compilar el servidor Express (necesario para que el bundle JS lo pueda importar)
echo [2/4] Compilando servidor Express...
cd /d "%APIK_SERVER%"
call pnpm run build
if errorlevel 1 (
    echo ERROR: build del servidor fallo
    exit /b 1
)
echo     OK

:: 3. Compilar el APK (cargar .env para EXPO_PUBLIC_* en el bundle)
echo [3/4] Compilando APK Android (%PROFILE%)...
cd /d "%MOBILE%"
if exist ".env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do (
        if not "%%a"=="" set "%%a=%%b"
    )
    echo     Variables cargadas desde artifacts\mobile\.env
)
if "%PROFILE%"=="debug" (
    call pnpm run build:apk:debug
) else (
    call pnpm run build:apk:release
)
if errorlevel 1 (
    echo ERROR: build del APK fallo
    exit /b 1
)
echo     OK

:: 4. Limpiar caches de Gradle (mantener node_modules para builds futuros)
echo [4/4] Limpiando caches de Gradle...
cd /d "%ROOT%"
if exist "%MOBILE%\android\app\.cxx" rmdir /s /q "%MOBILE%\android\app\.cxx"
if exist "%MOBILE%\android\.gradle" rmdir /s /q "%MOBILE%\android\.gradle"
echo     OK

:: Mostrar resultado
echo.
echo ================================================
echo  APK listo en:
if "%PROFILE%"=="debug" (
    echo  %MOBILE%\android\app\build\outputs\apk\debug\app-debug.apk
) else (
    echo  %MOBILE%\android\app\build\outputs\apk\release\app-release.apk
)
echo ================================================
echo.

endlocal
