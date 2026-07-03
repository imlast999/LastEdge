# Análisis Exit Research — eurusd_simple

**Run ID:** `20260702_225143` | **Generado:** 2026-07-03T00:30:50Z
**Estrategia:** `eurusd_simple` | **Config actual:** SL=1.5×ATR  TP=6.0×ATR  (RR≈1:4.0)
**Dataset:** 20000 velas H1

---
## NIVEL 1 — Resumen Ejecutivo

### `eurusd_simple` → **MANTENER salida actual** — no se observa mejora significativa.

| Criterio | Valor |
|---------|-------|
| Salida actual (producción) | PF=1.02  WR=22.9%  Stability=0.0 |
| Mejor variante (Stability) | `partial_close` — 51.7 pts |
| Más rentable (total pips) | `partial_close` |
| Mejor Walk-Forward | `ninguna con WF STABLE` |
| Menor prob. ruina | `partial_close` |
| Recomendada para operar | `partial_close` |

---
## NIVEL 2 — Análisis Completo

### Tabla comparativa (todas las variantes)

| # | Variante | PF | WR% | Pips | MaxDD | MAE | MFE | Cap% | Sharpe | WF | Stability |
|--:|---------|---:|----:|-----:|------:|----:|----:|-----:|-------:|----:|----------:|
| 1 | `partial_close` | 1.85 | 54.1 | 71062.1 | 2125.2 | 16.7 | 29.9 | 69.3 | 0.260 | MARGINAL | **51.74** |
| 2 | `rr_1_3` | 1.06 | 29.2 | 5915.9 | 5761.4 | 22.1 | 28.9 | 83.4 | 0.025 | UNSTABLE | **6.93** |
| 3 | `rr_1_25` | 1.02 | 32.2 | 1497.0 | 5125.2 | 21.5 | 26.5 | 80.2 | 0.007 | UNSTABLE | **0.00** |
| 4 | `rr_1_2` | 0.97 | 36.4 | -2636.2 | 6154.7 | 20.6 | 23.8 | 76.0 | -0.014 | UNSTABLE | **0.00** |
| 5 | `rr_1_35` | 1.04 | 25.8 | 4177.9 | 6468.2 | 22.9 | 30.9 | 85.9 | 0.017 | UNSTABLE | **0.00** |
| 6 | `current_production` ◄ producción | 1.02 | 22.9 | 1819.4 | 8122.8 | 23.4 | 32.7 | 87.3 | 0.007 | UNSTABLE | **0.00** |
| 7 | `rr_1_4` | 1.02 | 22.9 | 1819.4 | 8122.8 | 23.4 | 32.7 | 87.3 | 0.007 | UNSTABLE | **0.00** |
| 8 | `time_exit` | 0.99 | 24.7 | -567.5 | 9790.3 | 22.9 | 36.2 | 64.7 | -0.002 | UNSTABLE | **0.00** |
| 9 | `trailing_donchian` | 0.82 | 24.1 | -11212.5 | 11371.1 | 15.1 | 23.6 | 51.6 | -0.063 | UNSTABLE | **0.00** |
| 10 | `break_even` | 0.68 | 59.6 | -18064.4 | 19150.2 | 15.6 | 18.8 | 83.7 | -0.125 | UNSTABLE | **0.00** |
| 11 | `trailing_atr` | 0.56 | 34.3 | -28818.8 | 28827.3 | 16.5 | 20.6 | 42.7 | -0.222 | UNSTABLE | **0.00** |
| 12 | `dynamic_atr` | 0.56 | 34.3 | -28818.8 | 28827.3 | 16.5 | 20.6 | 42.7 | -0.222 | UNSTABLE | **0.00** |
| 13 | `trailing_ema` | 0.00 | 0.0 | -119177.1 | 119177.1 | 28.4 | 31.4 | 0.0 | -2.742 | UNSTABLE | **0.00** |

### Análisis MAE / MFE (calidad de salida)

| Variante | MAE gan. | MAE perd. | MFE gan. | MFE perd. | Cap% | Avg Win | Avg Loss |
|---------|----------:|----------:|----------:|----------:|-----:|--------:|---------:|
| `partial_close` | 7.6 | 27.3 | 46.0 | 10.9 | 69.3 | 31.9 | 20.0 |
| `rr_1_3` | 7.8 | 28.0 | 63.9 | 14.4 | 83.4 | 53.3 | 20.7 |
| `rr_1_25` | 7.9 | 28.0 | 55.4 | 12.8 | 80.2 | 44.4 | 20.8 |
| `rr_1_2` | 7.8 | 27.9 | 46.4 | 10.9 | 76.0 | 35.2 | 20.8 |
| `rr_1_35` | 7.7 | 28.1 | 72.1 | 16.5 | 85.9 | 61.9 | 20.7 |
| `current_production` | 7.7 | 28.1 | 80.9 | 18.4 | 87.3 | 70.7 | 20.7 |
| `rr_1_4` | 7.7 | 28.1 | 80.9 | 18.4 | 87.3 | 70.7 | 20.7 |
| `time_exit` | 9.0 | 27.5 | 94.0 | 17.2 | 64.7 | 60.8 | 20.0 |
| `trailing_donchian` | 5.0 | 18.2 | 65.7 | 10.3 | 51.6 | 33.9 | 12.4 |
| `break_even` | 7.8 | 27.1 | 28.8 | 4.0 | 83.7 | 24.1 | 11.2 |
| `trailing_atr` | 6.2 | 21.8 | 41.9 | 9.5 | 42.7 | 17.9 | 14.9 |
| `dynamic_atr` | 6.2 | 21.8 | 41.9 | 9.5 | 42.7 | 17.9 | 14.9 |
| `trailing_ema` | 0.0 | 28.4 | 0.0 | 31.4 | 0.0 | 0.0 | 20.4 |

### Interpretación cuantitativa

- **TP bien calibrado:** `profit_captured_pct=87.3%`. Las salidas capturan más del 60% del movimiento favorable.
- **SL utilizado eficientemente:** MAE medio en perdedoras (28.1 pips) cercano al SL configurado — el precio tiende a alcanzar el stop antes de cerrar.
- **Duración normal:** 20 velas H1 (≈ 20h).
- **Win Rate bajo (22.9%):** el sistema depende de un RR alto para ser rentable. Con RR=4.0 teórico, necesita WR > 20% para breakeven. Reducir el RR podría mejorar el WR y hacer el sistema más consistente.

---
### Potential Improvements

_Solo mejoras respaldadas por datos cuantitativos de esta ejecución._

1. **Reducir RR → `rr_1_3`**  _(Stability +6.9 pts vs producción)_  
   PF=1.06  WR=29.2%  Cap%=83.4%  MaxDD=5761.4
   → El mercado tiende a alcanzar un TP más cercano antes de revertir.

