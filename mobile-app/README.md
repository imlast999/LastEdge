<div align="center">

![LastEdge App banner](../branding/banners/LastEdge%20banner.png)

</div>

---

# LastEdge App

LastEdge App es el Mobile Control Center del ecosistema LastEdge: un centro de control portátil orientado a la monitorización de producción y a la investigación cuantitativa reproducible. Está diseñado para llevar el laboratorio de investigación al móvil, permitiendo:

- Monitorizar entornos de producción.
- Validar estrategias mediante backtests y análisis estadísticos.
- Ejecutar y consultar investigaciones reproducibles (Research Runs).
- Validar hipótesis y tomar decisiones basadas en evidencia, sin delegar la ejecución final al dispositivo móvil.

En una sola frase: Mobile Control Center + Portable Quantitative Research Lab para Production Monitoring y Strategy Validation.

---

**Philosophy**

Toda estrategia debe demostrar, mediante evidencia cuantitativa reproducible, que merece entrar en producción. En LastEdge App investigamos, documentamos y reutilizamos artefactos de investigación antes de promover una estrategia.

Puntos clave:

- La investigación es tan importante como la ejecución: las decisiones se fundamentan en resultados reproducibles, no en intuiciones.
- Toda investigación produce artefactos (configuración, métricas, curvas, conclusiones) que deben almacenarse y poder revisarse.
- No usamos herramientas aisladas: el flujo de trabajo es un protocolo completo que integra backtest, walk-forward, Monte Carlo y análisis de salida.
- La app refleja esta filosofía: centraliza la evidencia, facilita comparativas y permite reproducir investigaciones desde el móvil.

Esta sección documenta el comportamiento esperado del producto y el enfoque operativo para equipos de trading cuantitativo y auditoría.

---

**Características principales**

## Dashboard
- Estado del bot (conexión y uptime)
- Estado MT5 (margin, free margin, margin level)
- Portfolio: balance, equity y snapshots de drawdown
- Indicadores de riesgo y exposición
- Gráfica de equity (últimos snapshots)
- Resumen de posiciones abiertas y señales pendientes
- Banners de salud del sistema y errores

## Trades
- Pending Signals: `SignalCard` con aceptación/rechazo (escribe flag en DB)
- Closed Trades: historial con `TradeCard` y resumen de P&L
- Datos sincronizados desde producción (lectura del DB vía API)

## Research Lab
La sección de investigación ofrece tres modos operativos documentados a continuación.

---

**Investigation Modes**

Los modos implementados en LastEdge App están diseñados para cubrir desde validaciones rápidas hasta pipelines completos de investigación:

### Quick Validation
- Propósito: validación rápida y comprobaciones de hipótesis.
- Qué ejecuta: backtests acotados sobre conjuntos reducidos de datos.
- Cuándo usarlo: antes de lanzar investigaciones largas o para confirmar cambios menores en parámetros.

### LastEdge Protocol
- Propósito: ejecutar el pipeline de investigación recomendado y completo.
- Flujo (recomendado antes de promover a producción):

Backtest
↓
Walk Forward
↓
Monte Carlo
↓
Exit Research

- Qué hace: encadena backtest, walk-forward y análisis estadístico; ejecuta Monte Carlo para estimar riesgos y genera métricas y artefactos que se almacenan en el Run.
- Uso: validación exhaustiva de estrategias, análisis de estabilidad y decisión para promover a producción.

### Custom Investigation
- Propósito: permitir control manual y flexibilidad a investigadores avanzados.
- Qué permite: seleccionar fases individuales del protocolo (por ejemplo, sólo Monte Carlo o sólo walk-forward).
- Uso: depuración, replicación de pasos concretos y auditoría experimental.

---

**Research Runs**

Un Research Run representa una ejecución completa y reproducible del proceso de investigación. Cada Run almacena:

- Configuración: parámetros, seed, periodo de datos, estrategia y metadatos.
- Resultados: métricas agregadas (winrate, profit factor, net pips, drawdown percentiles).
- Gráficos y artefactos: curva de equity, distribuciones de outcomes, heatmaps, trade timeline.
- Conclusiones: anotaciones, observaciones y un score de estabilidad cuando esté disponible.

Beneficios clave:

