# Análisis completo — BOT-MT5 Mobile App

> Revisión actualizada el 26/06/2026. Refleja el estado tras las sesiones de implementación del 26/06/2026.

---

## Estado general del proyecto

La aplicación móvil es el sustituto de Discord para monitorizar y controlar el bot MT5 desde Android. El stack es: React Native + Expo (frontend), Express 5 + SQLite (backend), TypeScript estricto en ambos lados.

**La UI está completa. El servidor Express ya tiene todos los endpoints implementados y conectados a `bot_state.db`. Lo que falta es configuración de entorno, una pantalla de Settings en la app, y el rebuild del APK con los cambios.**

---

## ✅ Completamente implementado

### 1. UI — tres pantallas completas con diseño dark glassmorphism
- **Dashboard** (`app/(tabs)/index.tsx`): equity, balance, gráfico de equidad 24h, P&L del día, winrate, posiciones abiertas, pendientes, datos de cuenta MT5 (margen, margen libre, nivel de margen). Null-safe: usa `safeStatus` para no crashear durante el primer fetch.
- **Señales** (`app/(tabs)/signals.tsx`): lista de señales con filtrado por estado (Todas / Pendientes / Activas / Rechazadas), badge con contador de pendientes, botones de aceptar/rechazar por tarjeta.
- **Historial** (`app/(tabs)/history.tsx`): lista de trades cerrados ordenada por fecha, sumario con P&L total, ganadas, perdidas y Profit Factor.

### 2. Componentes (8 implementados)
`SignalCard`, `TradeCard`, `EquityChart`, `StatsCard`, `ConnectionBadge`, `ErrorBoundary`, `ErrorFallback`, `KeyboardAwareScrollViewCompat`.

### 3. Componente `ApiErrorBanner` (nuevo)
Banner visible en las tres pantallas:
- **Ámbar** `#f59e0b` cuando `usingMockData` es true — "⚠️ Datos de ejemplo — sin conexión real"
- **Rojo coral** cuando `apiError` tiene un mensaje — muestra el error de red

### 4. `TradingContext` refactorizado
- IP hardcodeada eliminada. Lee `EXPO_PUBLIC_API_URL` sin fallback; si no está configurada, falla visible.
- Estado ampliado con `status: BotStatus | null` (null durante el primer fetch), `apiError: string | null`, `usingMockData: boolean`.
- Token Bearer enviado en todas las peticiones (`EXPO_PUBLIC_API_SECRET`).
- Mock data cargada dinámicamente solo en `__DEV__` cuando la API no responde en el primer intento.

### 5. Mock data separada (`__mocks__/tradingData.ts`)
`MOCK_STATUS`, `MOCK_SIGNALS`, `MOCK_TRADES`, `generateMockEquityHistory` extraídos a su propio archivo. Solo se importan con `import()` dinámico desde `TradingContext` en modo desarrollo.

### 6. Servidor Express — `api-server/src/` (creado completo)
Todos los endpoints que necesita la app están implementados y leen de `bot_state.db`:

| Endpoint | Tabla SQLite | Descripción |
|---|---|---|
| `GET /api/healthz` | — | Health check público |
| `GET /api/status` | `session_stats` + `balance_snapshots` | Conexión MT5, balance, equity, margen, uptime |
| `GET /api/signals` | `enhanced_signals` | Señales pendientes y activas |
| `GET /api/trades` | `session_trades` | Trades cerrados |
| `GET /api/equityHistory` | `balance_snapshots` | Últimas 48 snapshots para el gráfico |
| `POST /api/signals/:id/accept` | `enhanced_signals` | Marca señal como ACCEPTED |
| `POST /api/signals/:id/reject` | `enhanced_signals` | Marca señal como REJECTED |

### 7. Autenticación Bearer Token (`src/lib/auth.ts`)
Middleware `requireAuth` aplicado a todas las rutas `/api/*` excepto `/healthz`. En dev sin `API_SECRET` configurado, deja pasar (para facilitar el desarrollo). En producción bloquea con 503 si el secret no está configurado.

### 8. CORS restringido (`src/app.ts`)
Acepta solo los orígenes listados en `ALLOWED_ORIGINS` (variable de entorno, separados por coma). En dev sin la variable, permite cualquier origen. En producción sin la variable, bloquea todo.

### 9. Lector SQLite directo (`src/lib/db.ts`)
Usa `node:sqlite` (Node 22+) para leer `bot_state.db` sin pasar por Drizzle ni PostgreSQL. Ruta configurable con `BOT_DB_PATH`. Sin dependencia de `lib/db` ni `lib/api-zod`.

### 10. Archivos de entorno documentados
- `api-server/.env` y `api-server/.env.example` — `PORT`, `BOT_DB_PATH`, `API_SECRET`, `ALLOWED_ORIGINS`, `LOG_LEVEL`
- `mobile/.env` y `mobile/.env.example` — `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_API_SECRET`

