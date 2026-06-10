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

---

### 2026-06-04 — [REVISIÓN] eurusd_simple: walk-forward UNSTABLE — no descartada, pero no avanza a paper trading

**Contexto**: Primer walk-forward de eurusd_simple. 20 ventanas en 20000 velas H1 (train 4320 / test 720 / step 720). CB: 3 pérdidas / 72 velas pausa.

**Observación**: Veredicto UNSTABLE. Pero el dato interesante es que el PF promedio en test (1.09) supera al de train (1.06) — esto descarta overfitting clásico. El problema real es la varianza: las ventanas van de PF test 0.50 (ventana 9) a 2.55 (ventana 18). Las ventanas 8 y 9 son las críticas — ambas con PF test < 0.65. El consistency score fue 0.84.

**Decisión**: eurusd_simple NO avanza a PAPER_TRADING todavía. Estado actualizado a VALIDATING. El resultado no justifica ni el descarte ni el avance — justifica investigación. Preguntas abiertas: ¿qué régimen de mercado cubre la ventana 8-9 (barras 10080–11520)? ¿Es un periodo de consolidación fuerte? ¿La estrategia tiene un régimen de mercado claro donde falla?

**Impacto**: Run Card `RC_walk_forward_20260604_eurusd_simple.json` generada y enlazada a la hipótesis. El test `walk_forward` marcado como completado en el registry. Hipótesis en VALIDATING hasta resolver las ventanas problemáticas.

**Pendiente**: Analizar las barras 10080–11520 (ventanas 8-9) en el contexto de precio real de EURUSD. Si corresponden a un período de mercado lateral de baja volatilidad, podría añadirse un filtro de régimen. Después: repetir walk-forward con filtro → si mejora → volver a RETESTING con nueva configuración.

---

### 2026-06-04 — [DESCUBRIMIENTO] Las ventanas 8-9 NO son un problema de régimen — son un problema de WR puntual en periodo específico

**Contexto**: Investigación profunda de las ventanas 8 y 9 del walk-forward (PF 0.61 y 0.50). Script `investigate_windows.py` ejecutado con datos reales de MT5. Se analizó régimen de mercado (ATR, ADX, pendiente EMA50) y operaciones trade por trade.

**Observación**: El hallazgo más importante es que **las ventanas TOP y las ventanas CRÍTICAS tienen el mismo régimen: LOW_VOLATILITY**. Los datos desmienten la hipótesis de régimen diferencial:

| Ventana | PF test | WR   | ATR%   | ADX  | Régimen        | Fechas                     |
|---------|---------|------|--------|------|----------------|----------------------------|
| 7 (TOP) | 2.290   | 60%  | 0.100% | 34.9 | LOW_VOLATILITY | Sep–Oct 2024               |
| 8 (MAL) | 0.610   | 30%  | 0.121% | 36.6 | LOW_VOLATILITY | Oct–Nov 2024               |
| 9 (MAL) | 0.500   | 24%  | 0.142% | 32.4 | LOW_VOLATILITY | Nov 2024–Ene 2025          |
| 18 (TOP)| 2.550   | 59%  | 0.093% | 33.3 | LOW_VOLATILITY | Dic 2025–Ene 2026          |

ATR, ADX y pendiente EMA50 son prácticamente idénticos entre las ventanas buenas y las malas. Lo que cambia completamente es el **Win Rate**: 60% en las buenas, 24-30% en las malas. El RR efectivo es casi idéntico en todos los casos (~3.24-3.42x).

**Conclusión de los datos**: El problema no es el régimen de mercado. El problema es que en Oct-Ene 2024/2025 la estrategia generó señales que fueron rechazadas con una frecuencia anormalmente alta. Esto puede ser:
1. Un periodo de **whipsaws**: EURUSD en esa época tuvo movimientos post-elecciones USA (Nov 2024) que invalidaron muchos setups de tendencia.
2. **Ruido estadístico real**: 18-26 trades con WR del 24-30% cae dentro del rango posible de una estrategia con expectativa real del 35-40% (el IC del 95% para n=20 con p=0.35 va de ~15% a ~55%).
3. La estrategia no tiene filtro para eventos macroeconómicos de alto impacto.

**Decisión**: Las hipótesis H2 (ADX), H3 (ATR) y H4 (pendiente EMA50) quedan descartadas por los datos. H1 (régimen) queda parcialmente descartada — el clasificador no distingue las ventanas. H5 (ruido estadístico) toma más peso como explicación. La causa más probable es una combinación de **ruido estadístico en muestra pequeña** + **evento macro específico** (elecciones USA Nov 2024 → rally USD fuerte que rompió tendencias EMA en EURUSD).