- Reproducibilidad: cualquier Run puede volver a ejecutarse con la configuración exacta.
- Historial: se construye un registro de investigaciones que permite comparativas en el tiempo.
- Auditoría: los artefactos permiten a analistas y a risk managers revisar y validar decisiones.

LastEdge App muestra y organiza Research Runs para facilitar comparativas y seguimiento en dispositivos móviles.

---

**Research-first philosophy (nuevo paradigma)**

Antes, backtest, Monte Carlo, walk-forward y exit research se veían como herramientas separadas. En LastEdge ese conjunto de herramientas se convierte en un único proceso investigativo centrado en el Run. El usuario piensa en investigaciones, no en herramientas sueltas. Este cambio de paradigma es uno de los pilares del proyecto: consolidar evidencia, fomentar reproducibilidad y reducir errores humanos en la promoción a producción.

---

**Identity Visual**

La identidad visual de LastEdge App se diseñó para trasladar los valores del proyecto: ingeniería, estabilidad, investigación y claridad de datos.

Directrices resumidas:

- Paleta sobria con alto contraste para favorecer la lectura de datos.
- Tipografía monoespaciada/tabular para valores numéricos y alineado de columnas.
- Iconografía clara y consistente (referencia al icono oficial abajo).
- Componentes con jerarquía visual orientada a la interpretación rápida de métricas.

Referencias a recursos (añadir los ficheros en el repo):
- Banner: `../branding/banners/LastEdge banner.png`
- Icono de la app: `../branding/icons/app/source/LastEdge icon.png`

---

**Capturas y recursos gráficos (estructura preparada)**

Colocar imágenes en `artifacts/mobile/assets/screens/` y referenciarlas con las rutas sugeridas. No se crean imágenes aquí; deje los ficheros en el repositorio para que el README los muestre.

- [COLOCAR IMAGEN: Dashboard] → ./assets/screens/dashboard.png
- [COLOCAR IMAGEN: Trades - Pending] → ./assets/screens/trades_pending.png
- [COLOCAR IMAGEN: Trades - Closed] → ./assets/screens/trades_closed.png
- [COLOCAR IMAGEN: Lab - Backtest Form] → ./assets/screens/lab_backtest_form.png
- [COLOCAR IMAGEN: Lab - Backtest Results] → ./assets/screens/lab_backtest_results.png
- [COLOCAR IMAGEN: Investigation Detail] → ./assets/screens/investigation_detail.png
- [COLOCAR IMAGEN: Settings] → ./assets/screens/settings.png

Si alguna captura no existe, el README mostrará el placeholder con la ruta sugerida.

---

**Arquitectura (resumen)**

Mobile App
↓ HTTP polling / POST
REST API (Express / Node)
↓ lectura/escritura
LastEdge Engine (Python) — `bot_state.db` (SQLite)
↓ MT5 API
MT5
↓ Broker

La app nunca conecta MT5 directamente: todas las acciones pasan por la API y la base de datos compartida.

---

**Navegación**

Estructura principal: Tab bar con `Dashboard`, `Trades`, `Lab` (Backtests/Research) y botón de `Settings` en la cabecera.

Flujo típico:
Dashboard → Trades → Lab → Settings (pantalla completa)

Detalle: `Trades` tiene sub-pestañas `Pending` y `Closed`. `Lab` expone formularios, polling de tareas y resultados.

---

**Capturas y recursos gráficos**

Colocar imágenes en la carpeta de assets del móvil y referenciarlas aquí. No se incluyen imágenes en el repo por defecto; añadir los ficheros con estos nombres para que se muestren:

- [COLOCAR IMAGEN: Dashboard] → ./assets/screens/dashboard.png
- [COLOCAR IMAGEN: Trades - Pending] → ./assets/screens/trades_pending.png
- [COLOCAR IMAGEN: Trades - Closed] → ./assets/screens/trades_closed.png
- [COLOCAR IMAGEN: Lab - Backtest Form] → ./assets/screens/lab_backtest_form.png
- [COLOCAR IMAGEN: Lab - Backtest Results] → ./assets/screens/lab_backtest_results.png
- [COLOCAR IMAGEN: Settings] → ./assets/screens/settings.png

Si una captura no existe, el README mostrará el texto del placeholder y la ruta sugerida.

---

**Instalación (desarrollo)**

