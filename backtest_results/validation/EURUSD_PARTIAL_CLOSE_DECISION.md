# Decision Record — EURUSD Partial Close

**Fecha:** 2026-07-03  
**Versión:** LastEdge v1.1  
**Tipo:** Mejora de salida validada cuantitativamente  

---

## Decisión

La configuración de salida de EURUSD pasa de `eurusd_simple` (RR 1:4 fijo) a `eurusd_partial` (50% parcial + trailing), validada mediante Exit Research.

**Esta mejora NO proviene de una modificación arbitraria de parámetros.**  
Proviene de un proceso de investigación cuantitativa estructurado que duró varias sesiones.

---

## Proceso seguido

### 1. Exit Research (run_id: `20260702_225143`)

- Dataset: 20.000 velas H1 EURUSD
- Variantes evaluadas: 13 (12 + current_production como referencia)
- Archivos: `backtest_results/exit_research/20260702_225143/`

### 2. Validación cruzada (run_id: `val_20260703_160132`)

- Finalistas seleccionadas: `partial_close`, `rr_1_3`
- Niveles: 10k / 15k / 20k velas H1
- Walk Forward + Monte Carlo incluidos
- Archivos: `backtest_results/validation/val_20260703_160132/`

---

## Comparativa de resultados (20.000 velas H1)

| Métrica | `eurusd_simple` (antes) | `eurusd_partial` (ahora) | Mejora |
|---|---|---|---|
| Profit Factor | 1.02 | **1.85** | +81% |
| Win Rate | 22.9% | **54.1%** | +136% |
| Max Drawdown | 8,123 pips | **2,125 pips** | -74% |
| Expectancy | 0.28 pips/trade | **7.88 pips/trade** | +2,714% |
| MC Prob Ruina | 66.0% | **0.0%** | — |
| WF Stability | UNSTABLE | **MARGINAL** | — |
| Stability Score | 0.00 | **51.73** | — |
| Racha pérdidas | 214 | **55** | -74% |

---

## Parámetros de salida validados

```
SL inicial:          1.5 × ATR
Cierre 50%:          al llegar a 2.0 × ATR de beneficio
Trailing SL:         1.5 × ATR del segundo tramo
TP máximo:           5.0 × ATR del segundo tramo
```

**No modificar estos parámetros sin ejecutar una nueva validación completa.**

---

## Lo que NO cambió

- Lógica de entrada: idéntica a `eurusd_simple`
- Filtros: EMA20/50/200, RSI, ATR, separación, distancia a EMA20
- Risk management: SL inicial 1.5×ATR, mismos cooldowns y circuit breaker
- Configuración de sesiones: London, NewYork, Overlap

---

## Estrategia anterior

`eurusd_simple` permanece disponible como referencia histórica:
- Clase: `EURUSDStrategy` en `strategies/eurusd.py`
- Símbolo de registro: `EURUSD_LEGACY`
- Alias en signals.py: `eurusd_simple`

No está activa en producción pero puede usarse para comparaciones y backtests.

---

## Fase siguiente

Validación continua en cuenta Demo MT5 durante mínimo 4 semanas.  
Criterio de éxito: WR real ≥ 48% (±5 puntos del backtest), PF ≥ 1.3 acumulado.  
No se modificarán parámetros durante este período.

> *Generado por el proceso de investigación cuantitativa de LastEdge.*
