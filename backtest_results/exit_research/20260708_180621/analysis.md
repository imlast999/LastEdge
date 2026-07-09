# Análisis Exit Research — BTCEUR

**Run ID:** `20260708_180621` | **Generado:** 2026-07-08T19:35:59Z
**Symbol:** `BTCEUR` | **Config producción:** SL=2.0×ATR  TP=3.0×ATR  (RR≈1:1.5)
**Dataset:** 20000 velas H1

---
## Nivel 1 — Decisión Ejecutiva

### → **RECOMENDADO** `partial_close`. Mejora relevante (+68.9% Stability).

| Criterio | Valor |
|---------|-------|
| Producción actual | PF=1.19  WR=45.3%  Stability=33.4 |
| Mejor variante    | `partial_close` — Stability=56.4 pts |
| Recomendada live  | `partial_close` |
| Más rentable      | `partial_close` |
| Mejor WF          | `partial_close` |

---
## Nivel 2 — Tabla Completa

| # | Variante | PF | WR% | Pips | MaxDD | Cap% | WF | Stability |
|--:|---------|---:|----:|-----:|------:|-----:|----:|----------:|
| 1 | `partial_close` | 2.08 | 55.9 | 1469997 | 55012 | 68.7 | STABLE | **56.4** |
| 2 | `current_production` ◄ | 1.19 | 45.3 | 313678 | 72407 | 82.1 | MARGINAL | **33.4** |
| 3 | `rr_1_2` | 1.09 | 36.8 | 129672 | 90188 | 81.5 | UNSTABLE | **13.2** |
| 4 | `trailing_donchian` | 1.12 | 31.9 | 120856 | 117818 | 47.2 | UNSTABLE | **8.8** |
| 5 | `rr_1_4` | 1.07 | 22.3 | 127729 | 118355 | 88.8 | MARGINAL | **2.1** |
| 6 | `rr_1_35` | 1.06 | 24.3 | 101193 | 108760 | 86.2 | MARGINAL | **0.0** |
| 7 | `rr_1_3` | 1.03 | 26.7 | 47497 | 110064 | 86.1 | MARGINAL | **0.0** |
| 8 | `rr_1_25` | 1.03 | 30.4 | 40941 | 116365 | 85.8 | UNSTABLE | **0.0** |
| 9 | `break_even` | 0.81 | 62.2 | -161733 | 182508 | 33.7 | UNSTABLE | **0.0** |
| 10 | `time_exit` | 1.02 | 30.1 | 24768 | 221482 | 57.6 | UNSTABLE | **0.0** |
| 11 | `trailing_atr` | 0.64 | 36.9 | -375762 | 407794 | 38.5 | UNSTABLE | **0.0** |
| 12 | `dynamic_atr` | 0.64 | 36.9 | -375762 | 407794 | 38.5 | UNSTABLE | **0.0** |
| 13 | `trailing_ema` | 0.00 | 0.0 | -1918978 | 1918978 | 0.0 | UNSTABLE | **0.0** |