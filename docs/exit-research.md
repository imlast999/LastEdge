# Exit Research Framework — LastEdge

> **Authoritative Single Source of Truth for Exit Strategy Research & Evaluation**

---

## 1. Overview & Objective

Exit Research is the quantitative framework within LastEdge designed to analyze and optimize position exit logic. Entry setups determine *when* to open a position, but exit management determines *how much profit is captured* and *how stable the strategy remains under changing market volatility*.

The Exit Research framework compares **13 standardized exit variants** for a given strategy over long sample sizes (typically 20,000 H1 candles, ~3 years of historical data), evaluating profit capture efficiency, adverse excursion, walk-forward degradation, and Monte Carlo ruin probabilities.

---

## 2. The 13 Exit Variants

Every Exit Research run evaluates the exact same entry signals against 13 distinct exit algorithms:

| Variant ID | Name / Description | Exit Logic & Mechanics |
|---|---|---|
| `baseline_1_4` | Baseline Fixed RR (1:4) | Fixed SL @ 1.5× ATR, Fixed TP @ 6.0× ATR (Original v1.0 baseline) |
| `fixed_1_1` | Fixed RR 1:1 | SL @ 1.5× ATR, TP @ 1.5× ATR |
| `fixed_1_2` | Fixed RR 1:2 | SL @ 1.5× ATR, TP @ 3.0× ATR |
| `fixed_1_3` | Fixed RR 1:3 | SL @ 1.5× ATR, TP @ 4.5× ATR |
| `fixed_1_5` | Fixed RR 1:5 | SL @ 1.5× ATR, TP @ 7.5× ATR |
| `partial_close` | Partial Close (50% + Trail) | **Promoted v1.1 Standard:** Closes 50% lot @ 2.0× ATR profit; moves remaining 50% to Trailing SL @ 1.5× ATR; final target @ 5.0× ATR |
| `partial_close_33` | Partial Close (33% Tri-stage) | Closes 33% @ 1.5× ATR, 33% @ 3.0× ATR, trails remaining 34% @ 1.5× ATR |
| `breakeven_1_2` | Early Breakeven | Fixed SL @ 1.5× ATR, TP @ 4.5× ATR; moves SL to entry (breakeven) when profit reaches +1.5× ATR |
| `trailing_atr_1_5` | Pure ATR Trailing | No fixed TP; trails SL dynamically at 1.5× ATR distance behind highest price reached |
| `trailing_atr_2_0` | Wide ATR Trailing | No fixed TP; trails SL dynamically at 2.0× ATR distance |
| `mae_mfe_adaptive` | MAE/MFE Adaptive Exit | Uses historical MAE/MFE distribution to trigger early exit when floating profit reaches 80% of median winner MFE |
| `time_based_24h` | Time-Based Cut (24h) | Fixed SL/TP as baseline; forcibly closes position after 24 H1 bars regardless of profit/loss |
| `time_based_48h` | Time-Based Cut (48h) | Fixed SL/TP as baseline; forcibly closes position after 48 H1 bars regardless of profit/loss |

---

## 3. Evaluated Metrics & Statistical Models

For each variant, the Exit Research engine (`core/exit_research/`) computes an exhaustive suite of performance and robustness metrics:

### Profitability Metrics
- **Profit Factor (PF):** Gross Profit / Gross Loss (with spread + commission included).
- **Win Rate (WR %):** Winning trades / Total trades.
- **Net Pips:** Cumulative pip gain or loss.
- **Expectancy:** Average gain per trade in pips.
- **Avg Win / Avg Loss Ratio:** Payoff ratio per trade.

### Excursion & Quality Metrics
- **MAE (Maximum Adverse Excursion):** Maximum drawdown experienced during the lifetime of winning vs losing trades.
- **MFE (Maximum Favorable Excursion):** Maximum floating profit achieved before trade exit.
- **Profit Captured (%):** Ratio of realized profit pips to MFE pips `(Exit Price - Entry) / (MFE Price - Entry)`. Measures how efficiently the exit variant harvests available market moves.

