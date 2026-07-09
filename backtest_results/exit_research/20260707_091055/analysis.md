# Análisis Exit Research — XAUUSD

**Run ID:** `20260707_091055` | **Generado:** 2026-07-07T10:26:22Z
**Symbol:** `XAUUSD` | **Config producción:** SL=2.0×ATR  TP=5.0×ATR  (RR≈1:2.5)
**Dataset:** 20000 velas H1

---
## Nivel 1 — Decisión Ejecutiva

### → **RECOMENDADO** `partial_close`. Mejora relevante (+148.8% Stability).

| Criterio | Valor |
|---------|-------|
| Producción actual | PF=1.34  WR=35.5%  Stability=27.0 |
| Mejor variante    | `partial_close` — Stability=67.2 pts |
| Recomendada live  | `partial_close` |
| Más rentable      | `partial_close` |
| Mejor WF          | `partial_close` |

---
## Nivel 2 — Tabla Completa

| # | Variante | PF | WR% | Pips | MaxDD | Cap% | WF | Stability |
|--:|---------|---:|----:|-----:|------:|-----:|----:|----------:|
| 1 | `partial_close` | 2.68 | 59.5 | 4468014 | 102227 | 73.1 | STABLE | **67.2** |
| 2 | `rr_1_2` | 1.33 | 39.6 | 957190 | 180013 | 83.5 | MARGINAL | **35.5** |
| 3 | `rr_1_4` | 1.44 | 26.5 | 1542501 | 332392 | 89.9 | UNSTABLE | **31.0** |
| 4 | `trailing_donchian` | 1.35 | 36.0 | 728374 | 204080 | 46.2 | MARGINAL | **28.2** |
| 5 | `current_production` ◄ | 1.34 | 35.5 | 1401963 | 419112 | 87.6 | MARGINAL | **27.0** |
| 6 | `rr_1_35` | 1.36 | 28.1 | 1248416 | 333030 | 88.0 | UNSTABLE | **26.2** |
| 7 | `rr_1_25` | 1.32 | 35.1 | 995327 | 302330 | 86.7 | MARGINAL | **26.1** |
| 8 | `rr_1_3` | 1.31 | 30.8 | 1030222 | 348206 | 86.7 | MARGINAL | **22.5** |
| 9 | `break_even` | 1.10 | 64.3 | 184129 | 175854 | 40.4 | UNSTABLE | **16.6** |
| 10 | `time_exit` | 1.18 | 30.1 | 610745 | 413893 | 63.0 | OVERFITTED | **1.5** |
| 11 | `trailing_atr` | 0.92 | 39.3 | -153776 | 222313 | 43.1 | UNSTABLE | **0.0** |
| 12 | `dynamic_atr` | 0.92 | 39.3 | -153776 | 222313 | 43.1 | UNSTABLE | **0.0** |
| 13 | `trailing_ema` | 0.00 | 0.0 | -4084880 | 4084880 | 0.0 | UNSTABLE | **0.0** |