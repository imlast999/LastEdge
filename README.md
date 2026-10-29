<div align="center">

<img src="branding/LastEdge_Banner.png" alt="LastEdge Banner" width="100%">

# LastEdge

**Decoupled Quantitative Trading Ecosystem & Strategy Research Framework**

Research • Walk-Forward Analysis • Monte Carlo • MT5 Execution • Risk Engine v2 • Circuit Breakers • Web Dashboard • Mobile App (React Native/Expo) • Discord & Telegram Bots

[![Trading Engine](https://img.shields.io/badge/GitHub-Trading--Engine-blue?logo=github)](https://github.com/imlast999/lastedge-trading-engine)
[![Strategy Lab](https://img.shields.io/badge/GitHub-Strategy--Lab-purple?logo=github)](https://github.com/imlast999/lastedge-strategy-lab)
[![App](https://img.shields.io/badge/GitHub-App-green?logo=github)](https://github.com/imlast999/lastedge-app)
[![Android APK](https://img.shields.io/badge/Download%20APK-v1.1.54-brightgreen?logo=android)](https://github.com/imlast999/lastedge-app/releases/download/v1.1.54/LastEdge-v1.1.54.apk)
[![Tests](https://img.shields.io/badge/Tests-201%2F201%20Passed-success)](https://github.com/imlast999/LastEdge)
[![Architecture](https://img.shields.io/badge/Architecture-Decoupled%20REST%20Microservices-orange)](https://github.com/imlast999/LastEdge)

</div>

---

## 🧭 Ecosystem Overview

**LastEdge** is structured as an ecosystem of **three independent, decoupled repositories**, each with its own continuous integration pipeline, automated tests, and dedicated documentation:

```text
                                 ┌──────────────────────────────────────────┐
                                 │               LastEdge App               │
                                 │          imlast999/lastedge-app          │
                                 │  • Web Dashboard Bento Grid (:8080)      │
                                 │  • Mobile App (React Native / Expo 54)   │
                                 │  • Discord & Telegram Bot Adapters       │
                                 └─────────────────────┬────────────────────┘
                                                       │
                                            HTTP REST Communication
                                                       │
                                 ┌─────────────────────┴────────────────────┐
                                 ▼                                          ▼
     ┌──────────────────────────────────────────┐   ┌──────────────────────────────────────────┐
     │         LastEdge Trading Engine          │   │          LastEdge Strategy Lab           │
     │    imlast999/lastedge-trading-engine     │   │      imlast999/lastedge-strategy-lab     │
     │  • MetaTrader 5 Execution Client & Reconnect │  • Historical Data Pipeline (Parquet)    │
     │  • Risk Engine v2 (Adaptive Sizing, Margin)  │  • Backtesting & Realistic Cost Slippage │
     │  • Circuit Breakers & Daily Drawdown Guards  │  • Walk Forward Analysis (WFA) Engine    │
     │  • Production REST API (:8081)               │  • Monte Carlo Risk-of-Ruin Engine       │
     │  • Trade Journal SQLite (bot_state.db)       │  • Deflated Sharpe & 6 Quantitative Gates│
     │  • Cryptographic Ingestion (SHA-256 Hash)    │  • Strategy Lab REST API (:8082)         │
     │  • Approved Production Strategies Vault      │  • Unified Research CLI (run_pipeline)   │
     └──────────────────────────────────────────┘   └──────────────────────────────────────────┘
```

---

## 📦 Repositories & Quick Access

The ecosystem consists of the following 3 standalone sub-repositories orchestrated by this master repository:

| Repository | GitHub Link | Role | Ports | Test Suite |
| :--- | :--- | :--- | :---: | :---: |
| ⚡ **LastEdge Trading Engine** | [**`imlast999/lastedge-trading-engine`**](https://github.com/imlast999/lastedge-trading-engine) | Execution core, MetaTrader 5 driver, Risk Engine v2, dynamic strategy loader, Circuit Breakers. | `:8081` | **108 / 108 PASSED** ✅ |
| 🧪 **LastEdge Strategy Lab** | [**`imlast999/lastedge-strategy-lab`**](https://github.com/imlast999/lastedge-strategy-lab) | Offline quantitative laboratory, WFA, 1,000 Monte Carlo runs, Deflated Sharpe, 6 quantitative gates. | `:8082` | **54 / 54 PASSED** ✅ |
| 📱 **LastEdge App** | [**`imlast999/lastedge-app`**](https://github.com/imlast999/lastedge-app) | Web Dashboard (:8080), React Native / Expo Android APK, Discord slash commands, and Telegram bot. | `:8080` | **39 / 39 PASSED** ✅ |

> **Overall Test Suite**: **201 / 201 automated unit & integration tests passing** across the monorepo.

---

## 🎯 Signal Confidence & Execution Matrix

Every trading signal emitted across the ecosystem (`EURUSD`, `XAUUSD`, `BTCEUR`) is evaluated against quantitative confluency factors (trend alignment, ATR volatility regime, RSI momentum, and setup strength):

| Tier | Confluence Score | Execution Mode | Pipeline Routing |
| :--- | :---: | :--- | :--- |
| **`VERY_HIGH`** | **`0.85 – 1.00`** | **Automated (Direct MT5)** | Order is executed immediately in MT5 with IOC filling. Broadcast as `AUTO-APROBADA ✅` to Discord, Telegram & Web Dashboard. |
| **`HIGH`** | **`0.67 – 0.84`** | **Automated (Direct MT5)** | Order is executed immediately in MT5 (optimized $\ge 0.67$ threshold). Captures high-conviction trades without manual delay. |
| **`MEDIUM`** | **`0.60 – 0.66`** | **Manual 1-Click Approval** | Stored in SQLite as `PROPOSED`. Sent to Web Dashboard & Mobile App for human oversight (filtered automatically when Autonomous Mode is ON). |
| **`LOW`** | **`< 0.60`** | **Automatic Rejection** | Discarded at pre-filter. Zero alert noise, preventing execution in choppy or sub-optimal market conditions. |

### 🤖 Dual-Mode Autonomous Operation (Hands-Free vs. Hybrid Review)

To eliminate emotional friction, psychological fatigue, and decision regret, LastEdge features an institutional **Autonomous Mode Switch** accessible via the Web Dashboard, Telegram Bot, and REST API:

* **🟢 100% Autonomous Mode (`ON` — Hands-Free)**: The system operates completely unattended. All `MEDIUM` signals ($0.60 - 0.66$) are automatically and silently filtered out, ensuring **only high-conviction trades ($\ge 0.67$)** execute directly into MT5 without requiring manual approvals or generating notification clutter.
* **🟡 Hybrid Mode (`OFF` — Discretionary Review)**: Enables the manual gate. `MEDIUM` signals are routed to the Web Dashboard and Telegram Bot with 1-click `[Approve]` / `[Reject]` actions for traders actively analyzing the market.
* **Full Persistence**: Toggle states are automatically saved to `rules_config.json` (`GLOBAL_SETTINGS.autonomous_mode`) and `autosignals_state.json`, surviving full VPS reboots.

---

## 📱 Mobile Native Client (Android APK)

The mobile client is built on **React Native (Expo SDK 54, Hermes Engine)**, designed to provide institutional oversight from any smartphone or tablet:

* 📥 **Direct APK Download**: [**`LastEdge-v1.1.54.apk`**](https://github.com/imlast999/lastedge-app/releases/download/v1.1.54/LastEdge-v1.1.54.apk)
* ⚡ **1-Tap MT5 Execution**: Pending signals generated by the scanner can be reviewed, accepted, or rejected directly from the phone.
* ⏳ **Reactive 1-Second Live Ticker**: Signal cards update their arrival timestamp (`HH:mm:ss`), relative elapsed time (`hace Xs / min`), and auto-expiration countdown in real time.
* 🛡️ **Session & Biometric Security**: Native Biometric Auth (Fingerprint / Face ID) and numeric PIN protection.
* 📊 **Broker Execution Quality**: Real-time monitoring of average latency (ms), fill rate (%), and broker slippage (pips).
* 🧪 **Strategy Lab Dual Sub-Navigation**:
  - `[ 🧪 Simulador de Tests ]`: Visual strategy selector in plain language, parameter depth toggles, visual score hero card (0-100), and the 6 quantitative pillars.
  - `[ 📚 Historial Guardado ]`: Real-time search and filter engine for past experiments with technical JSON inspect modals.


---

## 📈 Visual Chart Engine & Telegram Control Center

LastEdge App integrates an institutional-grade technical chart generator and interactive Telegram bot gateway:

* 🎨 **TradingView Dark Theme (`#090d16`)**: Native candlestick rendering powered by `mplfinance` with volume bars, EMA50 / EMA200 dynamic curves, and shaded Risk/Reward zone boxes.
* 📐 **Intelligent Dynamic Scaling**: Y-axis range automatically calculates Entry, Stop Loss, and Take Profit with +8% safety padding so targets are never off-screen.
* 🌐 **Bilingual Control Center**: Complete `/start` control matrix supporting real-time toggling between English (default) and Spanish with persistent preferences.
* ⌨️ **Slash Command Palette (`setMyCommands`)**: Instant autocomplete suggestions when typing `/` in Telegram registered with the Telegram Bot API in English and Spanish.
* 🔗 **Deep Linking & On-Demand Position Charts**: Direct bot triggers (`t.me/LastEdgeBot?start=chart_{ticket}`) and `/chart_{ticket}` commands for instant visual chart generation from open MT5 positions.
* 📊 **Web Dashboard Modal Integration**: Added `/api/positions/{ticket}/chart` endpoint and interactive `📊 Chart` modal viewer directly inside the Bento Grid positions table.

---

## 🧪 Strategy Lab 2.0: The 6 Quantitative Pillars Suite

Before any algorithmic strategy is allowed to trade real capital in the Trading Engine, it must pass the **6 Institutional Quantitative Pillars**:

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │                   THE 6 QUANTITATIVE PILLARS SUITE                     │
 ├────────────────────────────────┬───────────────────────────────────────┤
 │ 1. Monte Carlo (1,000 Runs)    │ Ruin Probability < 1.0% (DD 20% limit)│
 │ 2. Walk-Forward Analysis (WFA) │ Walk-Forward Efficiency (WFE) ≥ 60%   │
 │ 3. Overfitting & Deflated DSR  │ DSR ≥ 1.00 & p-value < 0.05           │
 │ 4. Mathematical Payoff         │ Profit Factor ≥ 1.30, Expectancy > 0  │
 │ 5. Market Regime Stress Test   │ Robustness in Bull, Bear, Chop & Vol  │
 │ 6. Cryptographic Graduation    │ Signed SHA-256 package promotion      │
 └────────────────────────────────┴───────────────────────────────────────┘
```

1. **Robustness & Monte Carlo (Pillar 1)**: Simulates 1,000 alternative futures by randomly reordering trade sequences to certify survival against streak volatility.
2. **Walk-Forward Analysis (Pillar 2)**: Rolling train/test windows across historical data to ensure the strategy learns persistent market inefficiencies instead of curve-fitting.
3. **Deflated Sharpe Ratio (Pillar 3)**: Applies the Bailey & López de Prado formula to discount selection bias and backtest trial counts.
4. **Payoff & Execution (Pillar 4)**: Mathematical edge per trade with strict Circuit Breaker thresholds (< 4 consecutive losses).
5. **Regime Stress Testing (Pillar 5)**: Evaluates performance across 4 distinct macroeconomic regimes (Bull, Bear, Chop / Lateral, Volatility Shock).
6. **Cryptographic Ingestion (Pillar 6)**: Approved strategies generate a signed `.json` sidecar with cryptographic checksums (`code_sha256` + `config_hash`). The Trading Engine rejects any strategy whose hash does not match.

---

## 💻 Web Dashboard: Bento Grid 2.0

* **Glassmorphism UI**: High-contrast financial palette with responsive Bento Grid architecture.
* **Real-Time Interactive Equity Curves**: Powered by Chart.js with dynamic time horizons (`1D`, `1W`, `1M`, `ALL`) and balance/equity tracking.
* **Educational Tooltips**: Interactive contextual guides explaining advanced quant metrics (Profit Factor, Sortino, Drawdown, Ruin Probability) in plain language.
* **Signal Audit Feed**: Live visual feed of incoming market signals with one-click manual approval.

---

## 🔐 Open-Core Framework vs. Private Strategy Model

LastEdge separates **software engineering** from **proprietary quantitative edge**:

* **Public / Open Source**:
  - The decoupled microservices architecture, IPC communication, and REST endpoints.
  - The MetaTrader 5 execution engine, order router, and risk calculation algorithms.
  - The complete 6 Pillars scientific laboratory, Monte Carlo simulator, and WFA framework.
  - The React Native mobile application, Bento Grid web dashboard, and CI/CD pipelines.
  - Baseline benchmark strategies (`BaseStrategy`, `eurusd_simple`).
* **Private / User-Owned (Never Committed)**:
  - Broker accounts, server names, and passwords (configured strictly via `.env`).
  - Private Telegram / Discord bot tokens.
  - **Proprietary Alpha Strategies**: Your personal, highly-optimized trading strategies reside safely in `strategies/private/` (enforced via `.gitignore`). The engine dynamically loads them without requiring code modification.

---

## 🚀 Quick Start & Workspace Synchronization

Clone this orchestrator repository to set up and manage the entire ecosystem with a single command:

### 1. Clone this orchestrator
```bash
git clone https://github.com/imlast999/LastEdge.git
cd LastEdge
```

### 2. Run the automated clone script
Execute `clone_repos.bat` (or `setup.bat`):
```cmd
.\clone_repos.bat
```
This automatically:
- Clones all three sub-repositories (`LastEdge Trading Engine`, `LastEdge Strategy Lab`, `LastEdge App`).
- Executes `git pull --ff-only` if repositories are already present.
- Generates initial configuration `.env` files from `.env.example` templates if missing.

### 3. Launch the unified CLI environment
```cmd
.\lastedge.bat
```
*(Or launch individual microservices in background using `pm2 start ecosystem.config.js`).*

---

## 📚 Technical Documentation Index

For exhaustive technical documentation, API specifications, and architectural diagrams, visit each sub-repository's docs:
- ⚡ [**Trading Engine Technical Documentation**](https://github.com/imlast999/lastedge-trading-engine/tree/main/docs)
- 🧪 [**Strategy Lab Research Documentation**](https://github.com/imlast999/lastedge-strategy-lab/tree/main/docs)
- 📱 [**App & Mobile Architecture Documentation**](https://github.com/imlast999/lastedge-app/tree/main/docs)

---

<div align="center">
<sub>Built with precision for quantitative systems traders and algorithmic portfolio managers.</sub>
</div>
