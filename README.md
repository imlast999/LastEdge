# 🤖 BOT MT5 — Trading Automatizado con Discord

Bot de trading para MetaTrader 5 con integración Discord, backtesting histórico, paper trading y modo real. Monitorea EURUSD, XAUUSD y BTCEUR en H1 con señales automáticas, dashboard web en tiempo real y circuit breaker integrado.

---

## Inicio rápido

```bash
# Opción recomendada: script automático (instala dependencias y arranca)
start_bot.bat

# Manual
pip install -r requirements.txt
python bot.py
```

Requiere MT5 abierto y credenciales en `.env`.

---

## Estructura del proyecto

```
bot.py                      # Punto de entrada — bot Discord + MT5
signals.py                  # Dispatcher de estrategias
rules_config.json           # Configuración de pares y riesgo
mt5_client.py               # Cliente MetaTrader 5
charts.py                   # Generación de gráficos
secrets_store.py            # Credenciales cifradas
position_manager.py         # Gestión de posiciones MT5
backtest_tracker.py         # Tracking de señales
audioop_patch.py            # Compatibilidad Python 3.13

core/
  engine.py                 # Motor principal de señales
  scoring.py                # Sistema de scoring y confianza
  risk.py                   # Gestión de riesgo y lot sizing
  filters.py                # Filtros de duplicados y cooldown
  replay_engine.py          # Motor de backtesting histórico
  circuit_breaker.py        # Circuit breaker y risk scaling

services/
  autosignals.py            # Loop de escaneo automático
  dashboard.py              # Dashboard web (puerto 8080)
  execution.py              # Ejecución de órdenes MT5
  logging.py                # Sistema de logging inteligente
  database.py               # Persistencia SQLite
  commands.py               # Comandos Discord adicionales
  news_filter.py            # Filtro de noticias de alto impacto

strategies/
  base.py                   # Clase base con indicadores comunes
  eurusd.py                 # eurusd_simple (fallback EURUSD)
  eurusd_asian_breakout.py  # ⭐ Estrategia activa EURUSD
  xauusd.py                 # xauusd_simple (activa) + Reversal + Momentum
  btceur_new.py             # btceur_simple (activa)
  btc_trend_pullback_v1.py  # Alternativa BTCEUR (H4+H1 multi-timeframe)
  btceur_weekly_breakout.py # Alternativa BTCEUR (breakout semanal)
  eurusd_mtf.py             # EURUSD multi-timeframe (experimental)
  xauusd_psychological.py   # Reversión niveles psicológicos (experimental)

tests/
  backtest_runner.py        # Script de backtesting CLI completo
  test_replay.py            # Tests del replay engine

logs/                       # Logs por sesión (rotación automática, en .gitignore)
backtest_results/           # CSVs de resultados de backtest
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
MT5_SERVER=...              # ej: ICMarkets-Demo

# Trading
AUTOSIGNALS=1
AUTOSIGNAL_INTERVAL=20      # segundos entre escaneos
AUTOSIGNAL_SYMBOLS=EURUSD,XAUUSD,BTCEUR

# Auto-ejecución (0 = paper trading, 1 = órdenes reales)
AUTO_EXECUTE_SIGNALS=0
AUTO_EXECUTE_CONFIDENCE=HIGH

# Riesgo
MT5_RISK_PCT=0.5

# Dashboard
DASHBOARD_PORT=5000
DASHBOARD_HISTORY_HOURS=168   # 7 días de historial
```

---

## Estrategias activas

Validadas con backtest histórico sobre datos H1 reales de MT5.

### EURUSD — `eurusd_asian_breakout` ⭐ (recomendada)

Breakout del rango asiático durante la apertura de Londres.

| Parámetro | Valor |
|---|---|
| Timeframe | H1 |
| Sesión de entrada | Londres 07:00–11:00 UTC |
| Rango asiático | 00:00–06:00 UTC |
| Entrada BUY | Cierre > asia_high + 3 pips buffer |
| Entrada SELL | Cierre < asia_low − 3 pips buffer |
| Stop Loss | Extremo opuesto del rango asiático |
| Take Profit | entry ± range × 1.5 |
| Filtros | No viernes · rango mínimo 5 pips · máximo 80 pips |
| Máx. señales | 1 por día |
| **Winrate backtest** | **56.5%** |
| **Profit factor** | **1.30** (3000 velas H1) |

