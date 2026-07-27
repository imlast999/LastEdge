# Estado Actual del Proyecto: LastEdge

> **Nota:** Documento temporal de diagnóstico y estado del sistema.

---

## 1. ¿De qué trata el proyecto?

**LastEdge** es una plataforma de trading algorítmico cuantitativo profesional integrada con **MetaTrader 5 (MT5)**. Está diseñada bajo los principios de *Research First*, *Clean Architecture* y mantenimiento a largo plazo. 

El sistema abarca desde la investigación estadística de estrategias (Walk Forward Analysis, Monte Carlo, Exit Research) y la gestión dinámica de riesgo en tiempo real (*Risk Engine v2*), hasta la ejecución automatizada de órdenes y el monitoreo remoto mediante una aplicación móvil y API REST.

---

## 2. Tecnologías y Stack Utilizado

### Backend y Motor de Trading (Python)
- **Lenguaje:** Python 3.12+
- **Integración Broker:** `MetaTrader5` API (conexión directa, reconexión automática y telemetría de posiciones).
- **Lógicas Principales:**
  - `bot.py`: Bucle principal de ejecución e integración con MT5.
  - `core/risk/`: Risk Engine v2 (gestión de margen, tamaño de posición, riesgo de cartera y trailing stops).
  - `run_exit_research.py`: Framework cuantitativo de pruebas de salida e investigación.
  - `market_opening_system.py`, `reconnection_system.py`, `position_manager.py`.

### Servidor de API REST (Node.js / Express)
- **Ubicación:** `mobile-app/Pasted-Rol-Objective/artifacts/api-server`
- **Stack:** Node.js, Express, TypeScript, esbuild, Pino logging, pnpm workspaces.
- **Función:** Expone los endpoints de control y estado para la aplicación móvil.

### Aplicación Móvil (React Native / Expo)
- **Ubicación:** `mobile-app/Pasted-Rol-Objective/artifacts/mobile`
- **Stack:** React Native (0.81.5), Expo (SDK 54), TypeScript, Expo Router, Reanimated, Lucide Icons, TailwindCSS.
- **Herramientas de Build:** Scripts de automatización en `scripts/build-apk.bat` y Gradle/CMake nativo para Android.

---

- **Motor de Trading y Riesgo (Python):** Funcional e integrado con MT5 y Risk Engine v2.
- **Capa Multiplataforma de Bots (Discord + Telegram):** Arquitectura desacoplada en `services/bot_service.py`, `services/commands_refactored.py` (DiscordAdapter), `services/telegram_adapter.py` (TelegramAdapter) y `services/notification_dispatcher.py` (Notificaciones simultáneas multi-canal). Ambos bots conviven en tiempo real usando exactamente la misma lógica de negocio sin duplicaciones.
- **Base de Datos de Investigación (Research Database):** Módulo `services/research_store.py` e ingesta automática activada. Tabla `research_experiments` lista con trazabilidad por `git_commit`, versión del bot, hipótesis, parámetros reproducibles completos (`config_json`), etiquetas y dictámenes (`PROMOTED`, `REJECTED`, `CANDIDATE`).
- **API Server:** Compilación limpia con `esbuild` y endpoints CRUD completos en `/api/research/experiments/*` (crear, consultar, filtrar, editar y reabrir experimentos).
- **Aplicación Móvil y Build Pipeline:** 
  - **Script de compilación (`build-apk.bat`):** Corregido y adaptado dinámicamente para cualquier entorno Windows/Android SDK.
  - **Empaquetamiento (Metro Bundler):** Resolución de módulos (`expo-router`, `babel-preset-expo`) 100% operativa.
  - **Compilación APK (Gradle / C++ Native):** Verificada con éxito (`BUILD SUCCESSFUL`). APK generado correctamente en `mobile-app/Pasted-Rol-Objective/artifacts/mobile/android/app/build/outputs/apk/release/app-release.apk`.
- **Arquitectura de Agentes:** Especificación completa de equipo de agentes IA definido en `AGENTS.md`.
