# Exit Research Report — EURUSD

**Run ID:** `20260702_225143`  
**Generated:** 2026-07-03T00:30:50Z  
**Validation mode:** no_optimization  

---

## Tabla comparativa

| Rank | Variante | PF | WR% | Pips | MaxDD | MAE | MFE | Capturado% | Sharpe | WF | MC Ruin | Stability |
|-----:|---------|---:|----:|-----:|------:|----:|----:|-----------:|-------:|----:|--------:|----------:|
| 1 | partial_close | 1.85 | 54.1 | 71062.1 | 2125.2 | 16.7 | 29.9 | 69.3 | 0.260 | MARGINAL | 0.000 | **51.74** |
| 2 | rr_1_3 | 1.06 | 29.2 | 5915.9 | 5761.4 | 22.1 | 28.9 | 83.4 | 0.025 | UNSTABLE | 0.012 | **6.93** |
| 3 | rr_1_25 | 1.02 | 32.2 | 1497.0 | 5125.2 | 21.5 | 26.5 | 80.2 | 0.007 | UNSTABLE | 0.652 | **0.00** |
| 4 | rr_1_2 | 0.97 | 36.4 | -2636.2 | 6154.7 | 20.6 | 23.8 | 76.0 | -0.014 | UNSTABLE | 0.885 | **0.00** |
| 5 | rr_1_35 | 1.04 | 25.8 | 4177.9 | 6468.2 | 22.9 | 30.9 | 85.9 | 0.017 | UNSTABLE | 0.141 | **0.00** |
| 6 | current_production | 1.02 | 22.9 | 1819.4 | 8122.8 | 23.4 | 32.7 | 87.3 | 0.007 | UNSTABLE | 0.659 | **0.00** |
| 7 | rr_1_4 | 1.02 | 22.9 | 1819.4 | 8122.8 | 23.4 | 32.7 | 87.3 | 0.007 | UNSTABLE | 0.659 | **0.00** |
| 8 | time_exit | 0.99 | 24.7 | -567.5 | 9790.3 | 22.9 | 36.2 | 64.7 | -0.002 | UNSTABLE | 0.949 | **0.00** |
| 9 | trailing_donchian | 0.82 | 24.1 | -11212.5 | 11371.1 | 15.1 | 23.6 | 51.6 | -0.063 | UNSTABLE | 0.998 | **0.00** |
| 10 | break_even | 0.68 | 59.6 | -18064.4 | 19150.2 | 15.6 | 18.8 | 83.7 | -0.125 | UNSTABLE | 1.000 | **0.00** |
| 11 | trailing_atr | 0.56 | 34.3 | -28818.8 | 28827.3 | 16.5 | 20.6 | 42.7 | -0.222 | UNSTABLE | 1.000 | **0.00** |
| 12 | dynamic_atr | 0.56 | 34.3 | -28818.8 | 28827.3 | 16.5 | 20.6 | 42.7 | -0.222 | UNSTABLE | 1.000 | **0.00** |
| 13 | trailing_ema | 0.00 | 0.0 | -119177.1 | 119177.1 | 28.4 | 31.4 | 0.0 | -2.742 | UNSTABLE | 1.000 | **0.00** |

---

## Degradación Profit Factor

| Variante | 5k | 10k | 15k | 20k |
|---------|---:|----:|----:|----:|
| current_production | 1.17 | 1.10 | 1.02 | 1.02 |
| rr_1_2 | 1.06 | 1.03 | 0.97 | 0.97 |
| rr_1_25 | 1.17 | 1.09 | 1.01 | 1.02 |
| rr_1_3 | 1.21 | 1.13 | 1.05 | 1.06 |
| rr_1_35 | 1.17 | 1.11 | 1.03 | 1.04 |
| rr_1_4 | 1.17 | 1.10 | 1.02 | 1.02 |
| trailing_atr | 0.54 | 0.57 | 0.56 | 0.56 |
| trailing_ema | 0.00 | 0.00 | 0.00 | 0.00 |
| dynamic_atr | 0.54 | 0.57 | 0.56 | 0.56 |
| break_even | 0.84 | 0.75 | 0.67 | 0.68 |
| partial_close | 2.02 | 1.96 | 1.89 | 1.85 |
| trailing_donchian | 0.93 | 0.83 | 0.82 | 0.82 |
| time_exit | 1.24 | 1.08 | 0.98 | 0.99 |

---

## Análisis MAE / MFE

| Variante | MAE medio | MFE medio | MAE ganadores | MFE ganadores | Capturado% |
|---------|----------:|----------:|--------------:|--------------:|-----------:|
| current_production | 23.4 | 32.7 | 7.7 | 80.9 | 87.3 |
| rr_1_2 | 20.6 | 23.8 | 7.8 | 46.4 | 76.0 |
| rr_1_25 | 21.5 | 26.5 | 7.9 | 55.4 | 80.2 |
| rr_1_3 | 22.1 | 28.9 | 7.8 | 63.9 | 83.4 |
| rr_1_35 | 22.9 | 30.9 | 7.7 | 72.1 | 85.9 |
| rr_1_4 | 23.4 | 32.7 | 7.7 | 80.9 | 87.3 |
| trailing_atr | 16.5 | 20.6 | 6.2 | 41.9 | 42.7 |
| trailing_ema | 28.4 | 31.4 | 0.0 | 0.0 | 0.0 |
| dynamic_atr | 16.5 | 20.6 | 6.2 | 41.9 | 42.7 |
| break_even | 15.6 | 18.8 | 7.8 | 28.8 | 83.7 |
| partial_close | 16.7 | 29.9 | 7.6 | 46.0 | 69.3 |
| trailing_donchian | 15.1 | 23.6 | 5.0 | 65.7 | 51.6 |
| time_exit | 22.9 | 36.2 | 9.0 | 94.0 | 64.7 |

---

## Conclusiones

- **🏆 Mayor rentabilidad:** `partial_close`
- **🛡 Menor drawdown:** `partial_close`
- **💎 Más robusta (Stability Score):** `partial_close`
- **📈 Mejor Walk-Forward:** `—`
- **🎲 Menor probabilidad de ruina:** `partial_close`
- **✅ Recomendada para operar:** `partial_close`

---

> *Generado automáticamente por Exit Research Framework — BOT-MT5*