### 11. Dependencias rotas eliminadas
- `@workspace/api-client-react` eliminado de `package.json` y `tsconfig.json` del mobile
- `@workspace/db` eliminado del `package.json` del servidor
- Referencias a `lib/db` y `lib/api-zod` eliminadas del `tsconfig.json` del servidor

### 12. APK compilado (debug + release)
`android/app/build/outputs/apk/debug/app-debug.apk` y `app-release.apk` existen. Instalables en Android ahora mismo (con datos de ejemplo hasta que se configure `EXPO_PUBLIC_API_URL`).

### 13. Notificaciones push — 3 categorías con canales Android
`services/notifications.ts` implementa canales Android (`critical`, `signals`, `trades`) con prioridades correctas, deep linking al tab correspondiente al pulsar la notificación, y registro de token EAS con fallback graceful si no hay `projectId`.

### 14. Logger de producción (Pino + redact)
Redacta `authorization`, `cookie` y `set-cookie` de los logs. pino-pretty solo en dev. Configurado en servidor y en la configuración base del workspace.

### 15. Configuración de workspace y TypeScript
`pnpm-workspace.yaml` con `minimumReleaseAge: 1440`, `tsconfig.base.json` con `strictNullChecks`, `noImplicitAny`, `noImplicitReturns`, `useUnknownInCatchVariables`. EAS con tres perfiles (development, preview, production).

---

## 🔄 En desarrollo o planificado

### 1. Pantalla de Settings — URL y token configurables en la app
El análisis identifica que actualmente `EXPO_PUBLIC_API_URL` y `EXPO_PUBLIC_API_SECRET` se leen del `.env` en tiempo de build. Cualquier cambio de IP requiere recompilar. La idea es añadir una pantalla `/settings` donde el usuario introduzca la URL y el token, persistirlos con `SecureStore`, y hacer que `TradingContext` los lea en runtime.

### 2. Rebuild del APK con los nuevos cambios
El APK en disco fue compilado antes de los cambios de esta sesión (IP hardcodeada, sin banner de error, sin auth). Hay que recompilar para que los cambios lleguen al dispositivo.

### 3. `lib/api-spec` — spec OpenAPI para el contrato servidor/cliente
El README documenta este paquete como la fuente de verdad del contrato API. Actualmente no existe. Una vez definido, Orval generaría automáticamente schemas Zod y hooks React Query. Mantendría servidor y cliente sincronizados sin trabajo manual.

### 4. `lib/api-client-react` — hooks React Query generados
Dependencia del pipeline OpenAPI → Orval → hooks. No existe hasta que exista `lib/api-spec`. El `TradingContext` podría simplificarse notablemente usando estos hooks en lugar del fetch manual.

### 5. `lib/db` — schema Drizzle ORM
Documentado en el README como paquete separado para las migraciones y el schema tipado de la BD. Actualmente se lee SQLite directamente con queries en texto. Si el proyecto evoluciona hacia PostgreSQL, este paquete se activaría.

### 6. `artifacts/mockup-sandbox` — sandbox UI web con Vite + React
Mencionado en el README como herramienta para iterar el diseño sin dispositivo físico. No implementado.

### 7. Validación Zod en runtime para respuestas de la API
Los tipos `BotStatus`, `Signal`, `Trade`, `EquityPoint` están definidos en `TradingContext` pero no tienen schemas Zod. Una respuesta malformada del servidor causaría un crash silencioso. Pendiente de implementar como parte de `lib/api-zod`.

---

## 📋 10 cosas para dejar la app Android funcionando correctamente

### 1. 🔴 Configurar `.env` del servidor con los valores reales
Editar `artifacts/api-server/.env`:
```
PORT=5000
BOT_DB_PATH=C:/BOT-MT5/bot_state.db
API_SECRET=<token_generado_con_crypto.randomBytes(32).toString('hex')>
ALLOWED_ORIGINS=http://<IP_LAN_WINDOWS>:8081
```
Sin `BOT_DB_PATH` correcto el servidor arranca pero todos los endpoints devuelven 500.

### 2. 🔴 Configurar `.env` del cliente móvil con la misma IP y token
Editar `artifacts/mobile/.env`:
```
EXPO_PUBLIC_API_URL=http://<IP_LAN_WINDOWS>:5000
EXPO_PUBLIC_API_SECRET=<mismo_token_del_servidor>
```
Asegurarse de que el móvil y el PC Windows estén en la misma red Wi-Fi, o que haya un túnel (ngrok, Tailscale).

### 3. 🔴 Recompilar el APK con los cambios
Las modificaciones de `TradingContext`, `ApiErrorBanner`, auth y variables de entorno no están en el APK actual. Ejecutar:
```bash
cd artifacts/mobile
pnpm run build:apk:release
# o para preview rápido:
eas build --profile preview --platform android
```
Instalar el nuevo APK en el dispositivo.

### 4. 🔴 Compilar y arrancar el servidor Express
El `src/` del servidor es nuevo código fuente que nunca se ha compilado. Ejecutar:
```bash
cd artifacts/api-server
pnpm run build   # compila src/ → dist/
pnpm run start   # arranca el servidor
```
Verificar que responde en `http://localhost:5000/api/healthz` antes de arrancar la app.

