# Análisis completo — BOT-MT5

> Revisión de código realizada el 25/06/2026. Basada en lectura directa de los archivos fuente.

---

## ✅ Implementado correctamente

### 1. Pipeline de backtesting completo y reproducible
[`core/replay_engine.py`](file:///c:/BOT-MT5/core/replay_engine.py) ejecuta el mismo pipeline que producción sobre datos históricos. Cada sesión guarda un JSON con parámetros exactos, timestamp y resultados, lo que garantiza reproducibilidad total.

### 2. Circuit breaker con persistencia en disco
[`core/circuit_breaker.py`](file:///c:/BOT-MT5/core/circuit_breaker.py) implementa pausa automática (4 pérdidas consecutivas → 24h), risk scaling dinámico (×0.3 a ×2.0), y persiste el estado en `circuit_breaker_state.json`. Al reiniciar el bot, respeta pausas vigentes pero descarta estados de más de 48h. Limpieza de sesión anterior en `on_ready()` correctamente implementada.

### 3. Sistema de scoring flexible por símbolo
[`core/scoring.py`](file:///c:/BOT-MT5/core/scoring.py) y [`core/engine.py`](file:///c:/BOT-MT5/core/engine.py) tienen umbrales configurables por par (EURUSD/XAUUSD/BTCEUR), cargados desde [`rules_config.json`](file:///c:/BOT-MT5/rules_config.json). El score combina peso del setup + confirmaciones ponderadas. Estadísticas volcadas cada 15 minutos.

### 4. Walk-forward testing con clasificación de overfitting
[`core/walkforward.py`](file:///c:/BOT-MT5/core/walkforward.py) divide datos en ventanas TRAIN/TEST solapadas, calcula degradación de PF y WR, y clasifica la estrategia como STABLE / MARGINAL / UNSTABLE / OVERFITTED. La lógica de agregación es sólida.

### 5. Modelo de costos reales en backtesting
[`core/trade_costs.py`](file:///c:/BOT-MT5/core/trade_costs.py) incluye spread + comisión por símbolo (EURUSD 1.5 pips roundtrip, XAUUSD 3.8, BTCEUR 25.3). Todos los resultados de backtest los incluyen.

### 6. Filtro de noticias de alto impacto
Fechas exactas hardcodeadas para 2025–2026 (NFP, CPI, FOMC, ECB). Ventana de blackout de ±30 minutos. Integrado en el flujo de autosignals.

### 7. Gestión de riesgo con límites por símbolo
[`core/risk.py`](file:///c:/BOT-MT5/core/risk.py) calcula lote basado en balance real, SL en puntos, y contract size del símbolo. Límites distintos por par (EURUSD ≤ 0.5 lot, XAUUSD ≤ 0.3, BTCEUR ≤ 0.2). R:R mínimo configurable.

### 8. Watchdog MT5 no bloqueante
[`bot.py L660-739`](file:///c:/BOT-MT5/bot.py#L660-739) verifica conexión cada 60s en `asyncio.to_thread`, reconecta usando credenciales del estado, y alerta en Discord tras 5 fallos consecutivos. No bloquea el event loop.

### 9. Cooldown por símbolo en backtesting
[`core/engine.py`](file:///c:/BOT-MT5/core/engine.py) implementa cooldown en barras (10 EURUSD, 8 XAUUSD, 6 BTCEUR) cargado desde `rules_config.json`. Resetea correctamente entre ventanas de walk-forward mediante `reset_replay_state()`.

### 10. Protección de estrategia BTCEUR (fail-safe)
[`signals.py L210-223`](file:///c:/BOT-MT5/signals.py#L210-223) rechaza explícitamente cualquier clase que no esté en la lista blanca de clases BTCEUR válidas, con logging de CRITICAL y actualización de `symbol_health`. Nunca hace fallback silencioso a EURUSD.

### 11. Trailing stops automáticos
[`trailing_stops.py`](file:///c:/BOT-MT5/trailing_stops.py) implementa breakeven a 50% del TP, trailing activo desde 75%, y cierre parcial del 50% al alcanzar el TP. Actualizado cada 30s por loop asíncrono.

### 12. Resumen semanal automático (Discord)
[`bot.py L745-830`](file:///c:/BOT-MT5/bot.py#L745-830) envía embed cada lunes 08:00–09:00 UTC con stats de la semana (señales, WR, mejor/peor par). Lógica de deduplicación por fecha para no enviar dos veces el mismo lunes.

### 13. Credenciales MT5 cifradas
[`secrets_store.py`](file:///c:/BOT-MT5/secrets_store.py) + [`mt5_credentials.enc`](file:///c:/BOT-MT5/mt5_credentials.enc) almacenan las credenciales con Fernet. El comando `/set_mt5_credentials` permite actualizarlas sin tocar el `.env`.

### 14. Clasificación progresiva de estrategias (10k/15k/20k)
Pipeline de retest documentado y ejecutado: ROBUST / STABLE / INCONCLUSIVE / DEGRADING / FAILED. Resultados guardados en `backtest_results/`.

---

## 🔄 En progreso o con errores detectados en el código

### 1. ⚠️ Clave duplicada en `STRATEGY_REGISTRY` — Bug silencioso
**[`signals.py L45 y L48`](file:///c:/BOT-MT5/signals.py#L45-48)**: `'eurusd_asian_breakout'` aparece dos veces en el mismo dict. En Python, la segunda entrada sobrescribe silenciosamente a la primera. Aunque en este caso ambas apuntan a la misma función, es un error que puede ocultar problemas futuros y genera confusión.

```python
# Línea 45:
'eurusd_asian_breakout': lambda: _get_eurusd_asian_breakout(),
# ...
# Línea 48 (¡duplicada!):
'eurusd_asian_breakout': lambda: _get_eurusd_asian_breakout(),
```

### 2. ⚠️ `_market_opening_loop_simple()` es un stub vacío
**[`bot.py L644-657`](file:///c:/BOT-MT5/bot.py#L644-657)**: El loop está iniciado como tarea, pero el cuerpo real es un `pass`:
```python
if MARKET_OPENING_AVAILABLE and market_opening_system:
    pass  # ← no hace nada
```
`MarketOpeningSystem` tiene toda la lógica implementada en [`market_opening_system.py`](file:///c:/BOT-MT5/market_opening_system.py), pero **nunca se llama** desde el bot. Las alertas de apertura de mercado están completamente inactivas.

### 3. ⚠️ Factor `temporal_consistency` hardcodeado a 0.7 (placeholder)
**[`core/engine.py L719`](file:///c:/BOT-MT5/core/engine.py#L719)**:
```python
factors['temporal_consistency'] = 0.7  # Placeholder - podría analizar velas anteriores
```
Este factor siempre es constante, por lo que el confidence score está artificialmente inflado y no refleja información real del mercado.

### 4. ⚠️ Walk-forward bug conocido: ventanas 2–6 generan 0 señales
Reportado en el README como bug abierto. Las ventanas posteriores a la primera de walk-forward producen 0 señales, lo que hace que el análisis sea inútil más allá de la ventana 1. Los CSV de walkforward en `backtest_results/` muestran solo 1 ventana útil en algunos casos.

### 5. ⚠️ `btceur_regime_momentum` — 0 señales, causa sin resolver
La estrategia [`strategies/btceur_regime_momentum.py`](file:///c:/BOT-MT5/strategies/btceur_regime_momentum.py) requiere datos H4+Daily, pero el `replay_engine` descarga H1 por defecto. La causa raíz del problema de datos nunca se ha corregido. La estrategia está registrada pero es inoperable en backtest.

### 6. ⚠️ `session_summary` módulo inexistente
**[`bot.py L119`](file:///c:/BOT-MT5/bot.py#L119)**:
```python
from session_summary import session_summary
SESSION_SUMMARY_AVAILABLE = True
```
El archivo `session_summary.py` **no existe** en el proyecto. El `try/except` captura el `ImportError`, por lo que no rompe el bot, pero `SESSION_SUMMARY_AVAILABLE` siempre será `False` y la funcionalidad nunca operará.

### 7. ⚠️ Validación de paper trading incompleta (< 50 trades)
El objetivo es ≥ 50 trades cerrados por estrategia activa antes de ir a live. EURUSD y XAUUSD llevan solo una fracción de ese número según el README. Los criterios de go-live no están verificables automáticamente.

### 8. ⚠️ `get_stats()` en `filters.py` devuelve datos incorrectos
**[`core/filters.py L464`](file:///c:/BOT-MT5/core/filters.py#L464)**:
```python
'shown_signals': sum(self.daily_trades.values()),  # Simplificado por ahora
'rejected_signals': 0,  # Se calculará cuando tengamos más datos
```
El método de compatibilidad siempre reporta 0 señales rechazadas, lo que da estadísticas falsas en cualquier comando que lo llame.

### 9. ⚠️ `_filter_trading_limits` en `ConsolidatedFilters` no está conectado al estado global
Los contadores `daily_trades` y `period_trades` de [`core/filters.py`](file:///c:/BOT-MT5/core/filters.py) son independientes del `state.trades_today` y `state.trades_current_period` de `bot.py`. Hay **dos sistemas paralelos** de conteo de trades que pueden desincronizarse.

---

## 📋 Lista de 10 cosas que se deberían hacer

### 1. 🔴 Corregir el bug del walk-forward (ventanas 2–6 con 0 señales)
Es el bloqueador más importante. Sin walk-forward funcional, no se puede validar correctamente si una estrategia sobreajusta. El problema probablemente está en cómo `reset_replay_state()` o el estado del motor de detección persiste entre ventanas. Investigar el estado de `_strategy_instances` y los indicadores calculados.

### 2. 🔴 Eliminar la entrada duplicada en `STRATEGY_REGISTRY`
**[`signals.py L48`](file:///c:/BOT-MT5/signals.py#L48)**: Borrar la segunda entrada `'eurusd_asian_breakout'`. También considerar si esta estrategia (descartada) debería eliminarse de `STATEFUL_STRATEGIES` para no cachearla sin necesidad.

### 3. 🟠 Conectar realmente `market_opening_system` al loop del bot
El sistema de alertas de apertura tiene toda la lógica implementada pero nunca se ejecuta. Completar `_market_opening_loop_simple()` llamando a `market_opening_system.get_next_market_opening()` y `market_opening_system.should_send_alert()`, y enviar el mensaje formateado al canal de Discord.

### 4. 🟠 Implementar `session_summary.py` o eliminar la referencia
El módulo importado no existe. Opciones: (a) crear un `session_summary.py` que genere resúmenes por sesión de trading (London, NY), o (b) borrar el `try/except` y la variable `SESSION_SUMMARY_AVAILABLE` para limpiar el código muerto.

### 5. 🟠 Reemplazar el placeholder `temporal_consistency = 0.7`
**[`core/engine.py L719`](file:///c:/BOT-MT5/core/engine.py#L719)**: Implementar una métrica real, por ejemplo: consistencia de la dirección en las últimas N velas, o correlación entre la señal actual y las anteriores exitosas. Un valor constante no aporta información al sistema de confianza.

### 6. 🟡 Unificar los contadores de trades (doble estado)
Elegir una única fuente de verdad: `state.trades_today` en `bot.py` o `ConsolidatedFilters.daily_trades`. Lo más limpio sería hacer que `ConsolidatedFilters` lea de `BotState` en lugar de mantener sus propios contadores. Esto eliminaría el riesgo de que el límite de trades falle por desincronización.

### 7. 🟡 Implementar `core/montecarlo.py`
Mencionado como "planned" en el README y ya aparece en la hoja de ruta. Una simulación de Monte Carlo sobre las señales del backtest daría información sobre la distribución de resultados, el riesgo de ruina, y la robustez estadística de las estrategias antes de ir a live. La base de datos de trades ya existe.

### 8. 🟡 Corregir el data bug de `btceur_regime_momentum` o descartar formalmente
O bien el `ReplayEngine` aprende a descargar H4 cuando una estrategia lo requiere, o la estrategia se mueve definitivamente a `experimental/` con nota clara. Actualmente ocupa espacio en el registry y en la documentación sin funcionar.

### 9. 🟡 Implementar verificación automática de criterios de go-live
Los 6 criterios para pasar a live están documentados pero se verifican manualmente. Crear un comando Discord `/go_live_check [symbol]` que evalúe automáticamente: (1) clasificación progresiva ≥ STABLE, (2) PF paper trading, (3) drawdown, (4) winrate vs backtest, (5) walk-forward windows, (6) PF sin CB. Esto eliminaría el riesgo de error humano al tomar la decisión.

### 10. 🟢 Trade journal con SQLite (`core/journal.py`)
La BD `bot_state.db` ya existe pero no registra el historial completo de operaciones con metadatos (estrategia usada, score de confianza en el momento, condiciones de mercado, duración del trade). Un journal permitiría analizar qué tipo de setups generan resultados reales en paper/live vs backtest, cerrar el loop de validación, y alimentar el resumen semanal con datos reales de P&L en lugar de estimaciones.

---

## Resumen visual

| Área | Estado |
|---|---|
| Circuit Breaker | ✅ Completo y robusto |
| Backtesting / Replay | ✅ Funcional con costos reales |
| Scoring / Confianza | ⚠️ Placeholder en `temporal_consistency` |
| Walk-Forward | ❌ Bug en ventanas 2–6 |
| Trailing Stops | ✅ Implementado (loop activo) |
| Market Opening Alerts | ❌ Loop vacío, nunca se ejecuta |
| Filtro de Noticias | ✅ Completo (fechas 2025–2026) |
| Risk Manager | ✅ Funcional con límites por símbolo |
| Session Summary | ❌ Módulo inexistente |
| Discord Bot (17 cmds) | ✅ Operativo |
| Paper Trading | 🔄 En curso (< 50 trades/estrategia) |
| Monte Carlo | 📋 Planificado, no iniciado |
| Trade Journal SQLite | 📋 Planificado, no iniciado |
| Go-Live Verification | 📋 Manual, sin automatización |