**Impacto**: Redefinir el plan de investigación. El siguiente experimento no debe ser un filtro de régimen genérico — debe ser: analizar si el drawdown de las ventanas 8-9 coincide con el periodo post-electoral de Nov 2024 donde el DXY tuvo un rally de +4% en pocas semanas.

**Pendiente**:
- Verificar manualmente en qué fecha exacta cayeron los trades perdedores de las ventanas 8-9 (está en el CSV del walk-forward).
- Si la concentración de pérdidas es en Nov 2024: la estrategia es viable pero sensible a eventos macro. Eso es diferente a un defecto estructural.
- Considerar si el paper trading actual (que corre en condiciones de mercado de 2026) es una mejor prueba que este walk-forward histórico.

---

---

### 2026-06-10 — [PROMOCIÓN] xauusd_simple avanza a PAPER_TRADING tras walk-forward MARGINAL

**Contexto**: Walk-forward de xauusd_simple. 20 ventanas en 20000 velas H1 (train 4320 / test 720 / step 720). CB: 4 pérdidas / 168 velas pausa.

**Observación**: Veredicto MARGINAL. Los datos clave:
- Avg test PF 1.30 > avg train PF 1.19 → no hay overfitting
- Consistency score 0.83 → 15 de 20 ventanas con PF test > 1.0
- 3 ventanas con colapso: ventana 2 (0 trades), ventana 17 (PF 0.25), ventana 19 (PF 0.84)
- Ventana 15 con PF 4.17: outlier positivo, probablemente pocos trades

El patrón es similar al de eurusd_simple: el test supera al train en promedio, lo que descarta overfitting. La estrategia tiene edge real en la mayoría de periodos con degradación puntual en algunos.

**Decisión**: xauusd_simple promovida a PAPER_TRADING. Es la primera estrategia que supera el walk-forward suficientemente para avanzar. El veredicto MARGINAL (no STABLE) implica que el paper trading tiene que confirmar el comportamiento — no es una validación completa, es evidencia suficiente para el siguiente paso.

**Impacto**: Pipeline activo ahora tiene dos estrategias en PAPER_TRADING: xauusd_simple y, cuando tengamos más datos, eurusd_simple (aún en VALIDATING pendiente de análisis de ventanas).

**Pendiente**: Acumular ≥ 50 trades cerrados en paper trading. Registrar entrada [PAPER_TRADING] cuando haya suficiente evidencia.

---

### 2026-06-10 — [DESCARTE] xauusd_momentum descartada — el retest 20k era un artefacto de muestra pequeña

**Contexto**: Walk-forward de xauusd_momentum. Misma configuración que xauusd_simple.

**Observación**: El resultado destruye la hipótesis completamente. Lo más importante no es el veredicto UNSTABLE — es que el **avg train PF es 0.76**. La estrategia no tiene edge ni en el periodo de entrenamiento de la mayoría de ventanas. Además:

- La mayoría de ventanas test tienen 0 trades o 1-3 trades → ruido estadístico puro
- Las ventanas con PF inf (8, 10) y PF 5.52/6.12 (16, 18) son outliers de 1 sola operación ganadora sin pérdidas — no edge real
- Consistency score 0.44: peor que lanzar una moneda
- Los buenos resultados del retest multi-horizonte (PF 1.42 en 10k velas, 63 trades totales) eran exactamente eso: una muestra de 63 trades que por azar dieron buenas métricas

**Decisión**: xauusd_momentum descartada definitivamente. Estado FAILED. A diferencia de eurusd_asian_breakout (donde la dirección era correcta pero el TP incorrecto), aquí la estrategia no tiene edge demostrable en ningún período suficientemente amplio.

**Impacto**: Pipeline queda con 3 estrategias: eurusd_simple (VALIDATING), xauusd_simple (PAPER_TRADING), btc_trend_pullback_v1 (TESTING, pendiente de inicio). xauusd_momentum eliminada del pipeline.

**Pendiente**: Actualizar rules_config.json si xauusd_momentum estaba activa en el bot. Verificar que el bot usa xauusd_simple y no xauusd_momentum en producción.

---

<!-- PLANTILLA PARA PRÓXIMAS ENTRADAS

### YYYY-MM-DD — [TIPO] Título

**Contexto**: 
**Observación**: 
**Decisión**: 
**Impacto**: 
**Pendiente**: 

-->