### XAUUSD — `xauusd_simple`

Momentum en tendencia con filtro EMA200. Sesión activa 06:00–22:00 UTC.

| Parámetro | Valor |
|---|---|
| Timeframe | H1 |
| Filtro tendencia | EMA20 > EMA50 + precio > EMA200 |
| Entrada | RSI > 55 (BUY) / RSI < 45 (SELL) + ATR > media |
| Confirmación | No 2 velas consecutivas en contra |
| Stop Loss | 2.0× ATR |
| Take Profit | 5.0× ATR |
| R:R | 2.5 |
| Riesgo/trade | 0.60% |
| Cooldown | 240 minutos entre señales |
| **Profit factor** | **1.28** (5000 velas H1) |

### BTCEUR — `btceur_simple` (baseline)

Tendencia EMA + MACD + expansión de volatilidad. Opera 24/7.

| Parámetro | Valor |
|---|---|
| Timeframe | H1 |
| Filtro tendencia | EMA20 > EMA50 + precio > EMA200 |
| Entrada | MACD histogram en dirección + ATR > media |
| Stop Loss | 2.0× ATR |
| Take Profit | 3.0× ATR |
| R:R | 1.5 |
| Riesgo/trade | 0.50% |
| Cooldown | 60 minutos entre señales |
| **Profit factor** | **1.30** (5000 velas H1) |

### Estrategias alternativas disponibles

| Estrategia | Par | Estado | Notas |
|---|---|---|---|
| `eurusd_simple` | EURUSD | Fallback (PF 1.28) | EMA50/200 + RSI |
| `btc_trend_pullback_v1` | BTCEUR | Alternativa (PF 1.20) | H4+H1 multi-timeframe |
| `btceur_weekly_breakout` | BTCEUR | Experimental (PF 3.70) | Racha máx. 29 wins |
| `xauusd_psychological` | XAUUSD | Experimental (WR 70%) | Niveles psicológicos |
| `xauusd_reversal` | XAUUSD | Experimental | Ultra-selectiva, RSI extremo + EMA200 |
| `xauusd_momentum` | XAUUSD | Experimental | Tendencias fuertes |
| `eurusd_mtf` | EURUSD | Experimental | Multi-timeframe H1+H4 |

Para cambiar estrategia: editar `rules_config.json` → campo `"strategy"`.

---

## Dashboard

Accesible en `http://localhost:5000` mientras el bot está corriendo. Se actualiza automáticamente cada 30 segundos.

### Secciones

**Barra superior**
- Estado del sistema y uptime
- Fecha/hora actual
- Indicador de conexión MT5 (🟢/🟡/🔴 según tiempo sin datos)

**KPIs (fila superior)**
- Estado del sistema (RUNNING/ERROR)
- Señales de la sesión actual
- Posiciones abiertas en MT5
- Profit total (paper o real)

**Equity simulada y winrate**
- Calcula cómo habría evolucionado el balance si se hubieran ejecutado todas las señales de la sesión
- Winrate en tiempo real con conteo de WIN/LOSS/OPEN
- Cambio en € y % respecto al balance inicial

**Curva de equity (Chart.js)**
- Gráfico de línea interactivo con la evolución del balance simulado
- Tooltip con valor exacto en cada punto

**Posiciones reales MT5** *(solo si hay posiciones abiertas)*
- Tabla con símbolo, dirección, volumen, precio apertura, precio actual, P&L en €, SL y TP

**Circuit Breaker**
- Estado actual (ACTIVO/PAUSADO)
- Pérdidas y wins consecutivos
- Multiplicador de riesgo actual

**Pares monitoreados**
- Estado de cada par (🟢/🟡/🔴)
- Total de señales, mostradas y score promedio
- Tiempo desde última señal

**Tabla de señales (sesión actual)**
- Solo señales desde que arrancó el bot (no persiste entre reinicios en la tabla)
- Entry, SL, TP con colores (rojo/verde)
- R:R calculado automáticamente
- Estado en tiempo real: `WIN ✅` / `LOSS ❌` / `OPEN +45%` (P&L como % del riesgo)
- Estado persistente — una vez WIN/LOSS no cambia aunque MT5 se desconecte
- Filtros por par: ALL / EURUSD / XAUUSD / BTCEUR