### 5. 🔴 Verificar que `bot_state.db` tiene datos reales
El servidor lee las tablas `session_stats`, `balance_snapshots`, `enhanced_signals`, `session_trades`. Si el bot Python no ha generado ninguna sesión todavía, esas tablas estarán vacías o no existirán y los endpoints devolverán arrays vacíos (que es correcto, no es un error). Para tener datos reales, el bot Python necesita haber corrido al menos una sesión de autosignals.

### 6. 🟠 Añadir pantalla de Settings en la app
Crear `app/settings.tsx` con campos para URL del servidor y token, persistirlos en `SecureStore`, y hacer que `TradingContext` lea de `SecureStore` en runtime en lugar de solo de `process.env`. Esto permite cambiar la IP sin recompilar. Es la diferencia entre una app usable en movilidad y una que requiere al desarrollador cada vez que cambia la red.

### 7. 🟠 Añadir `sqlite3` o `better-sqlite3` como fallback para Node < 22
`src/lib/db.ts` usa `node:sqlite` que requiere Node 22+. Si el servidor corre en Node 20 (LTS actual más extendido), arrancará pero fallará al importar. Añadir detección de versión y fallback a `better-sqlite3`:
```typescript
// En db.ts, detectar versión y elegir implementación
const useNativeSqlite = parseInt(process.version.slice(1)) >= 22;
```
O bien documentar explícitamente Node 22 como requisito mínimo en el README.

### 8. 🟠 Abrir el puerto 5000 en el firewall de Windows
La app móvil se conecta al servidor Express por red LAN. Windows Defender Firewall bloquea el puerto 5000 por defecto para conexiones entrantes. Ejecutar en PowerShell (como administrador):
```powershell
New-NetFirewallRule -DisplayName "BOT-MT5 API Server" `
  -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
```
Sin este paso, el móvil obtiene "Connection refused" aunque el servidor esté corriendo.

### 9. 🟡 Añadir `sqlite3` a las dependencias del servidor y actualizar `build.mjs`
El `build.mjs` tiene `better-sqlite3` en la lista de `external` (no se bundlea). Si se decide usar `better-sqlite3` como fallback, hay que añadirlo a las dependencies del `package.json` del servidor e instalarlo con `pnpm install`. También añadirlo explícitamente a `external` en `build.mjs` si no está ya.

### 10. 🟢 Automatizar el arranque del servidor con el bot Python
Actualmente el servidor Express hay que arrancarlo manualmente por separado del bot Python. Añadir al `start_bot.bat` (o crear un `start_all.bat`) que arranque ambos:
```bat
start "API Server" cmd /k "cd /d C:\BOT-MT5\mobile-app\Pasted-Rol-Objective\artifacts\api-server && node --enable-source-maps dist/index.mjs"
start "Discord Bot" cmd /k "cd /d C:\BOT-MT5 && python bot.py"
```
Así arrancan juntos con un solo doble-click y no hay riesgo de olvidar arrancar el servidor.

---

## Resumen visual

| Área | Estado |
|---|---|
| Workspace config (pnpm, overrides) | ✅ Correcto |
| TypeScript config (estricto) | ✅ Correcto |
| EAS build profiles (dev/preview/prod) | ✅ Configurado |
| APK compilado (debug + release) | ✅ Existe — necesita rebuild |
| App móvil — Dashboard | ✅ Completo, null-safe |
| App móvil — Señales (filtros + accept/reject) | ✅ Completo |
| App móvil — Historial (PF, sumario) | ✅ Completo |
| Componentes (8 + ApiErrorBanner) | ✅ Completo |
| Notificaciones push (3 canales Android) | ✅ Implementado |
| TradingContext (polling, auth, error state) | ✅ Refactorizado |
| Mock data separada en `__mocks__/` | ✅ Separada |
| Banner de error/mock en 3 pantallas | ✅ Implementado |
| Servidor Express — 6 endpoints reales | ✅ Implementado |
| Conexión Express → `bot_state.db` | ✅ SQLite directo |
| Autenticación Bearer Token | ✅ Implementado |
| CORS restringido por env var | ✅ Implementado |
| Logger Pino + redact headers | ✅ Implementado |
| `.env` y `.env.example` ambos lados | ✅ Creados |
| Dependencias rotas (`api-client-react`, `@workspace/db`) | ✅ Eliminadas |
| `.env` con valores reales configurados | ❌ Pendiente (placeholder) |
| Servidor compilado y corriendo | ❌ Pendiente (`pnpm run build`) |
| APK recompilado con cambios nuevos | ❌ Pendiente |
| Puerto 5000 abierto en firewall Windows | ❌ Pendiente |
| Pantalla de Settings en la app | 📋 Planificado |
| `lib/api-spec` + codegen Orval | 📋 Planificado |
| `lib/api-client-react` (hooks generados) | 📋 Planificado |
| Sandbox UI web (`mockup-sandbox`) | 📋 Planificado |
| Arranque automático servidor + bot | 📋 Planificado |
