@echo off
set "JAVA_HOME=C:\Users\dev-eugenio\jdk-17.0.14+7"
set "ANDROID_HOME=C:\Users\dev-eugenio\android-sdk"
set "PATH=%JAVA_HOME%\bin;%PATH%"

echo Accepting Android SDK licenses...
(for /l %%i in (1,1,20) do @echo y) | "%ANDROID_HOME%\cmdline-tools\latest\bin\sdkmanager.bat" --licenses --sdk_root="%ANDROID_HOME%" >nul 2>&1

echo Installing platform-tools, platforms;android-36, build-tools;36.0.0...
(for /l %%i in (1,1,20) do @echo y) | "%ANDROID_HOME%\cmdline-tools\latest\bin\sdkmanager.bat" "platform-tools" "platforms;android-36" "build-tools;36.0.0" --sdk_root="%ANDROID_HOME%"
