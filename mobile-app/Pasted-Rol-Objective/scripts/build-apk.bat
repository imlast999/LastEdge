@echo off
chcp 65001 >nul
:: ============================================================================
:: build-apk.bat - Compilar APK localmente con Gradle
::
:: Uso:
::   build-apk.bat           -> APK release (firmado con debug.keystore)
::   build-apk.bat debug     -> APK debug
::
:: El APK resultante queda en:
::   artifacts\mobile\android\app\build\outputs\apk\release\app-release.apk
::   artifacts\mobile\android\app\build\outputs\apk\debug\app-debug.apk
:: ============================================================================

setlocal EnableDelayedExpansion

set ROOT=%~dp0..
set MOBILE=%ROOT%\artifacts\mobile
set API_SERVER=%ROOT%\artifacts\api-server

:: Configurar Java (Android Studio JBR)
set JAVA_HOME=C:\Program Files\Android\Android Studio\jbr
set PATH=%JAVA_HOME%\bin;%PATH%

:: Configurar Android SDK
set ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk
set ANDROID_SDK_ROOT=%ANDROID_HOME%
set PATH=%ANDROID_HOME%\platform-tools;%ANDROID_HOME%\tools;%PATH%

:: Perfil de build
set PROFILE=release
if "%1"=="debug" set PROFILE=debug

echo.
echo ================================================
echo  BOT-MT5 Mobile - Build APK [%PROFILE%]
echo ================================================
echo.

:: Verificar Java
java -version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Java no encontrado en %JAVA_HOME%
    echo Instala Android Studio desde https://developer.android.com/studio
    pause
    exit /b 1
)
echo [OK] Java detectado

:: Verificar Android SDK
if not exist "%ANDROID_HOME%\platform-tools\adb.exe" (
    echo AVISO: Android SDK no encontrado en %ANDROID_HOME%
    echo Si Android Studio esta instalado, el SDK suele estar ahi.
    echo Puedes continuar igualmente si Gradle puede encontrarlo.
)

:: 1. Instalar dependencias
echo.
echo [1/4] Instalando dependencias...
cd /d "%MOBILE%"
call pnpm install --ignore-scripts
if errorlevel 1 (
    echo ERROR: pnpm install fallo.
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas

:: 2. Compilar servidor Express
echo.
echo [2/4] Compilando servidor Express...
cd /d "%API_SERVER%"
call node ./build.mjs
if errorlevel 1 (
    echo ERROR: Build del servidor fallo.
    pause
    exit /b 1
)
echo [OK] Servidor compilado

:: 3. Bundle JS con Expo (prebuild si hace falta)
echo.
echo [3/4] Generando bundle JavaScript con Metro...
cd /d "%MOBILE%"

:: Crear el bundle JS que Gradle necesita
call npx expo export --platform android --output-dir android/app/src/main/assets --no-minify 2>&1
if errorlevel 1 (
    :: Intentar con el metodo clasico de Metro
    echo Intentando bundle con Metro...
    call npx react-native bundle --platform android --dev false --entry-file node_modules/expo-router/entry.js --bundle-output android/app/src/main/assets/index.android.bundle --assets-dest android/app/src/main/res 2>&1
    if errorlevel 1 (
        echo AVISO: bundle JS fallo, Gradle intentara generarlo automaticamente
    )
)
echo [OK] Bundle listo (o Gradle lo generara)

:: 4. Compilar APK con Gradle
echo.
echo [4/4] Compilando APK con Gradle...
cd /d "%MOBILE%\android"

:: Configurar local.properties con el path del SDK y NDK (sin espacios extra)
set SDK_ESCAPED=%ANDROID_HOME:\=\\%
set NDK_ESCAPED=%ANDROID_HOME:\=\\%\\ndk\\27.1.12297006
powershell -NoProfile -Command "\"sdk.dir=%SDK_ESCAPED%`nndk.dir=%NDK_ESCAPED%\" | Set-Content 'local.properties' -Encoding UTF8 -NoNewline"
echo [OK] local.properties configurado con SDK y NDK

if "%PROFILE%"=="debug" (
    call gradlew.bat assembleDebug --no-daemon 2>&1
) else (
    call gradlew.bat assembleRelease --no-daemon 2>&1
)

if errorlevel 1 (
    echo.
    echo ERROR: Gradle fallo. Revisa los mensajes anteriores.
    echo.
    echo Causas comunes:
    echo  - Android SDK no tiene las Build Tools o el NDK necesarios
    echo  - Falta algun permiso o dependencia nativa
    echo  - Intenta ejecutar: cd android ^&^& gradlew.bat assembleDebug
    pause
    exit /b 1
)

:: 5. Limpiar node_modules para liberar espacio
echo.
echo [5/5] Limpiando node_modules...
cd /d "%ROOT%"
if exist "%MOBILE%\node_modules" rmdir /s /q "%MOBILE%\node_modules"
echo [OK] Limpieza completada

echo.
echo ================================================
if "%PROFILE%"=="debug" (
    echo  APK listo en:
    echo  %MOBILE%\android\app\build\outputs\apk\debug\app-debug.apk
) else (
    echo  APK listo en:
    echo  %MOBILE%\android\app\build\outputs\apk\release\app-release.apk
)
echo.
echo  Para instalar en Android:
echo  1. Copia el APK al movil (USB o Google Drive)
echo  2. Ajustes - Seguridad - Fuentes desconocidas - Activar
echo  3. Abre el APK desde el movil
echo ================================================
echo.

endlocal
