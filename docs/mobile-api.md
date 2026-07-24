# Mobile & Web REST API — Contract Specification

> **Authoritative Single Source of Truth for REST API Contracts & Telemetry Interfaces**

---

## 1. Overview & Architecture

LastEdge exposes REST API contracts through two HTTP service layers:

1. **Express REST API Server (`mobile-app/.../api-server/`):** Running on port 3000 by default. Provides secure JSON API endpoints consumed by the React Native Mobile Application. Interacts directly with `bot_state.db` and the `backtest_results/` filesystem.
2. **Python Web Dashboard Service (`services/dashboard.py`):** Running on port 8080 by default (`ThreadingHTTPServer`). Provides real-time HTML dashboard views and AJAX metrics endpoints for web browsers.

Authentication is enforced via `Authorization: Bearer <token>` headers on production API routes.

---

## 2. Express Mobile REST API Endpoints (Port 3000)

### System & Status Endpoints

#### `GET /api/healthz`
Public health check endpoint.
- **Response `200 OK`:**
```json
{
  "status": "ok",
  "service": "lastedge-api-server",
  "timestamp": "2026-07-23T00:00:00.000Z"
}
```

#### `GET /api/status`
Public status endpoint returning MT5 connection, balance, equity, margin, and execution quality telemetry.
- **Response `200 OK`:**
```json
{
  "connected": true,
  "uptime": "14h 22m",
  "balance": 10540.25,
  "equity": 10612.80,
  "margin": 420.00,
  "freeMargin": 10192.80,
  "executionQuality": {
    "avgLatency": 45,
    "avgSlippage": 0.2,
    "successRate": 99.9
  }
}
```

#### `GET /api/risk-dashboard` *(Implemented P0.2)*
Detailed risk exposure dashboard returning account drawdown, circuit breaker state, margin levels, open position risk breakdowns, and portfolio risk totals.
- **Response `200 OK`:**
```json
{
  "balance": 10540.25,
  "equity": 10612.80,
  "margin": 420.00,
  "freeMargin": 10192.80,
  "marginLevel": 2526.86,
  "peakEquity": 10800.00,
  "currentDrawdownPct": 1.73,
  "maxDrawdownPct": 3.45,
  "circuitBreaker": {
    "triggered": false,
    "consecutiveLosses": 1,
    "pauseUntil": null
  },
  "portfolioRisk": {
    "amount": 150.00,
    "pct": 1.41
  },
  "openPositions": [
    {
      "symbol": "EURUSD",
      "ticket": 984521,
      "volume": 0.10,
      "risk_pct": 0.71,
      "risk_amount": 75.00,
      "has_sl": true
    }
  ]
}
```

---

### Trading & Signal Endpoints

#### `GET /api/signals`
Retrieves pending and active trading signals from the `enhanced_signals` database table.
- **Response `200 OK`:**
```json
[
  {
    "id": "142",
    "symbol": "EURUSD",
    "type": "BUY",
    "entry": 1.08500,
    "takeProfit": 1.09200,
    "stopLoss": 1.08150,
    "status": "pending",
    "rrRatio": 2.00,
    "timestamp": "2026-07-23T00:15:00.000Z",
    "lot": 0.15
  }
]
```

#### `POST /api/signals/:id/accept`
Marks a proposed signal as `ACCEPTED` for automated execution.
- **Response `200 OK`:** `{ "ok": true, "message": "Signal accepted" }`

#### `POST /api/signals/:id/reject`
Marks a proposed signal as `REJECTED`.
- **Response `200 OK`:** `{ "ok": true, "message": "Signal rejected" }`