Requisitos:
- Node.js 20+ (recomendado)
- pnpm (opcional, el repositorio usa pnpm workspace)
- Expo CLI / Expo Application Services para builds (EAS) si se desean push notifications reales

Pasos rápidos (desde la raíz del repo):

```powershell
cd mobile-app/Pasted-Rol-Objective/artifacts/mobile
pnpm install           # o npm/yarn si no usa pnpm
pnpm expo start        # lanza Metro / Expo dev tools
``` 

Construir APK (Android):

```powershell
# Requiere EAS config si se desea push estable
pnpm expo prebuild     # opcional: para builds nativos
eas build -p android   # usando EAS (configurar projectId en eas.json)
``` 

Build iOS: requiere macOS + EAS; en este repositorio iOS no ha sido probado regularmente.

Nota: las dependencias y versiones concretas están definidas en `artifacts/mobile/package.json`.

---

**Configuración**

Parámetros esenciales (en la app, `Settings`):
- `API URL`: URL pública o interna del `api-server` (ej. `https://mi-servidor:3000`)
- `API Token`: token Bearer para autenticación con el servidor
- `Polling interval`: 3s / 5s / 10s / 30s
- `Mock data`: modo desarrollo (fallback cuando API inaccesible)

Conexión con backend:
- El `api-server` expone `GET /api/status`, `GET /api/signals`, `GET /api/trades`, `GET /api/equityHistory`, y endpoints para backtests y acciones de señales.
- Las requests (salvo `/api/healthz` y `/api/status`) requieren `Authorization: Bearer <token>`.

Notificaciones:
- Local notifications configuradas vía `expo-notifications`.
- Para push reales es necesario configurar EAS y un `projectId` en `eas.json`.

---

**Estructura del proyecto (resumen relevante)**

- `app/` — Entradas de pantalla y _layout (Expo Router)
- `components/` — Componentes reutilizables (`SignalCard`, `TradeCard`, `EquityChart`)
- `context/` — `TradingContext` y `SettingsContext` (polling, estado global)
- `services/` — Clientes API, notificaciones y utilidades
- `constants/` — Tokens y listas para formularios (símbolos, estrategias)
- `i18n/` — Traducciones EN/ES
- `__mocks__/` — Datos de desarrollo

Evitar listar archivos irrelevantes; los ficheros de build y artefactos nativos están fuera de `app/`.

---

**Tecnologías**

- React Native (Expo / SDK 54)
- Expo Router (file-based routing)
- TypeScript
- Expo Notifications, Expo Haptics
- AsyncStorage para persistencia local
- Express (API server) + SQLite (bot_state.db) para puente con el motor Python

---

**Estado del proyecto**

- Desarrollo activo.
- El **Dashboard** móvil está completamente funcional (equity, estados, conexión, señales pendientes).
- El **Research Lab** (Backtests + Monte Carlo) es funcional para ejecuciones remotas básicas y visualización de resultados, pero sigue en evolución (mejoras en comparativas y artefactos están en progreso).

Limitaciones conocidas:
- iOS no se ha probado/compilado regularmente en CI.
- No existe todavía un centro de notificaciones en-app.
- Algunas listas de estrategias están hardcodeadas y requieren sincronización con el backend.

---

**Roadmap**

Dirección estratégica del producto (sin fechas). Estas iniciativas guiarán el desarrollo a corto y medio plazo:

- Research Run History: historial completo y filtros avanzados para revisar y comparar ejecuciones pasadas.
- Push Notifications: integración y enriquecimiento de notificaciones (canales críticos, acciones rápidas desde notificación).
- Live Analytics: métricas en tiempo real y streaming ligero para indicadores clave en producción.
- Multi-device Synchronization: sincronización entre múltiples dispositivos del mismo usuario y roles de lectura/operación.
- Strategy Comparison: vistas para comparar variantes, parámetros y resultados de Runs en paralelo.
- Protocol Scheduling: planificación y automatización de investigaciones mediante calendarios o triggers.
- Cloud Research: integración opcional con infraestructura de cómputo remoto para ejecutar investigaciones pesadas.
- Remote Investigation Management: panel para gestionar la cola de investigaciones, prioridades y permisos.

Estas entradas representan la dirección del proyecto; su puesto en la hoja de ruta y prioridad estará sujeto a evaluación de recursos y dependencia del motor central.

