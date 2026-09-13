<div align="center">

<img src="branding/LastEdge_Banner.png" alt="LastEdge Banner" width="100%">

# LastEdge

**Decoupled Quantitative Trading Ecosystem & Strategy Research Framework**

Research · Optimization · Exit Research · MT5 Execution · Risk Engine v2 · Observability · Discord & Telegram · Web & Mobile UI

[![Trading Engine](https://img.shields.io/badge/GitHub-Trading--Engine-blue?logo=github)](https://github.com/imlast999/lastedge-trading-engine)
[![Strategy Lab](https://img.shields.io/badge/GitHub-Strategy--Lab-purple?logo=github)](https://github.com/imlast999/lastedge-strategy-lab)
[![App](https://img.shields.io/badge/GitHub-App-green?logo=github)](https://github.com/imlast999/lastedge-app)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Tests](https://img.shields.io/badge/Tests-146%2F146%20Passed-success)

</div>

---

## Ecosystem Overview

**LastEdge** is structured as an ecosystem of **three independent, decoupled repositories**, each with its own continuous integration pipeline, tests, and dedicated technical documentation:

```text
                                 ┌─────────────────────────────────────────┐
                                 │              LastEdge App               │
                                 │       imlast999/lastedge-app            │
                                 │  • Web Dashboard (:8080)                │
                                 │  • Mobile App (React Native/Expo)       │
                                 │  • Discord & Telegram Bot Adapters      │
                                 └────────────────────┬────────────────────┘
                                                      │
                                           HTTP REST Communication
                                                      │
                                 ┌────────────────────┴────────────────────┐
                                 ▼                                         ▼
     ┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐
     │         LastEdge Trading Engine         │   │          LastEdge Strategy Lab          │
     │    imlast999/lastedge-trading-engine    │   │      imlast999/lastedge-strategy-lab    │
     │  • MT5 Execution Client & Reconnect     │   │  • Historical Data Pipeline (Parquet)   │
     │  • Risk Engine v2 (Sizing, Margin)      │   │  • Backtesting & Realistic Trade Costs  │
     │  • Circuit Breaker & Daily Drawdown     │   │  • Walk Forward Analysis (WFA) Engine   │
     │  • Production REST API (:8081)          │   │  • Monte Carlo Risk-of-Ruin Engine      │
     │  • Trade Journal SQLite (trading.db)    │   │  • Promotion Security Gates (SHA-256)   │
     │  • Ingestion & Verifier (SignalIntent)  │   │  • Research REST API (:8082)            │
     │  • Approved Production Strategies       │   │  • Unified Research CLI (run_pipeline)  │
     └─────────────────────────────────────────┘   └─────────────────────────────────────────┘
```

---

## Repositories & Quick Access

The ecosystem consists of the following 3 standalone repositories:

| Repository | GitHub Link | Role | Test Suite |
| :--- | :--- | :--- | :---: |
| ⚡ **LastEdge Trading Engine** | [**`imlast999/lastedge-trading-engine`**](https://github.com/imlast999/lastedge-trading-engine) | Execution core, MetaTrader 5 driver, Risk Engine v2, dynamic strategy loader, and operational verification tools. | **89 / 89 PASSED** ✅ |
| 🔬 **LastEdge Strategy Lab** | [**`imlast999/lastedge-strategy-lab`**](https://github.com/imlast999/lastedge-strategy-lab) | Offline quantitative research laboratory, DataLoader, WFA, Monte Carlo, Exit Research, and promotion security gates. | **46 / 46 PASSED** ✅ |
| 📱 **LastEdge App** | [**`imlast999/lastedge-app`**](https://github.com/imlast999/lastedge-app) | Web Dashboard (:8080), React Native / Expo mobile application, Discord slash commands, and Telegram bot. | **11 / 11 PASSED** ✅ |

---

## Inter-Service Communication & Architecture

1. **Strategy Promotion (Lab ➔ Engine)**:
   * Strategy Lab validates candidate strategies through empirical quantitative gates (Walk Forward WES $\ge 0.60$, Monte Carlo Ruin $\le 5\%$).
   * Promoted strategies are frozen and exported as verified packages (`.py` + `.json` sidecar) containing `code_sha256` and `config_hash`.
   * Trading Engine verifies cryptographic integrity upon startup via `services/strategy_loader.py` and dynamically registers them into production without manual code copying.

2. **Telemetry & Control (Engine & Lab ➔ App)**:
   * Trading Engine exposes a local REST API on port `8081` (`/health`, `/positions`, `/account`, `/risk`).
   * Strategy Lab exposes a local REST API on port `8082` (`/health`, `/candidates`, `/experiments`).
   * LastEdge App queries both services using decoupled HTTP clients (`trading_client.py`, `research_client.py`) with automatic offline fallbacks and graceful degradation.

For detailed technical documentation, specifications, and guides, refer directly to each repository's docs:
- ⚡ [**Trading Engine Documentation**](https://github.com/imlast999/lastedge-trading-engine/tree/main/docs)
- 🔬 [**Strategy Lab Documentation**](https://github.com/imlast999/lastedge-strategy-lab/tree/main/docs)
- 📱 [**App Documentation**](https://github.com/imlast999/lastedge-app/tree/main/docs)
