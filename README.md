# 🤖 BOT MT5 — Trading Automatizado con Discord

Bot de trading para MetaTrader 5 con integración Discord, backtesting histórico, paper trading y modo real.

---

## Inicio rápido

```bash
# Opción 1: script automático (instala dependencias y arranca)
start_bot.bat

# Opción 2: manual
pip install -r requirements.txt
python bot.py
```

Requiere MT5 abierto y credenciales en `.env`.

---

## Estructura del proyecto

```
bot.py                    # Punto de entrada — bot Discord + MT5
signals.py                # Dispatcher de estrategias
rules_config.json         # Configuración de pares y riesgo
mt5_client.py             # Cliente MetaTrader 5
charts.py                 # Generación de gráficos
secrets_store.py          # Credenciales cifradas
position_manager.py       # Gestión de posiciones MT5
backtest_tracker.py       # Tracking de señales

core/
  engine.py               # Motor principal de señales
  scoring.py              # Sistema de scoring y confianza
  risk.py                 # Gestión de riesgo y lot sizing
  filters.py              # Filtros de duplicados y cooldown
  replay_engine.py        # Motor de backtesting histórico
  circuit_breaker.py      # Circuit breaker y risk scaling

services/
  autosignals.py          # Loop de escaneo automático (90s)
  dashboard.py            # Dashboard web (puerto 8080)
  execution.py            # Ejecución de órdenes MT5
  logging.py              # Sistema de logging inteligente
  database.py             # Persistencia SQLite
  commands.py             # Comandos Discord adicionales

strategies/
  base.py                 # Clase base con indicadores comunes
  eurusd.py               # eurusd_simple (fallback)
  eurusd_asian_breakout.py  # Estrategia activa EURUSD ⭐
  xauusd.py               # xauusd_simple (activa)
  btceur_new.py           # btceur_simple (activa)
  btc_trend_pullback_v1.py  # Alternativa BTCEUR
  btceur_weekly_breakout.py # Alternativa BTCEUR
  eurusd_mtf.py           # EURUSD multi-timeframe (experimental)
  xauusd_psychological.py # Reversión niveles psicológicos (experimental)

tests/
  backtest_runner.py      # Script de backtesting CLI
  test_replay.py          # Tests del replay engine

logs/                     # Logs por sesión (rotación automática)
backtest_results/         # CSVs de resultados de backtest
```

---

## Configuración (.env)

```env
# Discord
DISCORD_TOKEN=...
GUILD_ID=...
AUTHORIZED_USER_ID=...

# MT5
MT5_LOGIN=...
MT5_PASSWORD=...
MT5_SERVER=...            # ej: ICMarkets-Demo

# Trading
AUTOSIGNALS=1
AUTOSIGNAL_INTERVAL=90    # segundos entre escaneos
AUTOSIGNAL_SYMBOLS=EURUSD,XAUUSD,BTCEUR

# Auto-ejecución
AUTO_EXECUTE_SIGNALS=0    # 0=paper trading, 1=órdenes reales
AUTO_EXECUTE_CONFIDENCE=HIGH

# Riesgo
MT5_RISK_PCT=0.5

# Dashboard
DASHBOARD_PORT=8080
DASHBOARD_HISTORY_HOURS=168   # 7 días de historial
```

---

## Estrategias activas

Validadas con backtest histórico (~7 meses de datos H1).

### EURUSD — `eurusd_asian_breakout` ⭐ (recomendada)

Breakout del rango asiático durante sesión de Londres.

| Parámetro | Valor |
|---|---|
| Timeframe | H1 |
| Sesión entrada | Londres 07:00–11:00 UTC |
| Rango | Asia 00:00–06:00 UTC |
| Entrada | Cierre > asia_high + buffer (BUY) / < asia_low - buffer (SELL) |
| SL | Extremo opuesto del rango asiático |
| TP | entry ± range × 1.5 |
| Filtros | No viernes, rango mínimo 5 pips, máximo 80 pips |
| Max señales | 1 por día |
| **Winrate backtest** | **56.5%** |
| **Profit factor** | **1.30** (3000 velas H1) |

### XAUUSD — `xauusd_simple`

Momentum en tendencia con filtro EMA200.

| Parámetro | Valor |
|---|---|
| Timeframe | H1 |
| Filtro tendencia | EMA20 > EMA50, precio > EMA200 |
| Entrada | RSI > 55 (BUY) / RSI < 45 (SELL) + ATR > media |
| SL | 2.0× ATR |
| TP | 5.0× ATR |
| R:R | 2.5 |
| Riesgo/trade | 0.60% |
| **Profit factor** | **1.28** (5000 velas H1) |

### BTCEUR — `btceur_simple` (baseline)

Tendencia EMA + MACD + volatilidad.

| Parámetro | Valor |
|---|---|
| Timeframe | H1 |
| Filtro tendencia | EMA20 > EMA50, precio > EMA200 |
| Entrada | MACD histogram en dirección + ATR > media |
| SL | 2.0× ATR |
| TP | 3.0× ATR |
| R:R | 1.5 |
| Riesgo/trade | 0.50% |
| **Profit factor** | **1.30** (5000 velas H1) |

