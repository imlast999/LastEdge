<div align="center">

# LastEdge

**Decoupled Quantitative Trading Ecosystem & Strategy Research Framework**

Research · Optimization · Exit Research · MT5 Execution · Risk Engine v2 · Observability · Discord & Telegram · Web & Mobile UI

![Python](https://img.shields.io/badge/Python-3.10%2B%20%7C%203.13-blue?logo=python&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-18%2B-green?logo=nodedotjs&logoColor=white)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Architecture](https://img.shields.io/badge/Architecture-3%20Independent%20Repos-purple)
![Tests](https://img.shields.io/badge/Tests-146%2F146%20Passed-success)

</div>

---

## Ecosystem Overview

**LastEdge** is organized into **three independent, decoupled systems**, each with its own repository, continuous integration pipeline, and dedicated documentation:

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

1. **LastEdge Trading Engine** (`imlast999/lastedge-trading-engine`):
   - Execution core, MT5 driver, Risk Engine v2, Strategy Loader, and operational verification tools.
   - Test Suite: **89 / 89 passed** | Located in `LastEdge Trading Engine/`
2. **LastEdge Strategy Lab** (`imlast999/lastedge-strategy-lab`):
   - Offline quantitative laboratory, DataLoader, WFA, Monte Carlo, and Promotion security gates.
   - Test Suite: **46 / 46 passed** | Located in `LastEdge Strategy Lab/`
3. **LastEdge App** (`imlast999/lastedge-app`):
   - Web Dashboard, mobile application, Discord slash commands, and Telegram bot.
   - Test Suite: **11 / 11 passed** | Located in `LastEdge App/`

---

## Global System Architecture

For complete details on inter-service communication, security gates, and architectural boundaries, see:
- 🏛️ [**Global System Architecture Specification**](docs/SYSTEM_ARCHITECTURE.md)
- 🤖 [**AI Agent Team Guidelines**](AGENTS.md)
