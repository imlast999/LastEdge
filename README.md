# 🤖 BOT MT5 — Trading Automatizado con Discord

Bot de trading para MetaTrader 5 con integración Discord, backtesting histórico, paper trading y modo real. Monitorea EURUSD, XAUUSD y BTCEUR en H1 con señales automáticas, dashboard web en tiempo real, circuit breaker integrado y pipeline completo de validación cuantitativa.

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
  walkforward.py            # Walk-forward testing
  trade_costs.py            # Modelado de spread y comisiones reales

services/
  autosignals.py            # Loop de escaneo automático
  dashboard.py              # Dashboard web (puerto 5000)
  execution.py              # Ejecución de órdenes MT5
  logging.py                # Sistema de logging inteligente
  database.py               # Persistencia SQLite
  commands.py               # Comandos Discord adicionales
  news_filter.py            # Filtro de noticias de alto impacto

strategies/
  base.py                   # Clase base con indicadores comunes
  eurusd.py                 # eurusd_simple ⭐ activa EURUSD
  xauusd.py                 # xauusd_simple ⭐ activa XAUUSD + Momentum
  btceur_new.py             # btceur_simple ⭐ activa BTCEUR
  btc_trend_pullback_v1.py  # Alternativa BTCEUR (H4+H1 multi-timeframe)
  btceur_weekly_breakout.py # Alternativa BTCEUR (breakout semanal)
  btceur_regime_momentum.py # Alternativa BTCEUR (régimen + momentum H4)
  experimental/             # Estrategias descartadas tras validación
    eurusd_asian_breakout.py  # DESCARTADA — PF < 1.0 en retest 10k/15k/20k
    eurusd_mtf.py             # DESCARTADA — PF 0.46 en backtest
    xauusd_psychological.py   # DESCARTADA — PF negativo

tests/
  backtest_runner.py        # Script de backtesting CLI completo
  optimize_strategies.py    # Grid search de parámetros
  apply_optimization.py     # Aplica parámetros óptimos al código
  run_full_backtest.bat     # Ejecuta todos los backtests + walk-forward
  run_progressive_retests.py  # Retest multi-horizonte 10k/15k/20k
  run_progressive_retests.bat # Lanzador del retest progresivo
  run_long_retests.py       # Retests largos con logging persistente
  run_optimization.bat      # Lanzador del grid search
  run_backtest_logger.py    # Wrapper con logging para el .bat
  test_replay.py            # Tests del replay engine

backtest_results/
  optimization/             # JSONs de grid search (parámetros óptimos)
  progressive_retests/      # Sesiones de retest 10k/15k/20k
  walk_forward/             # Resultados de walk-forward (futuro)
  monte_carlo/              # Resultados de Monte Carlo (futuro)

logs/                       # Logs por sesión (rotación automática, en .gitignore)
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

Validadas con retest progresivo sobre 10.000 / 15.000 / 20.000 velas H1 reales de MT5 (junio 2026). Los costes de spread y comisión de cuenta Professional están incluidos en todos los resultados.

### EURUSD — `eurusd_simple` ⭐

Momentum en tendencia con ATR dinámico. Parámetros optimizados mediante grid search (mayo 2026).

| Parámetro | Valor |
|---|---|
| Timeframe | H1 |
| Stop Loss | 1.5× ATR |
| Take Profit | 6.0× ATR |
| R:R implícito | ~4:1 |
| Riesgo/trade | 0.75% |
| Circuit Breaker | 3 pérdidas → pausa 72 velas |
| Cooldown | 10 velas entre señales |

**Resultados retest progresivo (con costes reales):**

| Horizonte | Señales | WR | PF | Pips netos | Clasificación |
|---|---|---|---|---|---|
| 10.000 velas | 337 | 26.1% | 1.12 | +727 | — |
| 15.000 velas | 516 | 25.8% | 1.11 | +905 | — |
| 20.000 velas | 690 | 27.0% | **1.19** | +2068 | **✅ ROBUST** |

El PF mejora al ampliar el horizonte — señal de ausencia de overfitting. Racha máxima de pérdidas: 26 (requiere CB activo).

---

### XAUUSD — `xauusd_simple` ⭐

Momentum en tendencia con filtro EMA200. Sesión activa 06:00–22:00 UTC.

| Parámetro | Valor |
|---|---|
| Timeframe | H1 |
| Filtro tendencia | EMA20 > EMA50 + precio > EMA200 |
| Entrada | RSI > 55 (BUY) / RSI < 45 (SELL) + ATR > media |
| Stop Loss | 2.0× ATR |
| Take Profit | 5.0× ATR |
| R:R | 2.5 |
| Riesgo/trade | 0.60% |
| Circuit Breaker | 4 pérdidas → pausa 168 velas |
| Cooldown | 240 minutos entre señales |