#### `GET /api/trades`
Returns closed trade history from `session_trades` and `trade_journal`.
- **Response `200 OK`:**
```json
[
  {
    "id": "512",
    "symbol": "EURUSD",
    "type": "BUY",
    "openPrice": 1.08200,
    "closePrice": 1.08750,
    "pips": 55.0,
    "profit": 55.00,
    "closeReason": "TAKE_PROFIT",
    "closedAt": "2026-07-22T18:30:00.000Z",
    "lot": 0.10,
    "latencyMs": 42,
    "slippagePips": 0.1
  }
]
```

#### `GET /api/equityHistory`
Returns time-series balance and equity snapshots for historical chart rendering.
- **Response `200 OK`:**
```json
[
  { "time": 1784764800000, "value": 10000.00 },
  { "time": 1784768400000, "value": 10055.00 }
]
```

---

### Research Lab & Task Queue Endpoints *(Implemented P0.2)*

#### `POST /api/backtests`
Queues a new backtest or research task into `backtest_tasks`.
- **Request Body:**
```json
{
  "symbol": "EURUSD",
  "strategy": "eurusd_partial",
  "bars": 20000,
  "mode": "lastedge_protocol"
}
```
- **Response `200 OK`:** `{ "ok": true, "taskId": 8, "message": "Task queued" }`

#### `GET /api/research/exit-research`
Lists all completed Exit Research runs in `backtest_results/exit_research/`.
- **Response `200 OK`:**
```json
{
  "ok": true,
  "runs": [
    {
      "run_id": "20260702_225143",
      "generated_at": "2026-07-02T22:51:43Z",
      "symbol": "EURUSD",
      "variant_count": 13,
      "best_variant": "partial_close",
      "best_pf": 1.85,
      "best_stability": 28.5
    }
  ]
}
```

#### `POST /api/research/exit-research`
Queues an Exit Research execution task.
- **Request Body:** `{ "symbol": "EURUSD", "strategy": "eurusd_partial" }`
- **Response `200 OK`:** `{ "ok": true, "taskId": 9, "message": "Exit research task queued successfully" }`

#### `GET /api/research/exit-research/:runId`
Returns complete summary JSON for a specific Exit Research run, including comparison tables and Walk-Forward degradation tables.

#### `GET /api/research/exit-research/:runId/trades/:variant`
Returns individual trade logs for a specific variant (`?variant=partial_close`).

#### `GET /api/research/exit-research/:runId/montecarlo?variant=partial_close`
Generates 2,000 Monte Carlo bootstrap simulation percentile curves (`p5`, `p25`, `p50`, `p75`, `p95`) and original equity curve.

---

## 3. Python Web Dashboard HTTP Endpoints (Port 8080)

| Method | Endpoint Path | Description |
|---|---|---|
| `GET` | `/` or `/dashboard` | Standalone HTML Dashboard UI with Chart.js equity curve and signals table |
| `GET` | `/api/metrics` | Returns current `DashboardMetrics` JSON |
| `GET` | `/api/data` | Returns complete dashboard payload (metrics + history) |
| `GET` | `/api/history?hours=168` | Returns signal history log for the specified lookback window |
| `GET` | `/api/equity` | Real-time balance and floating equity snapshot |
| `GET` | `/api/execution-status` | Dynamic auto-execution toggle and confidence settings |
| `GET` | `/api/export` | Downloads trade signals history as a UTF-8 CSV attachment |
| `GET` | `/api/set-language?lang=es` | Hot-swaps UI language between English (`en`) and Spanish (`es`) |

---

## 4. Error Response Format

All REST endpoints return standardized HTTP status codes and JSON error objects:

```json
{
  "ok": false,
  "message": "Detailed error explanation string",
  "code": "INVALID_PARAMETER"
}
```

### HTTP Status Code Conventions:
- **`200 OK`**: Request succeeded.
- **`400 Bad Request`**: Malformed payload, invalid parameter, or security path traversal blocked.
- **`401 Unauthorized`**: Missing or invalid Bearer token.
- **`404 Not Found`**: Run ID or requested resource does not exist.
- **`500 Internal Server Error`**: Database error or unexpected server exception.
