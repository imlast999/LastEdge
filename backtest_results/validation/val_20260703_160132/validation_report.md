# Validation Report — EURUSD Exit Research

**Run ID:** `val_20260703_160132`  
**Generado:** 2026-07-03 16:24 UTC  
**Dataset máximo:** 20,000 velas H1  
**Finalistas analizadas:** `partial_close`, `rr_1_3`  
**Referencia:** `current_production` (SL=1.5xATR, TP=6.0xATR, RR=1:4)  

---

## Fase 3 — Backtest por Nivel

### `current_production` ◄ REFERENCIA

| Nivel | PF | WR% | Net Pips | MaxDD | Expectancy | MAE gan. | MFE gan. | Cap% | Sharpe |
|---|---|---|---|---|---|---|---|---|---|
| 10k | 1.10 | 23.9% | 4,510 | 8,123 | 1.41 | 6.8 | 73.6 | 87.6% | 0.038 |
| 15k | 1.02 | 22.7% | 1,546 | 8,123 | 0.32 | 7.9 | 83.5 | 86.5% | 0.008 |
| 20k | 1.02 | 22.9% | 1,803 | 8,123 | 0.28 | 7.7 | 80.9 | 87.3% | 0.007 |

### `partial_close`

| Nivel | PF | WR% | Net Pips | MaxDD | Expectancy | MAE gan. | MFE gan. | Cap% | Sharpe |
|---|---|---|---|---|---|---|---|---|---|
| 10k | 1.96 | 54.7% | 34,817 | 1,447 | 7.81 | 6.8 | 41.9 | 69.9% | 0.290 |
| 15k | 1.88 | 53.6% | 55,811 | 2,125 | 8.33 | 7.7 | 47.9 | 69.6% | 0.265 |
| 20k | 1.85 | 54.1% | 71,046 | 2,125 | 7.88 | 7.6 | 46.0 | 69.3% | 0.260 |

### `rr_1_3`

| Nivel | PF | WR% | Net Pips | MaxDD | Expectancy | MAE gan. | MFE gan. | Cap% | Sharpe |
|---|---|---|---|---|---|---|---|---|---|
| 10k | 1.13 | 30.3% | 5,554 | 5,761 | 1.73 | 7.0 | 58.0 | 83.0% | 0.054 |
| 15k | 1.05 | 28.8% | 3,635 | 5,761 | 0.75 | 8.0 | 66.0 | 82.4% | 0.020 |
| 20k | 1.06 | 29.2% | 5,900 | 5,761 | 0.90 | 7.8 | 63.9 | 83.4% | 0.025 |

---

## Fase 4 — Estabilidad entre Históricos

| Variante | Estado | PF 10k → 15k → 20k | Caída PF | WR Δ | DD crecimiento |
|---|---|---|---|---|---|
| `current_production` | ✅ STABLE | 1.10 → 1.02 → 1.02 | -7.5% | 1.0 pts | +0 pips |
| `partial_close` | ✅ STABLE | 1.96 → 1.88 → 1.85 | -5.8% | 0.7 pts | +678 pips |
| `rr_1_3` | ✅ STABLE | 1.13 → 1.05 → 1.06 | -6.4% | 1.0 pts | +0 pips |

**Observaciones:**

- Las tres variantes muestran degradación similar y contenida (5.8%–7.5%). Ninguna colapsa.
- `partial_close` es la única cuyo MaxDD crece entre 10k y 20k (+678 pips). Sigue siendo el DD más bajo en términos absolutos (2,125 vs 8,123 de producción).
- `rr_1_3` tiene un comportamiento inusual: el PF mejora ligeramente de 15k (1.05) a 20k (1.06). Señal de que las últimas 5k barras le favorecen — no es necesariamente estabilidad real, puede ser ruido.
- El WR de las tres variantes es sorprendentemente estable (variación < 1 punto). Las entradas son consistentes.

---

## Fase 5 — Walk Forward

| Variante | WF Stability | Evaluación |
|---|---|---|
| `current_production` | ❌ UNSTABLE | El edge no se mantiene en ventanas de TEST fuera de muestra. |
| `partial_close` | ⚠️ MARGINAL | Edge presente en TEST con cierta degradación. Único resultado positivo. |
| `rr_1_3` | ❌ UNSTABLE | El edge no se mantiene en ventanas de TEST. |

**Nota crítica:** MARGINAL significa que `partial_close` tiene PF ≥ 1.0 en las ventanas de TEST pero con degradación entre 0.3 y 0.6 desde el TRAIN. No es STABLE (que requeriría PF ≥ 1.2 y degradación < 0.3), pero tampoco colapsa. Es el único de los tres que genera rentabilidad fuera de muestra.

---

## Fase 6 — Monte Carlo

| Variante | Prob Ruina | Prob Profit | Stability Score | Evaluación |
|---|---|---|---|---|
| `current_production` | 66.0% | 33.3% | 0.00 | 🔴 Riesgo inaceptable. |
| `partial_close` | **0.0%** | **100.0%** | **51.73** | ✅ Robusto a la varianza. |
| `rr_1_3` | 1.1% | 97.7% | 6.92 | ✅ Riesgo de ruina bajo. |