**Resultados retest progresivo (con costes reales):**

| Horizonte | Señales | WR | PF | Pips netos | Clasificación |
|---|---|---|---|---|---|
| 10.000 velas | 253 | 38.7% | 1.23 | +13.151 | — |
| 15.000 velas | 361 | 36.8% | 1.20 | +13.154 | — |
| 20.000 velas | 456 | 35.5% | **1.17** | +12.462 | **✅ ROBUST** |

Degradación controlada del 5.1% — la más estable del sistema. Drawdown máximo estable en los tres horizontes.

---

### BTCEUR — `btceur_simple` ⭐

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
| Circuit Breaker | 4 pérdidas → pausa 168 velas |
| Cooldown | 60 minutos entre señales |
| Límite dirección | Máx. 3 señales en la misma dirección por día |

**Resultados retest progresivo (con costes reales):**

| Horizonte | Señales | WR | PF | Pips netos | Clasificación |
|---|---|---|---|---|---|
| 10.000 velas | 239 | 46.4% | 1.23 | +36.836 | — |
| 15.000 velas | 344 | 43.6% | 1.02 | +4.175 | — |
| 20.000 velas | — | — | — | — | **⚠️ INCONCLUSIVE** |

Dependencia de régimen de mercado detectada: funciona bien en tendencia, se deteriora en lateralización. Drawdown crece significativamente al ampliar el horizonte. Monitorear con precaución en paper trading.

---

### Estrategias alternativas disponibles (no activas)

| Estrategia | Par | PF backtest | Estado | Notas |
|---|---|---|---|---|
| `xauusd_momentum` | XAUUSD | 1.25 (20k) | Disponible | ROBUST, degradación 12.2%, muestra pequeña (78 trades) |
| `btc_trend_pullback_v1` | BTCEUR | 1.21 | Disponible | CB muy activo (53% señales bloqueadas) |
| `btceur_weekly_breakout` | BTCEUR | 2.66 (con CB) | Disponible | PF inflado por CB, no validado sin CB |
| `btceur_regime_momentum` | BTCEUR | — | En prueba | H4+Daily, 0 señales en backtest (bug datos H4 pendiente) |

Para cambiar estrategia: editar `rules_config.json` → campo `"strategy"`, o usar `/set_strategy` en Discord.

---

### Estrategias descartadas (`strategies/experimental/`)

| Estrategia | Par | Motivo de descarte |
|---|---|---|
| `eurusd_asian_breakout` | EURUSD | PF < 1.0 en retest 10k/15k/20k con costes reales |
| `eurusd_mtf` | EURUSD | PF 0.46 en backtest — sin edge |
| `xauusd_psychological` | XAUUSD | PF negativo — pierde más de lo que gana |
| `xauusd_reversal` | XAUUSD | 1–3 señales en 5000 velas — demasiado restrictiva |

Movidas a `strategies/experimental/` para referencia histórica. No registradas en el sistema activo.

---

## Pipeline de validación cuantitativa

El proyecto incluye un pipeline completo para validar estrategias antes de usarlas en real.

### 1. Backtest individual

```bash
# Modo interactivo
python tests/backtest_runner.py

# CLI con circuit breaker simulado
python tests/backtest_runner.py --symbol EURUSD --strategy eurusd_simple --bars 10000 --save
python tests/backtest_runner.py --symbol XAUUSD --bars 10000 --cb-losses 4 --cb-pause 168
python tests/backtest_runner.py --symbol BTCEUR --bars 10000 --cb-losses 0  # sin CB

# Todos los pares + walk-forward
tests\run_full_backtest.bat
```

Opciones: `--symbol`, `--strategy`, `--bars`, `--verbose`, `--save`, `--all`, `--walkforward`, `--cb-losses`, `--cb-pause`

### 2. Grid search de parámetros

```bash
tests\run_optimization.bat
# o directamente:
python tests/optimize_strategies.py
```

Prueba todas las combinaciones de SL/TP/CB para cada estrategia sobre 5000 velas. Guarda el top 5 de cada estrategia en `backtest_results/optimization/`. Duración: ~7 horas para todas las estrategias.

Para aplicar los parámetros óptimos:
```bash
python tests/apply_optimization.py backtest_results/optimization/optimization_YYYYMMDD.json
```

### 3. Retest progresivo multi-horizonte

```bash
tests\run_progressive_retests.bat
# o directamente:
python tests/run_progressive_retests.py
```

Ejecuta cada estrategia activa con 10.000, 15.000 y 20.000 velas H1 de forma secuencial. Detecta automáticamente degradación temporal y clasifica cada estrategia como:

