# Research Journal — BOT-MT5

Captura decisiones, descubrimientos y cambios de criterio.
**No registrar**: ejecuciones rutinarias sin decisión.
**Sí registrar**: cambios de criterio, descartes, promociones, descubrimientos, aprendizajes.

---

## Formato de entrada

```
### YYYY-MM-DD — [TIPO] Título corto

**Contexto**: qué estaba pasando / qué se estaba evaluando
**Observación**: qué encontramos / qué salió diferente a lo esperado
**Decisión**: qué se decidió hacer y por qué
**Impacto**: qué cambia en el pipeline / en las hipótesis
**Pendiente**: qué necesita seguimiento
```

Tipos: `[DESCARTE]` `[PROMOCIÓN]` `[DESCUBRIMIENTO]` `[CRITERIO]` `[REVISIÓN]` `[PAPER_TRADING]` `[LIVE]`

---

## Entradas

---

### 2026-06-01 — [DESCARTE] eurusd_asian_breakout descartada tras retest multi-horizonte

**Contexto**: Primera sesión de retest sistemático. Se probaron 5 estrategias en 10k/15k/20k velas H1.

**Observación**: eurusd_asian_breakout nunca supera PF 1.0. El máximo alcanzado fue 0.989 en 15k velas. El WR del 54% indica que la dirección de la ruptura se detecta correctamente, pero el TP (1.5x rango asiático) es demasiado pequeño para compensar las pérdidas.

**Decisión**: Estrategia descartada en su configuración actual. El concepto no se descarta completamente — el problema probable es el sizing del TP, no la lógica de dirección. Queda en estado FAILED.

**Impacto**: Eliminada del pipeline de walk-forward y monte carlo. No entra en paper trading.

**Pendiente**: Si se retoma en el futuro, explorar TP dinámico basado en ATR de sesión en lugar de múltiplo fijo del rango asiático.

---

### 2026-06-01 — [DESCUBRIMIENTO] btceur_simple colapsa entre 10k y 15k velas

**Contexto**: btceur_simple no era candidata principal pero se incluyó en el retest.

**Observación**: PF cae de 1.226 (10k velas) a 0.924 (15k velas). Comportamiento opuesto al esperado. Las primeras 10k velas son un período favorable para BTC que no se reproduce en contexto más amplio.

**Decisión**: btceur_simple excluida del pipeline actual. No tiene hipótesis registrada y su comportamiento es inestable. btc_trend_pullback_v1 (diferente estrategia) sigue en estado TESTING pendiente de grid search propio.

**Impacto**: Pipeline activo queda con 3 candidatas: eurusd_simple, xauusd_simple, xauusd_momentum.

**Pendiente**: Validar btc_trend_pullback_v1 por separado cuando las 3 candidatas principales avancen suficientemente.

---

### 2026-06-01 — [CRITERIO] Umbrales de robustez definidos para el pipeline

**Contexto**: Después del primer retest sistemático, necesitamos criterios explícitos para decidir qué avanza.

**Observación**: La clasificación automática del sistema usa PF mínimo ≥ 1.1 y degradación < 15%. Esto funciona como primer filtro, pero necesitamos criterios adicionales para la siguiente fase.

**Decisión**: Criterios para avanzar a walk-forward:
- PF mínimo ≥ 1.1 en todos los horizontes ✓
- Degradación total < 15% ✓
- Consistencia ≥ 0.5 (el sistema ya lo verifica) ✓
- Señales mínimas: >50 en el horizonte más largo (xauusd_momentum borderline con 78)

xauusd_momentum avanza con advertencia: solo 78 señales en 20k velas — la estadística es limitada. Walk-forward lo confirmará o rechazará.

**Impacto**: Los tres criterios quedan documentados y serán la referencia para futuras sesiones.

**Pendiente**: Revisar criterio de señales mínimas tras walk-forward. Puede ser necesario ajustar.

---

### 2026-06-04 — [CRITERIO] Sistema de research formalizado (Hypothesis Registry + Run Cards + Journal)

**Contexto**: El proyecto entra en fase v1.0-research-start con paper trading activo y retests largos completados. Necesitamos estructura para acumular evidencia a lo largo de meses sin perder conocimiento.

**Decisión**: Implementar tres capas de documentación ligeras:
1. **Hypothesis Registry** (`research/hypotheses/*.json`) — una hipótesis por estrategia, evoluciona con evidencia
2. **Run Cards** (`research/run_cards/*.json`) — una tarjeta por experimento importante, reproducibilidad garantizada
3. **Research Journal** (`research/journal.md`) — solo decisiones y descubrimientos, no ejecuciones rutinarias

El script `research/tools/run_card_generator.py` automatiza la creación de Run Cards desde session_summary.json existentes. El script `research/tools/hypothesis_status.py` muestra el estado actual de todas las hipótesis en una línea cada una.

**Impacto**: A partir de ahora, todo experimento importante genera una Run Card. Toda decisión se registra aquí. Las hipótesis se actualizan cuando cambia su estado o llega nueva evidencia.

**Pendiente**: Completar paper trading de esta semana → registrar entrada de tipo [PAPER_TRADING] con resultados reales.

---

<!-- PLANTILLA PARA PRÓXIMAS ENTRADAS

### YYYY-MM-DD — [TIPO] Título

**Contexto**: 
**Observación**: 
**Decisión**: 
**Impacto**: 
**Pendiente**: 

-->