---

**Cómo contribuir**

- Fork + branch con prefijo `mobile/`.
- Mantener consistencia con TypeScript y linters del proyecto.
- Añadir tests cuando sea apropiado (componentes y utilidades).
- Para cambios en la API, coordinar con el repo del motor (LastEdge Engine) y documentar cambios de contrato.

Pull request checklist:
- Describe el cambio y su impacto en la app y en la API
- Incluir capturas o paths de assets nuevas
- Actualizar `i18n/translations.ts` si se añaden strings

---

**Licencia**

La aplicación mantiene la licencia del repositorio raíz. Consulte el archivo `LICENSE` en la raíz del proyecto.

---

**Verificación final (comprobaciones realizadas)**

- He actualizado la identidad a "LastEdge App" en todo el README.
- El documento refleja el estado actual del código en `mobile-app/Pasted-Rol-Objective/artifacts/mobile`.
- He dejado placeholders claros y rutas recomendadas para las capturas (no se han creado imágenes nuevas).
- No se ha modificado el README principal del repositorio.

Si quieres, puedo:
- añadir los placeholders de imagen como archivos PNG vacíos en `mobile-app/Pasted-Rol-Objective/artifacts/mobile/assets/screens/` (para que Git detecte rutas),
- o ejecutar una búsqueda rápida por referencias a nombres antiguos para confirmar que no quedan menciones antiguas en el código.


### API server

| Package | Version | Purpose |
|---|---|---|
| `express` | ^5.2.1 | HTTP server |
| `cors` | ^2.8.6 | CORS middleware |
| `pino` | ^9.14.0 | Structured JSON logger |
| `pino-http` | ^10.5.0 | HTTP request logging |
| `pino-pretty` | ^13.1.3 | Dev log formatting |
| `esbuild` | 0.27.3 | TypeScript bundler |
| `node:sqlite` | built-in (Node 22) | SQLite reader — **requires Node 22+** |

---

## 10. Screenshots

> No screenshots are currently included in the repository.

The expected screens to capture for documentation:

| Screen | What to show |
|---|---|
| Dashboard | MT5 connected badge + equity card + chart + 4 KPI cards |
| Trades / Pending | At least one `SignalCard` with pending state |
| Trades / Closed | Summary bar + 2-3 TradeCards |
| Backtests form | Symbol/strategy/CB selectors |
| Backtests result | Completed result with Monte Carlo verdict card |
| Settings | Server section + test result |
| ApiErrorBanner | Red banner visible on any screen |
| ErrorFallback | Dev mode stack trace modal |

---

## 11. Roadmap

Features that are partially implemented or planned based on the current codebase:

- **`eurusd_partial` in backtest form** — `constants/backtest.ts` and `routes/bot.ts#/strategies` both list `eurusd_simple` as the default EURUSD strategy. Neither has been updated to reflect the v1.1 active strategy. This is the most immediate gap.
- **TanStack Query migration** — `@tanstack/react-query` is installed and `QueryClient` is initialized in `_layout.tsx`, but `TradingContext` still uses manual `setInterval` + `fetch`. A migration to `useQuery` would simplify polling logic significantly.
- **Light theme** — `colors.ts` defines both `light` and `dark` keys with identical values. The infra (`useColors` reads `useColorScheme()`) is ready; only the palette tokens need to differ.
- **Live floating P&L** — `BotStatus` includes `equity` but there is no per-trade floating P&L. Would require an additional endpoint or augmented `/api/signals`.
- **Confirmation dialog before accept** — `SignalCard` calls `onAccept` immediately on tap. A confirmation step would prevent accidental order acceptance.
- **Strategy analytics view** — The data is available in `session_trades` and `trade_journal` but there is no per-strategy breakdown screen in the app.
- **Zod validation** — `zod` is installed but not used. API responses are cast with `as T` in `TradingContext`. Adding validation would catch schema drift.

---

## 12. Project State

| Dimension | Status |
|---|---|
| Functionality | Functional MVP — all core monitoring features work end-to-end |
| Stability | Stable for personal use on Android; not production-hardened |
| iOS support | Not built or tested |
| Test coverage | None — no test files exist in the mobile app |
| Build system | Android APK via Gradle (`assembleRelease`) or EAS local build |
| Node requirement | **Node 22+** required by the API server (`node:sqlite` built-in) |
| API server | Must run on the same machine as the Python bot (shares `bot_state.db`) |