| Clasificación | Criterio |
|---|---|
| **ROBUST** | PF mínimo ≥ 1.1 en todos los horizontes, degradación < 15% |
| **STABLE** | PF mínimo ≥ 1.05, degradación < 25% |
| **DEGRADING** | PF positivo pero degradación ≥ 15% |
| **OVERFITTED** | PF alto en 10k pero cae por debajo de 1.0 en 20k |
| **FAILED** | PF < 1.0 en algún horizonte |
| **INCONCLUSIVE** | Datos insuficientes o resultados contradictorios |

Resultados guardados en `backtest_results/progressive_retests/session_YYYYMMDD_HHMMSS/`.

### 4. Walk-forward testing

```bash
python tests/backtest_runner.py --symbol EURUSD --bars 10000 --walkforward
python tests/backtest_runner.py --symbol XAUUSD --bars 10000 --walkforward --wf-train 2160 --wf-test 720
```

Divide los datos en ventanas TRAIN/TEST solapadas y evalúa la consistencia de la estrategia en cada ventana. Detecta overfitting cuando el PF en TEST es significativamente inferior al de TRAIN.

### Costes reales incluidos (`core/trade_costs.py`)

Todos los backtests descuentan automáticamente los costes de la cuenta Professional de FXLiveCapital:

| Par | Spread | Comisión | Total round-trip |
|---|---|---|---|
| EURUSD | 1.2 pips | 0.3 pips | **1.5 pips** |
| XAUUSD | 3.5 pips | 0.3 pips | **3.8 pips** |
| BTCEUR | 25.0 pips | 0.3 pips | **25.3 pips** |

---

## Dashboard

Accesible en `http://localhost:5000` mientras el bot está corriendo. Se actualiza automáticamente cada 30 segundos.

### Secciones

**Barra superior** — Estado del sistema, uptime, fecha/hora, indicador de conexión MT5 (🟢/🟡/🔴)

**KPIs** — Estado del sistema, señales de la sesión, posiciones abiertas en MT5, profit total

**Equity en tiempo real**
- Balance base (MT5 al arrancar) + P&L acumulado de señales cerradas + P&L flotante de señales abiertas
- Se actualiza cada 10 segundos vía `/api/equity` sin recargar la página
- En modo real usa directamente `mt5.account_info().equity`

**Curva de equity (Chart.js)** — Gráfico interactivo con la evolución del balance. El último punto incluye el flotante actual.

**Posiciones reales MT5** — Tabla con símbolo, dirección, volumen, precio apertura, precio actual, P&L en €, SL y TP *(solo si hay posiciones abiertas)*

**Circuit Breaker** — Estado actual, pérdidas/wins consecutivos, multiplicador de riesgo activo

**Pares monitoreados** — Estado de cada par, total de señales, score promedio, tiempo desde última señal

**Tabla de señales (sesión actual)**
- Solo señales desde que arrancó el bot — se resetea a 0 en cada reinicio
- Entry, SL, TP con colores · R:R calculado · Estado: `WIN ✅` / `LOSS ❌` / `OPEN +45%`
- Estado persistente — una vez WIN/LOSS no cambia aunque MT5 se desconecte
- Filtros por par: ALL / EURUSD / XAUUSD / BTCEUR

**Botón modo real** — Modal de confirmación con aviso de dinero real. Sin reinicio necesario.

**Exportar CSV** — Botón en la tabla y endpoint `/api/export`. Descarga señales de los últimos 7 días.

### APIs disponibles

| Endpoint | Descripción |
|---|---|
| `GET /` | Dashboard HTML completo |
| `GET /api/metrics` | Métricas en JSON |
| `GET /api/history` | Historial de señales (7 días) |
| `GET /api/export` | Descarga CSV |
| `GET /api/equity` | Snapshot de equity en tiempo real |
| `GET /api/enable-real` | Activa modo real |
| `GET /api/disable-real` | Desactiva modo real |
| `GET /api/execution-status` | Estado actual del modo de ejecución |

---

## Circuit Breaker y Risk Scaling

Implementado en `core/circuit_breaker.py`. Estado persistente durante la sesión, se resetea en cada reinicio del bot.

| Situación | Acción |
|---|---|
| 2 pérdidas seguidas | Riesgo × 0.8 |
| 3 pérdidas seguidas | Riesgo × 0.5 |
| 4 pérdidas seguidas | **Pausa automática 24h** |
| 3 wins seguidos | Riesgo × 1.4 |
| 5 wins seguidos | Riesgo × 1.8 |
| 7 wins seguidos | Riesgo × 2.0 |

El CB está completamente integrado con el dashboard: cada señal que se cierra como WIN/LOSS actualiza el estado del CB en tiempo real.

---