### Robustness & Risk Metrics
- **Max Drawdown (Pips & %):** Peak-to-trough decline.
- **Consecutive Losses:** Maximum sequence of losing trades.
- **Walk-Forward Stability (4 Windows):** Retests variant across 4 rolling TRAIN/TEST windows to check out-of-sample consistency (classified as PASS, MARGINAL, or FAIL).
- **Monte Carlo Permutations (2,000 Runs):** Bootstraps trade sequences with replacement to calculate ruin probability (Equity < 50% of starting balance) and percentile curves (p5, p25, p50, p75, p95).
- **Stability Score (0–100):** Aggregate score combining Profit Factor, Win Rate stability, Walk-Forward pass rate, and Monte Carlo ruin probability.

---

## 4. Execution Guide & CLI

Exit Research runs are orchestrated by `core/exit_research/runner.py` via dedicated CLI scripts:

### Running EURUSD Exit Research

```bash
# Full research run (20,000 H1 candles, ~90 minutes)
python run_exit_research.py --bars 20000

# Quick evaluation run (5,000 candles)
python run_exit_research.py --bars 5000
```

### Running XAUUSD Exit Research

```bash
python run_exit_research_xauusd.py --bars 20000
```

---

## 5. REST API Integration

Exit Research artifacts are exposed to the Web Dashboard and React Native Mobile App via the Express API Server (`mobile-app/.../api-server/src/routes/research.ts`):

| Method | Endpoint Path | Description |
|---|---|---|
| `GET` | `/api/research/experiments` | Queries and filters the Research Database (by symbol, strategy, decision_status, tag, search, min_pf) |
| `POST` | `/api/research/experiments` | Registers a new reproducible research experiment record in `research_experiments` SQLite table |
| `GET` | `/api/research/experiments/:id` | Retrieves complete experiment details (git_commit, bot_version, hypothesis, config_json, metrics) |
| `PATCH` | `/api/research/experiments/:id` | Updates research decision status (`PROMOTED`, `REJECTED`, `CANDIDATE`), rationale, hypothesis, or notes |
| `GET` | `/api/research/experiments/:id/reopen` | Returns exact reproducible payload and parameter recipe to re-run or clone the experiment |
| `GET` | `/api/research/exit-research` | Lists all available Exit Research sessions in `backtest_results/exit_research/` |
| `POST` | `/api/research/exit-research` | Queues a new Exit Research task in `backtest_tasks` SQLite table |
| `GET` | `/api/research/exit-research/:runId` | Returns `summary.json` enriched with `comparison_table` and `degradation_table` |
| `GET` | `/api/research/exit-research/:runId/trades` | Returns trade list for a specific variant in a run |
| `GET` | `/api/research/exit-research/:runId/montecarlo` | Computes Monte Carlo bootstrap equity percentile curves for a variant |

---

## 6. Output Artifacts & Directory Structure

Every Exit Research run writes a self-contained session directory under `backtest_results/exit_research/{run_id}/`:

```
backtest_results/exit_research/20260702_225143/
├── summary.json          # Master run metadata, comparison table, and Stability Scores
├── trades.csv            # Detailed trade log for all 13 variants (entry, exit, MAE, MFE, variant)
├── mae_mfe.csv           # Per-trade MAE/MFE excursion measurements
├── comparison.csv        # Summary CSV table comparing all 13 variants side-by-side
├── analysis.md           # Automated Markdown statistical report
└── report.md             # Final executive summary and recommendation report
```

---

## 7. Strategy Promotion Criteria

To promote an exit variant from Exit Research to active production validation (Demo MT5), it must satisfy **all** of the following quantitative conditions:

1. **Stability Score:** Aggregated Stability Score **≥ 20.0**.
2. **Monte Carlo Ruin Probability:** Ruin probability **≤ 5.0%** across 2,000 bootstrap simulations.
3. **Walk-Forward Performance:** Classified as **MARGINAL** or **PASS** across 4 rolling Walk-Forward windows.
4. **Profit Factor:** PF **≥ 1.20** with real transaction costs (spread + commission) included.
5. **No Circuit Breaker Inflation:** Profit Factor **> 1.0** even when evaluated without Circuit Breaker intervention (proving true baseline edge).