**Observaciones:**

- `partial_close`: 0% de ruina en 2,000 simulaciones con reorden aleatorio de los 6,500+ trades. Prob profit = 100%. El sistema es robusto independientemente del orden en que lleguen los resultados.
- `rr_1_3`: 1.1% de ruina — aceptable. Pero Prob Profit 97.7% indica que en ~2.3% de los escenarios el sistema termina en pérdida.
- `current_production`: 2 de cada 3 escenarios Monte Carlo terminan en ruina. Confirma que la configuración actual no es viable a largo plazo tal como está.

---

## Fase 7 — Análisis Individual por Variante

### `current_production` (REFERENCIA)

| Métrica | 10k | 15k | 20k |
|---|---|---|---|
| Profit Factor | 1.10 | 1.02 | 1.02 |
| Win Rate | 23.9% | 22.7% | 22.9% |
| Max Drawdown | 8,123 pips | 8,123 pips | 8,123 pips |
| Expectancy | 1.41 pips | 0.32 pips | 0.28 pips |
| Sharpe | 0.038 | 0.008 | 0.007 |
| MC Prob Ruina | — | — | 66.0% |
| WF | — | — | UNSTABLE |
| Stability Score | — | — | 0.00 |

**Diagnóstico:**  
El sistema de producción tiene un edge estructuralmente frágil. PF=1.02 con expectancy de 0.28 pips/trade significa que cualquier incremento en el spread, slippage o cambio de régimen elimina el edge por completo. El MaxDD de 8,123 pips permanece constante de 10k a 20k, lo que indica que el drawdown máximo ocurrió en la primera mitad del dataset y no se ha recuperado completamente. La racha de 214 pérdidas consecutivas es el síntoma más grave: en producción real equivaldría a meses de pérdidas continuas sin señal de recuperación.

**Fortalezas:**
- Profit Captured 87.3% — cuando gana, captura casi todo el movimiento hasta el TP
- MAE ganadoras 7.7 pips — las operaciones correctas apenas retroceden antes de despegar
- Degradación PF contenida (7.5%) — no es un sistema que se rompa bruscamente

**Debilidades críticas:**
- MC Ruin 66% — no es viable como sistema de trading a largo plazo
- WF UNSTABLE — el edge no generaliza fuera de muestra
- Expectancy 0.28 pips/trade — demasiado cerca del margen de costes reales
- Racha máx pérdidas 214 — psicológica y financieramente insostenible
- Stability Score 0.00 — no supera ningún filtro de robustez compuesto

---

### `partial_close`

| Métrica | 10k | 15k | 20k |
|---|---|---|---|
| Profit Factor | 1.96 | 1.88 | 1.85 |
| Win Rate | 54.7% | 53.6% | 54.1% |
| Max Drawdown | 1,447 pips | 2,125 pips | 2,125 pips |
| Expectancy | 7.81 pips | 8.33 pips | 7.88 pips |
| Sharpe | 0.290 | 0.265 | 0.260 |
| MC Prob Ruina | — | — | 0.0% |
| WF | — | — | MARGINAL |
| Stability Score | — | — | 51.73 |

**Diagnóstico:**  
`partial_close` es cualitativamente diferente al resto. No es "un poco mejor" — es un sistema distinto. Al cerrar el 50% al llegar a 2×ATR y dejar correr el resto con trailing, transforma la estructura del trade: pasa de un sistema de alta expectativa/baja frecuencia (producción) a uno de expectativa media/alta frecuencia. El WR sube de 22.9% a 54.1% porque el cierre parcial convierte muchas situaciones que en producción acabarían en SL, en una ganancia parcial. La Expectancy de 7.88 pips/trade es 28x la de producción. El MaxDD de 2,125 pips — menos de la mitad del MaxDD de producción — es posiblemente el dato más relevante para la gestión de riesgo real.

**Fortalezas:**
- PF 1.85 → 1.96 en todos los niveles — edge real, no marginal
- WR 54% — rachas de pérdidas cortas (máx 55), sostenibles psicológicamente
- MC Ruin 0.0% — el más robusto de todos ante varianza del orden de trades
- Expectancy 7.88 pips/trade — 28x la de producción actual
- MaxDD 4x menor que producción en términos absolutos
- Stability Score 51.73 — la única variante con robustez compuesta real
- Degradación PF solo 5.8% en 20k barras — el edge es estable

**Debilidades:**
- WF MARGINAL, no STABLE — hay degradación entre TRAIN y TEST, aunque el sistema sigue siendo rentable en TEST
- Profit Captured 69.3% — deja más dinero sobre la mesa que producción (87.3%). El trailing del segundo tramo no siempre captura el movimiento completo
- Racha máx pérdidas 55 — por debajo de lo crítico pero exige disciplina
- DD creció de 1,447 (10k) a 2,125 (20k) — el peor drawdown ocurrió en la segunda mitad del dataset

---

### `rr_1_3`