**Botón modo real** *(esquina inferior derecha)*
- 🟢 Activar modo real — abre modal de confirmación con aviso de dinero real
- 🔴 Desactivar — vuelve a paper trading instantáneamente
- Sin reinicio necesario

**Banner de modo real** *(visible cuando está activo)*
- Aviso prominente en rojo cuando el bot ejecuta órdenes reales

**Exportar CSV**
- Botón en la tabla y endpoint `/api/export`
- Descarga todas las señales de los últimos 7 días con entry/SL/TP/R:R/estado

### APIs disponibles

| Endpoint | Descripción |
|---|---|
| `GET /` | Dashboard HTML completo |
| `GET /api/metrics` | Métricas en JSON |
| `GET /api/history` | Historial de señales (7 días) |
| `GET /api/export` | Descarga CSV |
| `GET /api/enable-real` | Activa modo real |
| `GET /api/disable-real` | Desactiva modo real |
| `GET /api/execution-status` | Estado actual del modo de ejecución |

---

## Backtesting

```bash
# Modo interactivo (recomendado)
python tests/backtest_runner.py

# CLI directo
python tests/backtest_runner.py --symbol EURUSD --strategy eurusd_asian_breakout --bars 3000
python tests/backtest_runner.py --symbol XAUUSD --bars 5000
python tests/backtest_runner.py --symbol BTCEUR --strategy btceur_simple --bars 3000
python tests/backtest_runner.py --all --bars 3000 --save

# Opciones
#   --symbol    EURUSD | XAUUSD | BTCEUR
#   --strategy  ver lista abajo
#   --bars      número de velas H1 (168 ≈ 1 semana, 720 ≈ 1 mes)
#   --verbose   muestra detalle de cada señal
#   --save      guarda resultados en backtest_results/ como CSV
#   --all       ejecuta los 3 pares con su estrategia por defecto
```

**Estrategias disponibles por par:**

| Par | Estrategias |
|---|---|
| EURUSD | `eurusd_simple`, `eurusd_advanced`, `eurusd_mtf`, `eurusd_asian_breakout` |
| XAUUSD | `xauusd_simple`, `xauusd_reversal`, `xauusd_momentum`, `xauusd_psychological` |
| BTCEUR | `btceur_simple`, `btc_trend_pullback_v1`, `btceur_weekly_breakout` |

Los resultados se guardan en `backtest_results/` como CSV con timestamp.

---

## Circuit Breaker y Risk Scaling

Implementado en `core/circuit_breaker.py`. Se activa automáticamente según el historial de trades:

| Situación | Acción |
|---|---|
| 2 pérdidas seguidas | Riesgo × 0.8 |
| 3 pérdidas seguidas | Riesgo × 0.5 |
| 4 pérdidas seguidas | **Pausa automática 24h** |
| 3 wins seguidos | Riesgo × 1.4 |
| 5 wins seguidos | Riesgo × 1.8 |
| 7 wins seguidos | Riesgo × 2.0 |

---

## Filtro de noticias (`services/news_filter.py`)

Pausa el trading 30 minutos antes y después de eventos de alto impacto:

| Evento | Símbolo afectado | Hora UTC |
|---|---|---|
| NFP (primer viernes del mes) | EURUSD, XAUUSD | 13:30 |
| CPI USA (2º martes del mes) | EURUSD, XAUUSD | 13:30 |
| Fed FOMC (meses impares + jun/dic) | EURUSD, XAUUSD | 19:00 |
| ECB Meeting (ene/abr/jun/sep) | EURUSD | 12:15 |
| ECB Press Conference | EURUSD | 12:45 |

BTCEUR no está afectado por noticias macro.

---

## Modo real vs Paper trading

El bot arranca siempre en **paper trading** (`AUTO_EXECUTE_SIGNALS=0`).

Para activar el modo real:
1. Abrir el dashboard en `http://localhost:5000`
2. Pulsar el botón verde **"Activar modo real"** (esquina inferior derecha)
3. Confirmar el modal de advertencia
4. Las señales MEDIUM-HIGH y HIGH se ejecutarán automáticamente en MT5

Para desactivar: pulsar el botón rojo en el dashboard o reiniciar el bot.