**What is missing for a stable v1.0 release:**
1. Update strategy list in `constants/backtest.ts` and `routes/bot.ts` to include `eurusd_partial`
2. At least smoke tests for the API server endpoints
3. A real light color palette or explicit dark-only declaration
4. iOS build verification
5. Confirmation dialog on signal accept

---

## 13. Current Limitations

| Limitation | Detail |
|---|---|
| No direct MT5 connection | The app talks to the API server, which talks to the DB. The bot must be running for data to be current. |
| No real-time push | Data updates via polling only. There is no WebSocket or server-sent events. Minimum latency = poll interval (default 5s). |
| API server not exposed remotely by default | Requires manual port forwarding or VPN for access outside the local network. |
| `bot_state.db` schema dependency | The app reads tables (`session_trades`, `enhanced_signals`, `balance_snapshots`, `session_stats`) that must exist and be populated by the Python bot. If the bot has never run, all data will be empty. |
| Signal accept ≠ immediate execution | Accepting a signal writes a DB flag. The Python bot reads it on its next ~20s cycle. There is no acknowledgment back to the app. |
| Monte Carlo says "5,000 simulations" | The translation string says "Monte Carlo · 5,000 simulations" but the actual Python backend runs 2,000. The string is incorrect. |
| Strategy list is hardcoded | `routes/bot.ts#/strategies` returns a static array. Adding `eurusd_partial` requires a manual code change in the API server. |
| `eurusd_asian_breakout` is the default strategy | `constants/backtest.ts` sets `DEFAULT_STRATEGY.EURUSD = "eurusd_asian_breakout"`, which is a discarded strategy. This is a stale default. |
| No offline caching | If the API is unreachable, previous data is lost on refresh (except for mock data in dev mode). |
| `react-native-svg` installed but unused | The equity chart uses a custom `View`-based rendering instead of SVG. The dependency adds bundle size without benefit. |

---

## 14. Design Decisions

**Why a separate API server instead of connecting directly to MT5 or the Python bot?**  
The Python bot writes to `bot_state.db` but does not expose an HTTP API. Rather than modifying the bot, a thin Express bridge was added that reads the same DB. This keeps the bot architecture unchanged and the mobile app loosely coupled.

**Why `node:sqlite` instead of `better-sqlite3`?**  
Node 22 ships SQLite as a built-in module with a synchronous API. This eliminates a native dependency that would require compilation per platform. The tradeoff is a hard Node 22+ requirement.

**Why polling instead of WebSockets?**  
Polling at 5s intervals is sufficient for the monitoring use case. WebSockets would require changes to both the Python bot and the API server. The complexity is not justified for a single-user tool.

**Why no chart library (react-native-svg, Victory, recharts)?**  
The equity chart uses custom `View` segments to avoid adding a large dependency for a single use. `react-native-svg` is installed but unused — this decision should be revisited if more charts are needed.

**Why file-based routing (Expo Router) instead of React Navigation directly?**  
Expo Router provides a simpler developer experience for a small app with a predictable screen structure. The tab + stack combination maps naturally to the app's navigation needs.

**Why `TradingProvider` as a single global context?**  
All screens need the same data (status, signals, trades). A single provider avoids prop drilling and redundant fetches. The tradeoff is that a polling error anywhere affects all screens.

**Why `AsyncStorage` at key `@bot_mt5_settings_v2`?**  
The `_v2` suffix indicates a schema migration from `v1` (which lacked `language` and `serverToken`). The `SettingsProvider` reads both keys and merges, so users upgrading from v1 don't lose their settings. The old name (`@bot_mt5_settings`) reflects the pre-rebranding project name.

---

## 15. Developer Observations

Items that should be addressed before the next development phase, in priority order:

### Critical
1. **`constants/backtest.ts` — stale strategy list:** `eurusd_asian_breakout` is set as `DEFAULT_STRATEGY.EURUSD` and listed first in `STRATEGIES_BY_SYMBOL.EURUSD`. This is a discarded strategy. The default should be `eurusd_partial` and the list should reflect the current active + reference strategies.