| Métrica | 10k | 15k | 20k |
|---|---|---|---|
| Profit Factor | 1.13 | 1.05 | 1.06 |
| Win Rate | 30.3% | 28.8% | 29.2% |
| Max Drawdown | 5,761 pips | 5,761 pips | 5,761 pips |
| Expectancy | 1.73 pips | 0.75 pips | 0.90 pips |
| Sharpe | 0.054 | 0.020 | 0.025 |
| MC Prob Ruina | — | — | 1.1% |
| WF | — | — | UNSTABLE |
| Stability Score | — | — | 6.92 |

**Diagnóstico:**  
`rr_1_3` es una mejora incremental sobre producción pero no resuelve los problemas estructurales. Reducir el TP de 6×ATR a 4.5×ATR sube el WR de 22.9% a 29.2% y reduce la racha de pérdidas de 214 a 73. Esos son avances reales. Pero el edge sigue siendo marginal: PF=1.06, Expectancy=0.90 pips/trade, WF UNSTABLE. El MC Ruin del 1.1% es positivo — el sistema aguanta la varianza del orden de trades. El problema es que el WF revela que el edge no generaliza: en las ventanas de TEST el PF cae por debajo de 1.0, lo que significa que si hubiera operado solo en los períodos de TEST habría perdido dinero.

**Fortalezas:**
- MC Ruin 1.1% — bajo riesgo de ruina ante varianza del orden de trades
- MaxDD 5,761 pips — 30% menor que producción (8,123)
- Racha máx pérdidas 73 — mucho más tolerable que las 214 de producción
- MC Prob Profit 97.7% — en casi todos los escenarios de reordenación, el sistema gana

**Debilidades:**
- WF UNSTABLE — el edge no se mantiene en períodos de TEST fuera de muestra
- PF=1.06 — demasiado marginal. Cualquier cambio en las condiciones de mercado lo hace negativo
- Expectancy 0.90 pips/trade — vulnerable a un spread ligeramente mayor o slippage real
- Stability Score 6.92 — por encima de producción pero todavía muy bajo

---

## Fase 8 — Recomendación Final

### Ranking de recomendación

| Pos | Variante | PF | WR% | MC Ruin | WF | Stability Score |
|---|---|---|---|---|---|---|
| **1** | **`partial_close`** | **1.85** | **54.1%** | **0.0%** | **MARGINAL** | **51.73** |
| 2 | `rr_1_3` | 1.06 | 29.2% | 1.1% | UNSTABLE | 6.92 |
| REF | `current_production` | 1.02 | 22.9% | 66.0% | UNSTABLE | 0.00 |

### Decisión

**Variante recomendada: `partial_close`**

Esta es mi recomendación como si el dinero fuese mío.

`partial_close` es la única variante que supera simultáneamente todos los filtros que importan para la supervivencia a largo plazo:

- **MC Ruin 0.0%** — el sistema aguanta cualquier reordenación de trades sin arruinarse
- **WF MARGINAL** — el edge existe fuera de muestra, aunque con cierta degradación
- **PF 1.85 en 20k barras** — edge real que absorbe costes reales de trading
- **Expectancy 7.88 pips/trade** — margen suficiente para slippage, spread y comisiones
- **MaxDD 2,125 pips** — 74% menor que producción, lo que permite usar tamaños de posición mayores sin arruinarse
- **Stability Score 51.73** — 7x el de `rr_1_3`, que es la segunda mejor

El WF MARGINAL (no STABLE) es la única señal de precaución real. Significa que hay períodos en los que el edge se reduce, pero no desaparece. En un sistema de trading real eso es normal — ningún sistema tiene WF STABLE indefinidamente. Lo importante es que en TEST sigue siendo rentable.

**`rr_1_3` no se elige** porque WF UNSTABLE significa que en las ventanas fuera de muestra el sistema pierde dinero. Con PF=1.06 y Expectancy=0.90, el margen es demasiado pequeño para confiar en que el edge sobreviva a cambios de régimen o a los costes reales de ejecución.

### Condiciones para implementar `partial_close`

1. **Paper trading mínimo 4 semanas** antes de activar en producción. Comparar WR real vs backtest. Si el WR real < 48% (5 puntos menos que el 54% del backtest), pausar e investigar.

2. **No modificar los parámetros** de la variante: cierre parcial al 50% en 2×ATR, trailing del resto a 1.5×ATR, TP máximo 5×ATR. La validación se hizo sobre estos valores exactos.

3. **Monitorear el MaxDD real**. El sistema tiene un MaxDD de 2,125 pips en 20k barras. Si en producción real el DD supera los 3,000 pips desde el pico, revisar antes de continuar.

4. **El circuit breaker sigue siendo necesario**. Con rachas de hasta 55 pérdidas consecutivas, el CB protege en los períodos de baja frecuencia de acierto.

5. **Esta validación aplica solo a EURUSD `eurusd_simple`**. No extrapolar a XAUUSD o BTCEUR sin ejecutar el mismo pipeline completo para esos instrumentos.

---

> *Informe generado por el sistema de validación cuantitativa de BOT-MT5.*  
> *Ninguna configuración de producción fue modificada durante este proceso.*