> ⚠️ El modo real implica pérdidas o ganancias reales de dinero. Úsalo solo cuando hayas validado el rendimiento en paper trading.

---

## Comandos Discord

### Control del bot

| Comando | Descripción |
|---|---|
| `/autosignals on\|off\|status` | Activa, desactiva o consulta el loop de escaneo automático |
| `/status` | Estado del bot: uptime, MT5, módulos cargados, configuración activa |
| `/pairs` | Muestra los 3 pares con su estado y permite activar/desactivar cada uno con botones |
| `/logs_info` | Ruta y tamaño del archivo de log actual |

### MT5 y posiciones

| Comando | Descripción |
|---|---|
| `/positions` | Lista posiciones abiertas en MT5 con ticket, símbolo y P&L |
| `/close_position [ticket]` | Cierra una posición por número de ticket |
| `/close_positions_ui` | Igual que el anterior pero con desplegable visual |
| `/set_mt5_credentials` | Modal para introducir login/password/server de MT5 sin tocar el .env |

### Señales y análisis

| Comando | Descripción |
|---|---|
| `/signal [symbol]` | Pide una señal manual para un par en ese momento |
| `/chart [symbol] [timeframe] [candles]` | Genera un gráfico PNG con las últimas velas |
| `/force_autosignal [symbol]` | Fuerza un escaneo inmediato sin esperar el intervalo |
| `/debug_signals [symbol]` | Pipeline completo de evaluación con todos los filtros y razones de rechazo |
| `/diagnose_signals [symbol] [iterations]` | Analiza N ventanas históricas para ver si la estrategia detecta setups |

### Backtest desde Discord

| Comando | Descripción |
|---|---|
| `/replay` | Abre un modal con 5 campos configurables y ejecuta el backtest completo con el pipeline real |

El modal de `/replay` permite configurar:
- **Par**: EURUSD / XAUUSD / BTCEUR
- **Estrategia**: cualquiera de las disponibles para ese par (vacío = estrategia activa)
- **Velas**: 100–10000 velas H1
- **Circuit Breaker**: pérdidas consecutivas para activar la pausa (0 = desactivado)
- **Pausa CB**: velas de pausa tras activar el circuit breaker

El resultado se muestra como embed con winrate, profit factor, pips netos, R:R medio, racha máxima y estadísticas del circuit breaker simulado.

### Estadísticas y configuración

| Comando | Descripción |
|---|---|
| `/performance [days]` | Reporte de rendimiento: señales, winrate, P&L de los últimos N días |
| `/strategy_performance [days]` | Desglose de rendimiento por estrategia |
| `/set_strategy [symbol] [strategy]` | Cambia la estrategia activa de un par en caliente sin reiniciar el bot |

---

## Watchdog y reconexión MT5

El bot incluye dos niveles de watchdog:

1. **MT5 watchdog** (`_mt5_watchdog_loop`): verifica la conexión cada 60s y reconecta automáticamente. Tras 5 fallos consecutivos envía alerta a Discord.
2. **Autosignal watchdog**: si no hay escaneo en 30 minutos, envía alerta al canal de señales.

---

## Resumen semanal automático

Cada lunes entre 08:00–09:00 UTC el bot envía un embed a Discord con:
- Total de señales de los últimos 7 días
- Wins / Losses / Winrate
- Mejor y peor par por winrate

---

## Notas operativas

- El bot no genera señales de forex/oro el fin de semana (mercados cerrados)
- BTCEUR opera 24/7 y puede generar señales cualquier día
- EURUSD Asian Breakout solo opera lunes–jueves, sesión de Londres (07:00–11:00 UTC)
- XAUUSD solo opera 06:00–22:00 UTC (filtro de sesión activa)
- Cooldowns: EURUSD 60 min · XAUUSD 240 min · BTCEUR 60 min
- Límite de 5 trades por período de 12h (global)
- Los logs se guardan en `logs/` con rotación automática por sesión (en `.gitignore`)
- El dashboard persiste el historial de señales 7 días entre reinicios (`dashboard_data.json`)
- Las señales LOW y VERY_LOW se filtran automáticamente (no se envían a Discord)
- Señales MEDIUM se muestran en Discord pero no se auto-ejecutan en modo real
- Señales MEDIUM-HIGH y HIGH se auto-ejecutan cuando el modo real está activo