2. **`routes/bot.ts#/strategies` — hardcoded and outdated:** The strategy list in the API server includes `eurusd_simple`, `eurusd_mtf`, `eurusd_asian_breakout` but not `eurusd_partial`. Any backtest launched from the mobile app for EURUSD will use the wrong strategy set. This needs to be updated whenever strategies change in `signals.py`.

3. **`translations.ts` — Monte Carlo count mismatch:** `monteCarloSimulations` says "5,000 simulations" in both EN and ES. The Python backend (`core/exit_research/runner.py`) runs 2,000 simulations. Either the translation or the backend count needs alignment.

### High priority
4. **`@tanstack/react-query` installed but unused:** `QueryClient` is initialized in `_layout.tsx` but `TradingContext` uses manual `setInterval`. The package adds ~50KB to the bundle for no benefit. Either migrate to `useQuery` or remove the dependency.

5. **`react-native-svg` installed but unused:** ~300KB native dependency. Remove if no SVG charts are planned, or migrate `EquityChart` to use it.

6. **`expo-glass-effect`, `expo-image`, `react-native-worklets` installed but unused:** Dead dependencies increasing bundle size.

7. **No confirmation dialog on signal accept:** Tapping "ACEPTAR" in `SignalCard` immediately fires the API call. For a tool that influences trading decisions, at minimum an `Alert.alert` confirmation step should exist.

### Medium priority
8. **Light theme tokens are identical to dark:** `colors.ts` defines `light` and `dark` with the same values. Either implement a real light palette or remove the `light` key and document the app as dark-only.

9. **`SettingsScreen` footer says `t("mockData")`:** The footer text renders `{t("tradingBotMonitor")} · {t("mockData")}` regardless of actual data mode. This looks like a copy-paste error — it should probably show the app version or a copyright line.

10. **`AsyncStorage` key still uses `@bot_mt5_settings_v2`:** Post-rebranding, this key should ideally be `@lastedge_settings_v2`. A migration would be needed to avoid resetting user settings.

11. **`pips` calculation in `routes/bot.ts#/trades` is symbol-agnostic:** The trade pips are calculated as `(closePrice - openPrice)` without accounting for pip size per symbol. For EURUSD this is wrong (needs ×10000), for XAUUSD it's different, for BTCEUR it's different again.

12. **`zod` installed but not used for API response validation:** API responses are cast with `as T` which silently swallows schema changes from the server. Adding Zod schemas would catch mismatches early.

### Low priority
13. **No test coverage:** Neither the mobile app nor the API server has any test files. Unit tests for `apiConfig.ts`, `connectionTest.ts`, and the Express routes would catch regressions quickly.

14. **`TradeCard` formats dates in `es-ES` locale hardcoded:** `formatDate()` in `TradeCard.tsx` uses `d.toLocaleDateString("es-ES", ...)`. This should respect the app language setting.

15. **`SignalCard` precision logic uses string includes:** `signal.symbol.includes("JPY") || signal.symbol.includes("XAU")` to pick decimal places. This is fragile — a proper pip size lookup from a constants map would be cleaner.

---

## Installation and Running

### Requirements
- Node.js **22+** (API server uses `node:sqlite` built-in)
- pnpm 9+
- Expo CLI
- Android device or emulator (iOS not tested)
- LastEdge Python bot running and writing to `bot_state.db`

### API server

```bash
cd artifacts/api-server
cp .env.example .env
# Edit .env: set PORT, API_SECRET, BOT_DB_PATH
pnpm run build
pnpm run start
```

`.env` required fields:
```env
PORT=5000
API_SECRET=your_secret_token
BOT_DB_PATH=C:/BOT-MT5/bot_state.db
NODE_ENV=development
```

### Mobile app (development)

```bash
cd artifacts/mobile
cp .env.example .env
# Edit .env: set EXPO_PUBLIC_API_URL and EXPO_PUBLIC_API_SECRET
pnpm install
pnpm run start
# Scan QR with Expo Go or run on connected device
```

### Build APK

```bash
cd artifacts/mobile
pnpm run build:apk:release
# Output: android/app/build/outputs/apk/release/app-release.apk
```

---

<div align="center">
<sub>LastEdge App — centro de control móvil y laboratorio de investigación portátil para el ecosistema LastEdge</sub>
</div>