## Filtro de noticias (`services/news_filter.py`)

Pausa el trading 30 minutos antes y después de eventos de alto impacto. Fechas exactas hardcodeadas para 2025–2026 (no aproximaciones).

| Evento | Símbolo afectado | Hora UTC |
|---|---|---|
| NFP (primer viernes del mes) | EURUSD, XAUUSD | 13:30 |
| CPI USA | EURUSD, XAUUSD | 13:30 |
| Fed FOMC | EURUSD, XAUUSD | 19:00 |
| ECB Meeting | EURUSD | 12:15 |
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

> ⚠️ El modo real implica pérdidas o ganancias reales de dinero. Úsalo solo cuando hayas validado el rendimiento en paper trading con al menos 50 operaciones cerradas por estrategia.

---

## Comandos Discord

### Control del bot

| Comando | Descripción |
|---|---|
| `/autosignals on\|off\|status` | Activa, desactiva o consulta el loop de escaneo automático |
| `/status` | Estado del bot: uptime, MT5, módulos cargados, configuración activa |
| `/pairs` | Muestra los 3 pares con su estado y permite activar/desactivar cada uno |
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
| `/replay` | Abre un modal con 5 campos configurables y ejecuta el backtest completo |

El modal de `/replay` permite configurar par, estrategia, velas (100–10000), pérdidas para activar CB y velas de pausa. El resultado se muestra como embed con WR, PF, pips netos, R:R medio, racha máxima y estadísticas del CB simulado.

### Estadísticas y configuración

| Comando | Descripción |
|---|---|
| `/performance [days]` | Reporte de rendimiento: señales, winrate, P&L de los últimos N días |
| `/strategy_performance [days]` | Desglose de rendimiento por estrategia |
| `/set_strategy [symbol] [strategy]` | Cambia la estrategia activa de un par en caliente sin reiniciar el bot |
| `/bot_status` | Estado del circuit breaker (activo/pausado, racha, multiplicador) y cooldowns por par |
| `/news` | Próximos eventos de alto impacto con ventana de blackout y símbolos afectados |
| `/equity` | Snapshot de equity paper: balance cerrado + P&L flotante de señales abiertas |

---

## Watchdog y reconexión MT5

El bot incluye dos niveles de watchdog:

1. **MT5 watchdog** (`_mt5_watchdog_loop`): verifica la conexión cada 60s y reconecta automáticamente. Tras 5 fallos consecutivos envía alerta a Discord. No bloquea el event loop de asyncio.
2. **Autosignal watchdog**: si no hay escaneo en 30 minutos (y el CB no está activo), envía alerta al canal de señales.

---

## Resumen semanal automático

Cada lunes entre 08:00–09:00 UTC el bot envía un embed a Discord con total de señales, wins/losses, winrate y mejor/peor par de los últimos 7 días.

---

## Notas operativas

- El bot arranca con un **cooldown de 2 minutos** antes de enviar la primera señal (evita falsas señales al inicio)
- Cada reinicio del bot es una sesión completamente limpia: historial de señales, balance paper, circuit breaker y cooldowns se resetean a 0
- El bot no genera señales de forex/oro el fin de semana (mercados cerrados)
- BTCEUR opera 24/7 y puede generar señales cualquier día
- EURUSD solo opera en sesiones de Londres y Nueva York
- XAUUSD solo opera 06:00–22:00 UTC (filtro de sesión activa)
- Cooldowns: EURUSD 10 velas · XAUUSD 240 min · BTCEUR 60 min
- BTCEUR tiene límite de 3 señales en la misma dirección por día (anti-spam en tendencias fuertes)
- Límite de 5 trades por período de 12h (global)
- Los logs se guardan en `logs/` con rotación automática por sesión (en `.gitignore`)
- Las señales LOW y VERY_LOW se filtran automáticamente
- Señales MEDIUM se muestran en Discord pero no se auto-ejecutan en modo real
- Señales MEDIUM-HIGH y HIGH se auto-ejecutan cuando el modo real está activo

---

## Criterios para pasar a trading real

Basados en el análisis cuantitativo del proyecto (junio 2026):

1. **Paper trading** ≥ 3 meses o ≥ 50 operaciones cerradas por estrategia
2. **PF acumulado** ≥ 1.10 en paper trading
3. **Drawdown máximo** en paper < 10% del capital asignado
4. **WR real** dentro de ±10% del WR del backtest
5. **Walk-forward** con ≥ 4 de 7 ventanas positivas en TEST
6. La estrategia funciona con PF > 1.0 **sin** circuit breaker (o el CB es mejora, no requisito)

> El objetivo no es encontrar la estrategia con el PF más alto en backtest. Es encontrar la estrategia que menos se rompe cuando el mercado cambia.