### Estrategias alternativas disponibles

| Estrategia | Par | Estado |
|---|---|---|
| `eurusd_simple` | EURUSD | Fallback (PF 1.28) |
| `btc_trend_pullback_v1` | BTCEUR | Alternativa (PF 1.20) |
| `btceur_weekly_breakout` | BTCEUR | Experimental (PF 3.70, racha 29) |
| `xauusd_psychological` | XAUUSD | Experimental (WR 70%, PF negativo) |
| `eurusd_mtf` | EURUSD | Experimental (necesita más histórico) |

Para cambiar estrategia: editar `rules_config.json` → `"strategy": "nombre"`

---

## Dashboard

Accesible en `http://localhost:8080` mientras el bot está corriendo.

### Secciones

**KPIs superiores**
- Estado del sistema y uptime
- Señales de la sesión actual
- Posiciones abiertas en MT5
- Profit total (paper o real)

**Equity simulada**
- Calcula cómo habría evolucionado el balance si se hubieran ejecutado todas las señales
- Sparkline visual con la curva de equity
- Winrate paper trading en tiempo real (WIN/LOSS/OPEN)

**Circuit Breaker**
- Estado actual (activo/pausado)
- Pérdidas y wins consecutivos
- Multiplicador de riesgo actual

**Pares monitoreados**
- Estado de cada par (🟢/🟡/🔴)
- Total de señales y score promedio
- Tiempo desde última señal

**Tabla de señales (sesión actual)**
- Entry, SL, TP con colores
- R:R calculado
- Estado en tiempo real: WIN ✅ / LOSS ❌ / OPEN +45% (P&L como % del riesgo)
- Estado persistente — una vez WIN/LOSS no cambia aunque MT5 se desconecte

**Botón modo real** (esquina inferior derecha)
- 🟢 Activar modo real — abre modal de confirmación con aviso de dinero real
- 🔴 Desactivar — vuelve a paper trading
- Sin reinicio necesario

**Exportar CSV**
- Botón en la tabla y endpoint `/api/export`
- Descarga todas las señales de los últimos 7 días

### APIs disponibles

| Endpoint | Descripción |
|---|---|
| `GET /` | Dashboard HTML |
| `GET /api/metrics` | Métricas en JSON |
| `GET /api/history` | Historial de señales (7 días) |
| `GET /api/export` | Descarga CSV |
| `GET /api/enable-real` | Activa modo real |
| `GET /api/disable-real` | Desactiva modo real |

---

## Backtesting

```bash
# Modo interactivo
python tests/backtest_runner.py

# Directo
python tests/backtest_runner.py --symbol EURUSD --strategy eurusd_asian_breakout --bars 3000
python tests/backtest_runner.py --symbol XAUUSD --bars 5000
python tests/backtest_runner.py --all --bars 3000 --save

# Estrategias disponibles
# EURUSD : eurusd_simple, eurusd_advanced, eurusd_mtf, eurusd_asian_breakout
# XAUUSD : xauusd_simple, xauusd_reversal, xauusd_momentum, xauusd_psychological
# BTCEUR : btceur_simple, btc_trend_pullback_v1, btceur_weekly_breakout
```

Los resultados se guardan en `backtest_results/` como CSV.

---

## Circuit Breaker y Risk Scaling

Implementado en `core/circuit_breaker.py`. Se activa automáticamente:

| Situación | Acción |
|---|---|
| 2 pérdidas seguidas | Riesgo × 0.8 |
| 3 pérdidas seguidas | Riesgo × 0.5 |
| 4 pérdidas seguidas | **Pausa 24h automática** |
| 3 wins seguidos | Riesgo × 1.4 |
| 5 wins seguidos | Riesgo × 1.8 |

---

## Modo real vs Paper trading

El bot arranca siempre en **paper trading** (`AUTO_EXECUTE_SIGNALS=0`).

Para activar el modo real:
1. Abrir el dashboard en `http://localhost:8080`
2. Pulsar el botón verde **"Activar modo real"** (esquina inferior derecha)
3. Confirmar el modal de advertencia
4. Las señales MEDIUM-HIGH y HIGH se ejecutarán automáticamente en MT5

Para desactivar: pulsar el botón rojo o reiniciar el bot.

---

## Comandos Discord principales

```
/autosignals on|off|status   — Control del escaneo automático
/signal [EURUSD]             — Señal manual de un par
/positions                   — Posiciones abiertas en MT5
/close_position [ticket]     — Cerrar posición
/replay EURUSD 1000          — Backtest rápido desde Discord
/logs_info                   — Archivo de log actual
```

---

## Notas operativas

- El bot no genera señales de forex/oro el fin de semana (mercados cerrados)
- BTCEUR opera 24/7 y puede generar señales cualquier día
- EURUSD Asian Breakout solo opera lunes-jueves, sesión de Londres (07:00–11:00 UTC)
- Cooldown de 60 minutos por par — máximo 1 señal/hora por símbolo
- Límite de 5 trades por período de 12h (global)
- Los logs se guardan en `logs/` con rotación automática por sesión
- El dashboard persiste el historial de señales 7 días entre reinicios
