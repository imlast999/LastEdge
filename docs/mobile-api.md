# Mobile API — Comunicación entre Mobile App y Backend

Este documento describe la interfaz de red utilizada por la aplicación móvil (REST API / proxy) y los contratos JSON principales.

## Arquitectura

- Backend Python (LastEdge Engine): motor que escribe `bot_state.db` y procesa Research Runs.
- API Server (Express): puente y capa HTTP que expone endpoints REST seguros contra `bot_state.db`.
- Mobile App: cliente que consume la API para Dashboard, Trades y Research.

La comunicación es REST basada en JSON; autenticación por `Bearer <token>`.

## Endpoints principales (resumen)

- `GET /api/healthz` — estado básico, pública.
- `GET /api/status` — estado del bot, equity, connection (pública por diseño).
- `GET /api/signals` — señales pendientes/activas.
- `POST /api/signals/:id/accept` — marcar señal como aceptada.
- `POST /api/signals/:id/reject` — marcar señal como rechazada.
- `GET /api/trades` — historial de trades cerrados.
- `GET /api/equityHistory` — snapshots de equity para gráficas.
- `POST /api/backtests` — encolar Research Run (body: configuración básica).
- `GET /api/backtests/:id` — estado y resultados de un backtest/Research Run.

## Formatos JSON (ejemplos)

`GET /api/status` →

```json
{
  "connected": true,
  "account": {"balance": 12345.67, "equity": 12100.12, "margin_level": 220.5},
  "uptime": 3600
}
```

`GET /api/signals` → array de `Signal`:

```json
[{"id": 42, "symbol": "EURUSD", "side": "BUY", "entry": 1.1234, "tp": 1.1260, "sl": 1.1190, "status": "pending"}]
```

`POST /api/backtests` — cuerpo resumido:

```json
{
  "symbol": "EURUSD",
  "strategy": "eurusd_partial",
  "timeframe": "H1",
  "bars": 20000,
  "mode": "lastedge_protocol"
}
```

## Errores y status codes

- 200: OK (GET)
- 201: Created (POST que crea una task)
- 400: Bad Request (validación de payload)
- 401: Unauthorized (token faltante/incorrecto)
- 404: Not Found
- 500: Server Error (problema al leer DB o ejecutar task)

Los endpoints devuelven objetos `error` con `{code, message}` cuando procede.

## Versionado

Actualmente el API es internal y no cuenta con versión mayor. Para compatibilidad futura se recomienda prefixar rutas con `/v1/` y añadir `X-Api-Version` en cabeceras.

## Consideraciones operativas

- Polling: la app usa polling configurables (3/5/10/30s). Evitar llamadas paralelas que puedan bloquear la lectura de SQLite.
- Autenticación: usar token bearer; en dev el auth puede estar deshabilitado.
- Backtest tasks: encoladas en DB; el Engine procesa y actualiza el estado.
