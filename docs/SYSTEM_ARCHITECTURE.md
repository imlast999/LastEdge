# LastEdge — Global Ecosystem Architecture

> **Document:** Global System Architecture  
> **Status:** Production Standard  
> **Ecosystem:** 3 Decoupled Independent Systems  

---

## 1. What is LastEdge?

**LastEdge** is an enterprise-grade quantitative trading and strategy development ecosystem built for multi-asset automated trading (Forex, Metals, Crypto) with MetaTrader 5.

The ecosystem is architecturally divided into **three independent systems**, each maintained in its own dedicated repository:

1. **`lastedge-trading-engine`** (`LastEdge Trading Engine/`): Production execution engine, Risk Engine v2, automated order loops, position management, and local REST API (`:8081`).
2. **`lastedge-strategy-lab`** (`LastEdge Strategy Lab/`): Quantitative research laboratory, Historical DataLoader, Walk Forward Analysis (WFA), Monte Carlo stress simulations, Exit Research framework, and Strategy Promotion pipeline (`:8082`).
3. **`lastedge-app`** (`LastEdge App/`): Unified control plane, Web Dashboard, Mobile application, and decoupled Discord/Telegram messaging adapters (`:8080`).

---

## 2. Global Architecture Diagram

```text
                                 ┌─────────────────────────────────────────┐
                                 │              LastEdge App               │
                                 │                                         │
                                 │  • Web Dashboard (:8080)                │
                                 │  • Mobile App (React Native/Expo)       │
                                 │  • Discord & Telegram Bot Adapters      │
                                 │  • TradingClient & ResearchClient       │
                                 └────────────────────┬────────────────────┘
                                                      │
                                           HTTP REST Communication
                                                      │
                                 ┌────────────────────┴────────────────────┐
                                 ▼                                         ▼
     ┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐
     │         LastEdge Trading Engine         │   │          LastEdge Strategy Lab          │
     │                                         │   │                                         │
     │  • MT5 Execution Client (sub-second)    │   │  • Historical Data Pipeline (Parquet)   │
     │  • Risk Engine v2 (Sizing, Margin)      │   │  • Backtesting & Realistic Trade Costs  │
     │  • Circuit Breaker & Daily Drawdown     │   │  • Walk Forward Analysis (WFA) Engine   │
     │  • Dynamic Trailing Stops & Partial SL  │   │  • Monte Carlo Risk-of-Ruin Engine      │
     │  • Trade Journal & SQLite (trading.db)  │   │  • Exit Research Framework & Variants   │
     │  • Production REST API (:8081)          │   │  • Promotion Security Gates (SHA-256)   │
     │  • Dynamic Strategy Loader              │   │  • Research REST API (:8082)            │
     └─────────────────────────────────────────┘   └─────────────────────────────────────────┘
                         ▲                                         │
                         │       EXPORTED STANDARDIZED PACKAGE     │
                         │          (BaseStrategy + SHA-256)       │
                         └─────────────────────────────────────────┘
```

---

## 3. Core System Responsibilities & Boundaries

| Domain | LastEdge Trading Engine | LastEdge Strategy Lab | LastEdge App |
|---|:---:|:---:|:---:|
| **MetaTrader 5 Order Execution** | ✅ Primary Owner | ❌ Prohibited | ❌ Prohibited |
| **Risk Engine v2 & Margin Safeguards** | ✅ Primary Owner | ❌ Prohibited | ❌ Prohibited |
| **Live Order Lifecycle & Trailing Stops**| ✅ Primary Owner | ❌ Prohibited | ❌ Prohibited |
| **Historical Data Store & Offline Loading**| ❌ Prohibited | ✅ Primary Owner | ❌ Prohibited |
| **Walk Forward & Monte Carlo Research** | ❌ Prohibited | ✅ Primary Owner | ❌ Prohibited |
| **Exit Strategy Research** | ❌ Prohibited | ✅ Primary Owner | ❌ Prohibited |
| **Strategy Promotion & Hashing** | ❌ Consumer (`strategies/`) | ✅ Primary Owner (`services/promotion.py`) | ❌ Prohibited |
| **Web Dashboard UI & Bot Adapters** | ❌ Prohibited | ❌ Prohibited | ✅ Primary Owner |

---

## 4. Architectural Invariants

1. **Zero Cross-System Python Imports:** No Python module in any system directly imports files from another system.
2. **REST Decoupling:** All inter-system telemetry flows over REST APIs with graceful offline degradation.
3. **Canonical Strategy Contract:** `BaseStrategy` and `StrategyMetadata` share an identical signature across Lab and Engine, allowing promoted code to run in production with zero manual translation.
4. **Promotion Security:** Strategies cannot reach production without passing all 6 quantitative gates and cryptographic hash verifications.
