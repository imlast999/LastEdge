# 🗺️ LastEdge Ecosystem — Strategic Roadmap

Central evolution, development phases, and monetization roadmap for the **LastEdge** quantitative ecosystem.

> **Strategic direction (November 2026):** LastEdge is migrating to a **Linux-first, multi-platform architecture**. A single headless Linux server will host both execution stacks side by side: **MetaTrader 5** (headless under Wine) and **cTrader Open API** (native). The 60-day verified challenge is **paused** until both stacks pass stability testing, and will then launch on both platforms at the same time from the same frozen code.

**Team:** **Last** (founder, strategy and MT5 stack) · **co-dev** (infrastructure and cTrader stack).

---

## 📌 Phase Execution Overview

```
  [████████████████████] 100% — Phase 1: Infrastructure & MT5 Execution Engine
  [████████████████████] 100% — Phase 2: Quantitative Laboratory & 6 Pillars Suite
  [████████████████████] 100% — Phase 3: Web Dashboard Bento Grid & Android Mobile App
  [████████████████████] 100% — Phase 4: Multi-Device Remote Access (being superseded by Phase 6)
  [██████████████████░░]  90% — Phase 5: Consolidation, Global i18n & Audited Track Record
  [███████░░░░░░░░░░░░░]  35% — Phase 6: Linux Migration & Dual-Platform Execution (MT5 + cTrader)  ← ACTIVE
  [░░░░░░░░░░░░░░░░░░░░]   0% — Phase 7: Dual 60-Day Verified Challenge ($10k MT5 + $10k cTrader)
  [██████████░░░░░░░░░░]  50% — Phase 8: Monetization Route 1 (Recurring VIP Signals & Community)
  [░░░░░░░░░░░░░░░░░░░░]   0% — Phase 9: Monetization Route 2 (Prop Firm Funded Accounts)
```

---

## 🧭 Why Linux (Cold Assessment)

| Question | Conclusion |
| :--- | :--- |
| Does Linux improve strategy returns? | **No.** Edge depends on strategies and broker execution, not on the OS. |
| Does Linux allow more trades? | **No.** Trade count is bounded by risk rules (max 3 open positions, 2.5% total risk, daily direction caps), not by hardware. |
| What does Linux unlock? | **Scale and platform independence**: many accounts in parallel on cheap hardware; access to prop firms on cTrader, DXtrade, Match-Trader and TradeLocker (reduced dependency on MetaQuotes after its 2024 prop-firm license cut-off); copy-trading / SaaS at near-zero cost per client. |
| Is MT5 a bad platform? | **No.** It is the industry standard and fully adequate for one or two accounts. It becomes the bottleneck only for multi-account, multi-client scaling (one terminal per account, Windows-bound Python API). |
| Main prerequisite before scaling | A **verified edge**: current evidence (≈4 weeks of bot trading on demo, profit factor ≈3.0 on ~45 closing deals) is promising but statistically insufficient. |

**Decision:** keep MT5 (headless on Linux) **and** add cTrader Open API, both behind a common broker abstraction, so strategies and risk logic stay identical across platforms.

---

## ✅ Completed Phases (Engineering & Infrastructure)

### Phase 1: Execution Core & Risk Engine v2 (`Trading Engine`)
- [x] Native MetaTrader 5 bridge client (`MetaTrader5` Python API).
- [x] **Risk Engine v2**: Adaptive position sizing, margin surveillance, and portfolio risk capping.
- [x] Automated **Circuit Breakers**: Execution halt on loss streaks or maximum daily drawdown.
- [x] Dynamic Trailing Stops and multi-stage partial take-profit automation in MT5.
- [x] High-integrity SQLite trade journal and persistent state store (`bot_state.db`).
- [x] **Weekend Exposure Guard**: Automated Friday position liquidation with per-strategy switch (`weekend_exposure_guard: bool`).
- [x] **FXLiveCapital 10% Margin Cap**: Hard broker protection preventing account blowout on floating margin spikes.
- [x] **117 / 117 unit and integration tests passed (100% Green).**

### Phase 2: Scientific Audit & Strategy Lab 2.0 (`Strategy Lab`)
- [x] High-fidelity historical data pipeline in Parquet and CSV.
- [x] Market Replay simulator with realistic dynamic spreads and slippage modeling.
- [x] **Suite of the 6 Quantitative Pillars**:
  1. *Monte Carlo (1,000 permutations)*: Risk of ruin < 1.0% under adverse sequence shuffles.
  2. *Walk-Forward Analysis (WFA)*: WFE efficiency ≥ 60% across rolling out-of-sample windows.
  3. *Overfitting & Data-Snooping Guard*: Deflated Sharpe Ratio (DSR) mathematical validation.
  4. *Mathematical Payoff*: Profit Factor ≥ 1.30 with robust clearance over broker commissions.
  5. *Macro Regime Stress Testing*: Multi-scenario performance in Bull, Bear, Chop, and Volatility Shocks.
  6. *Institutional Verdict & Graduation*: Cryptographic SHA-256 package verification.
- [x] Dynamic strategy loader auto-discovering strategies from `strategies/`, `vault/`, `private/`, and `public/`.
- [x] Research runner and backtest validation engine for proprietary alpha models.
- [x] **54 / 54 unit and mathematical tests passed (100% Green).**

### Phase 3: Monitoring & Mobile Control Plane (`LastEdge App`)
- [x] Modern Bento Grid 2.0 Glassmorphism Web Dashboard on port `8080`.
- [x] Real-time equity and balance tracking charts powered by Chart.js & Lightweight Charts.
- [x] **Production Mobile Client (React Native Expo 54 / Hermes)**:
  - 1-second live countdown tickers on pending signals (`HH:mm:ss`).
  - 1-tap MT5 signal approval, rejection, and price drift safeguards.
  - Live broker execution telemetry (latency, slippage, fill rate).
  - Biometric authentication (Fingerprint / FaceID) and security PIN protection.
  - Mobile Strategy Lab featuring dual subtabs: `[Simulator]` & `[History]`.
  - Typography System: Nexa (Titles & Display) + Plus Jakarta Sans (Fintech Metrics & Body).
- [x] **Granular Mobile Notification Center (15 Alert Types & 5 Android Channels)**:
  - ⚡ *Señales & Ejecución*: 1.1 Señal Discrecional (TTL 10m), 1.2 Señal Auto-Ejecutada (Tier HIGH/VERY_HIGH $\ge 0.67$), 1.3 Alerta de Señal Expirada.
  - 📊 *Órdenes & Beneficios*: 2.1 Break-Even Asegurado (Riesgo Cero), 2.2 Take Profit Parcial (50% volumen), 2.3 Cierre en Ganancia (TP), 2.4 Cierre en Stop Loss.
  - 🛡️ *Salvaguardas de Riesgo*: 3.1 Aviso Previo Weekend Guard (viernes tarde), 3.2 Liquidación Weekend Guard (21:45 UTC), 3.4 Circuit Breaker Activado.
  - 🔬 *Strategy Lab*: 4.2 Fin de Backtest / Optimización Monte Carlo en Lab.
  - 🔌 *Broker & Conectividad*: 5.1 Desconexión / Reconexión MT5 y VPS, 5.2 Alerta de Spread Anormal (>4.0 pips).
  - 📱 *Rutina & Mantenimiento*: 6.1 Resumen Diario de Sesión (22:00 UTC), 6.2 Nueva Versión de App APK (1-tap update).
  - Configuración granular e independiente con toggles agrupados por categoría e i18n bilingüe (ES / EN).
- [x] Automated GitHub Actions CI/CD pipeline compiling signed release APKs (`v1.1.94`).
- [x] **Google Play Store Deployment & Protection**:
  - Private `.aab` compilation workflow (`.github/workflows/build-playstore-bundle.yml`) with manual `workflow_dispatch` trigger and 7-day private artifact retention, completely isolating `.aab` bundles from public releases.
  - Local bundle tooling via `build_bundle.bat` and `build_apk.py --bundle`.
  - Production graphic creatives: 512x512 PNG app icon (32-bit RGBA) & 1024x500 PNG feature graphic (24-bit RGB).
  - Responsive dark-mode Privacy Policy (`docs/privacy.html` & `PRIVACY_POLICY.md`) with in-app settings link.
  - Direct founder contact strategy (`@imlast999`) complying with Google Play in-app billing rules.
- [x] **Mobile Community Hub & Direct VIP Channel Access**:
  - Bento card in Home Dashboard (`COMUNIDAD & SEÑALES VIP` / `COMMUNITY & VIP SIGNALS`) with 3 direct links: Public Telegram Journal, Instagram broadcast, and featured VIP access button linking directly to `@imlast999`.
  - Dedicated Community section in Settings modal with 100% bilingual reactivity (ES / EN).
- [x] **Ecosystem Onboarding Wizard & Modular Architecture**:
  - First-run setup modal in Web & Mobile prompting active components (`Trading Engine`, `Strategy Lab`).
  - Minimum 1 selection invariant (prohibits 0-selection state).
  - Cross-version persistence via `AsyncStorage` (`@lastedge_ecosystem_modules_v1`) and `localStorage`.
  - Adaptive UI: auto-hiding inactive tabs and suppressing false offline alerts.
- [x] **50 / 50 control plane, chart engine, and telegram adapter tests passed (100% Green).**

### Phase 4: Remote Station & Multi-Device Accessibility *(being superseded by Phase 6)*
- [x] ~~Continuous 24/7 PM2 public tunnel for remote access~~ → **Deprecated.** Public relay tunnels are being retired in favor of private-network-only access (see Phase 6 · Security).
- [x] Zero-trust encrypted point-to-point mesh via Tailscale VPN (kept as the **only** remote access path going forward).
- [x] Mobile SSH terminal integration (ConnectBot) supporting physical keyboards on tablets/phones.
- [x] Strict `.gitignore` repository boundary isolating proprietary algorithms from public code.
- [x] **24/7 Permanent Antigravity Daemon**: Registered native Windows scheduled task (`\AntigravityCliDaemon`) enabling zero-terminal browser access without requiring an open SSH connection.

---

## 🔄 Phase 5: Consolidation, Global i18n & Audited Track Record (In Progress)
> **Goal**: Achieve total internationalization, bulletproof operational resilience, and an undeniable verified track record before commercial launch.

### 🌐 Global Internationalization (i18n & English Standardization)
- [x] **All Repository READMEs**: 100% standardized in English across the 4 repositories.
- [x] **Public Benchmark Strategies**: Documentation and code standardized in English (`strategies/public/README.md`).
- [x] **Web Dashboard**: 100% English default UI (Bento Positions, Overview, Trade Journal, and Research audit tools).
- [x] **Mobile App Localization** (English default, ES/EN toggle, all screens and widgets localized).
- [ ] **Core Engine Logs & Errors**: Complete migration of runtime log strings and API errors to standard English.
- [x] **Account Milestone ($2,800 USD Cash Balance Broken)**: Net realized overnight profit of +$32.23 USD and +$48.67 USD total equity expansion under 100% autonomous hands-free execution.

### 📱 Visual Telegram & Discord Control Center
- [x] **Technical Chart Generation Engine**: Dark-mode (`#090d16`) `mplfinance` generator with candlestick volume, EMA50 / EMA200 overlays, and dynamic Risk/Reward zone boxes.
- [x] **Unobstructed Live Candle Visibility**, **Intelligent Break-Even Badge Alignment**, **Dual Chart Modality** (on-demand vs. new-signal projection), **Intelligent Y-Axis Headroom** and **80-Candle H1 Context**.
- [x] **Bilingual Interactive Control Center** (`/start`), **Deep Linking** (`/chart_{ticket}`), **Native Slash Command Autocomplete** (EN/ES).
- [x] **Web Dashboard Modal Integration**: `/api/positions/{ticket}/chart` endpoint and visual chart viewer in the positions table.
- [x] **Independent Bot Switches**: `ACTIVATE_DISCORD_BOT=on|off`, `ACTIVATE_TELEGRAM_BOT=on|off`.

### 🎯 Signal Scoring & Auto-Execution Matrix
- [x] **Unified 4-Tier Confluence Matrix**:
  - `VERY_HIGH` (Score $\ge 0.85$): Auto-execution.
  - `HIGH` (Score $0.67 - 0.84$): Auto-execution (optimized threshold $\ge 0.67$).
  - `MEDIUM` (Score $0.60 - 0.66$): Discretionary 1-click approval (Hybrid Mode only).
  - `LOW` (Score $< 0.60$): Discarded.
- [x] **Dual-Mode Autonomous Operation Switch (100% Hands-Free vs. Hybrid Gate)** across Dashboard, Telegram (`/autonomous`, `/modo`…) and REST API, persisted in `rules_config.json` and `autosignals_state.json`.
- [x] **Cross-Repository Parity**: Synchronized configuration across `rules_config.json`, `engine.py`, `scoring.py`, and ecosystem documentation.

### 🤖 Institutional CI/CD & Automated Ecosystem Pipelines
- [x] **Ecosystem Orchestrator CI (`imlast999/LastEdge`)**.
- [x] **Semantic Release Notes & Changelog Drafter (`LastEdge App`)**.
- [x] **Dynamic Version Sync & README Direct Download**.
- [x] **Multi-Channel CI/CD Broadcast (Telegram + Discord)** (`scripts/notify_bots.py`).
- [x] **Private Strategy Vault CI (`LastEdge-Private-Strategies`)**: contract compliance and risk-bound checks (52 automated checks).
- [x] **Strict Pre-Push Git Hooks** enforcing 100% test pass rate.

### 🛡️ VPS Resilience & Hardening (Windows era)
- [x] **MT5 Disconnect Watchdog** with Telegram alerts and auto-restart (PM2).
- [x] **Automated Database Backups** (daily, 14-day rolling retention).
- [x] **OS Reboot Persistence** (PM2 dump).
- [ ] → All three are being re-implemented for Linux in Phase 6 (supervisord, off-site backups).

### 📈 Verified Forward Testing & Track Record
- [x] **Sandbox / incubation MT5 demo account** ($5,000 start): used as a zero-cost test bed while building and debugging LastEdge, including manual test trades. After testing it sat at ≈$2,700; it was then left **3 weeks fully autonomous** to see whether the bot could recover to $3,000 — it went beyond that (≈$3,100). Bot-only results since 2026-10-20 ≈ +$329 net over ~45 closing deals (PF ≈ 3.0). **Positive signal, but not enough evidence to justify a prop firm evaluation** → origin of the $10k / 2-month challenge.
- [x] **Broker access incident (Nov 2026)**: after a weekend-long platform/dashboard migration by the demo broker, Google sign-in stopped working and previously created accounts no longer appeared under the same email. New-account creation and Myfxbook linking on that broker are therefore blocked.
- [x] **Alternative broker search** (requirements below) did not produce a suitable MT5 option yet.
- [⏸️] **60-Day $10k Verified Challenge** → **paused** and moved to **Phase 7** (dual-platform launch after the Linux migration).
- [ ] **Gold (XAUUSD) Stop-Loss Multiplier Calibration**: evaluate ATR multiplier $1.5\times \rightarrow 2.0\times$ or dynamic volatility padding.
- [x] **Vault Strategy Graduation & Audit**: 10,000-candle multi-pillar audit; consolidated 5-strategy challenge portfolio.

---

## 🐧 Phase 6: Linux Migration & Dual-Platform Execution (ACTIVE)
> **Goal**: Run the entire ecosystem on a single headless Linux server with two execution stacks — **MT5 (headless, Wine)** and **cTrader Open API (native)** — sharing the same strategies, risk engine, and journal. Work happens on the `linux-support` branches; production stays untouched until cut-over.

### 🖥️ Target Infrastructure
- **Server**: dedicated headless Linux environment — **Debian 13 (trixie)**, x86_64, 4 vCPU / 8 GB RAM, persistent data volume. *(Minimum viable: 2 vCPU / 4 GB + swap.)*
- **Access**: private mesh only (Tailscale), SSH key authentication, no public ports.
- **Process management**: `supervisord` (the host environment does not allow nested containers, so Docker/Podman are not used; isolation is provided by the host container itself).
- **Python**: 3.12 pinned (matching CI), dependencies managed with `uv`.

```
Debian 13 (headless, SSH via private mesh only)
└── supervisord
    ├── xvfb            → virtual display :99
    ├── mt5-terminal    → MT5 under Wine (auto-login via /config ini, Algo Trading enabled at start)
    ├── mt5-bridge      → mt5linux RPyC bridge (localhost only)
    ├── engine-mt5      → Trading Engine · MT5 backend
    ├── engine-ctrader  → Trading Engine · cTrader Open API backend
    ├── lab             → Strategy Lab API
    ├── app             → Dashboard + Telegram/Discord bots
    └── watchdog        → health monitoring & alerts
```

### Workstream A — MT5 Headless on Linux *(owner: Last)*
- [x] Linux server provisioned and verified (Debian 13, 4 vCPU / 8 GB, x86_64).
- [x] Python 3.12 environment; Engine, Lab and App deployed (secrets excluded) — **test suites green on Linux**.
- [x] Wine 10 prefix with **MetaTrader 5 installed** and Windows-side Python 3.12.
- [x] `mt5linux` bridge installed on both sides; drop-in `MetaTrader5` shim so the Engine runs **unchanged** on Linux.
- [x] **Cross-platform watchdog** (Wine process detection, supervised mode, Telegram alerts preserved).
- [x] **supervisord configuration** with ordered startup (display → terminal → bridge → engine) and helper scripts.
- [x] MT5 startup config template (`mt5.ini`) for unattended login with Algo Trading enabled.
- [⏳] End-to-end bridge validation (terminal + bridge + Engine connectivity).
- [ ] Dedicated **$10k MT5 demo account** (broker meeting the Phase 7 requirements) and unattended auto-login. Until then, stack validation can use a disposable demo account.
- [ ] Boot persistence hook (start `supervisord` on host container restart).
- [ ] 24–72 h stability soak test.

### Workstream B — cTrader Open API *(owner: co-dev)*
- [x] Platform research completed:
  - Recommended demo broker: **Pepperstone (EU entity)** — only broker found with **EURUSD + XAUUSD + BTCEUR** on cTrader. Note: EU crypto leverage is 1:2 (affects BTCEUR sizing). Fallback: IC Markets (London LD5) with synthetic BTCEUR (BTCUSD ÷ EURUSD).
  - Open API facts: demo/live endpoints (`*.ctraderapi.com:5035/5036`), 50 req/s general & 5 req/s historical limits, OAuth2 tokens (~30 days, refresh token rotation).
- [x] `CTraderAdapter` skeleton with Open API message mapping (verified against official docs) and tested price/volume conversion helpers.
- [ ] Register LastEdge application at `openapi.ctrader.com` (approval time not published — start early).
- [ ] Open **$10k cTrader demo account** and verify BTCEUR availability via `ProtoOASymbolsListReq`.
- [ ] Choose client: official `ctrader-open-api` (Twisted, stable but slow-moving) vs. community `ctrader-api-client` (asyncio, early-stage).
- [ ] Full adapter implementation: auth, spot subscriptions, trendbars, orders, SL/TP amend, partial close, reconcile, heartbeat, token refresh, reconnection.
- [ ] 24–72 h stability soak test.

### Workstream C — Shared Core *(both)*
- [x] **Broker abstraction layer (`core/broker/`)**: `BrokerAdapter` base with neutral data models, unified order path, symbol-precision rounding, `NO_CHANGE` short-circuit; `Mt5Adapter`, deterministic `SimBroker` (Parquet replay, intrabar SL/TP, partial closes, commissions, slippage) and factory `BROKER_BACKEND = mt5 | sim | ctrader`. **+92 tests.**
- [x] Broker usage inventory and step-by-step migration plan (`docs/broker_adapter_inventory.md`, `docs/broker_adapter_migration.md`).
- [ ] Migrate the 22 Engine modules from direct `MetaTrader5` calls to the adapter (risk modules first, trailing stops coordinated last).
- [ ] Portable paths and configuration (`pathlib`, env-based), lockfile, `python-dotenv` added to requirements.
- [ ] Off-site encrypted backups and structured (JSON) logs.
- [ ] Freeze strategy/config release **`reto-v1`** (git tag) used by both stacks.

### 🛡️ Security Hardening *(prerequisite for cut-over)*
- [x] Control plane hardening implemented on `linux-support` (App + Engine API): localhost-only binding by default, real session authentication with expiring random tokens and login rate limiting, authentication enforced on all API routes, restricted CORS, request size limits, internal service token between App and Engine, input path validation. **App 61/61 tests green.**
- [ ] Apply equivalent hardening to the Strategy Lab API.
- [ ] Retire all public relay tunnels; private mesh access only.
- [ ] Rotate operational secrets at cut-over.
- [ ] Mobile app: send session token, remove offline PIN fallback, handle 401/429/503.

### 🔧 Execution Correctness Fixes *(found during migration audit)*
- [x] **Trailing-stop ratchet loop**: persisted SL with excess decimals vs. broker-rounded SL triggered endless modify requests → fixed (symbol-digit rounding + half-point tolerance) with regression test.
- [x] Portable pytest temp directory (Windows/Linux).
- [ ] Trailing minimum stop distance reads the wrong symbol field (`stops_level` vs `trade_stops_level`).
- [ ] Hard-coded IOC filling in 5 modules (must follow symbol filling mode for broker portability).
- [ ] SL/TP sent unrounded in order execution.
- [ ] Lot size rounded to nearest instead of **down** (can exceed sized risk).
- [ ] MT5 server time treated as UTC (impacts session-based strategies such as Asian/London windows).
- [ ] MT5 `None` responses treated as "no positions" during micro-disconnects.
- [ ] Candle fetch reconnects to MT5 on every call.
- [ ] Align `rules_config.json` active strategies with the frozen 5-strategy challenge portfolio.

### ✅ Test Status (linux-support)
| Repository | Result |
| :--- | :---: |
| Trading Engine (incl. broker layer & Linux watchdog) | **231 / 231** ✅ |
| LastEdge App (incl. security hardening) | **61 / 61** ✅ |
| Strategy Lab | **56 / 56** ✅ |

---

## 🏁 Phase 7: Dual 60-Day Verified Challenge
> **Model**: Two **$10,000 demo** accounts, **same frozen code (`reto-v1`)**, same symbols (EURUSD, XAUUSD, BTCEUR), same risk rules, **zero manual intervention for 60 days**, launched simultaneously once both stacks pass the soak test.

- [ ] **Stack A — MT5** (headless Linux) · **Stack B — cTrader Open API** (Linux native).
- [ ] **Challenge broker requirements** (both stacks):
  - Free demo account with configurable **$10,000** balance and no expiry during the 60 days.
  - **No KYC** required for demo accounts.
  - **Crypto CFDs** — ideally **BTCEUR** (fallback: BTCUSD with synthetic BTCEUR = BTCUSD ÷ EURUSD).
  - **Investor (read-only) password** available / changeable, or native platform support, so the account can be linked to **Myfxbook / FXBlue** and shared publicly.
  - Stable account management (no loss of access after platform migrations).
  - Candidates: cTrader → Pepperstone (EU) demo; MT5 → still open (re-evaluate once Stack A is ready).
- [ ] Third-party verification on **Myfxbook / FXBlue** for both accounts.
- [ ] Trade-by-trade comparison during the overlapping window (same signals, different execution).
- [ ] **Go / No-Go criteria at day 60**:
  - Profit Factor ≥ **1.30**
  - Max drawdown < **6%**
  - ≥ **60–80** trades
  - Positive result in **both** months
  - → **Go**: proceed to Phase 9 (funded accounts) on Linux infrastructure.
  - → **No-Go**: return to Strategy Lab before any capital or infrastructure spend.

---

## 🚀 Future Milestones: Monetization & Capital Scaling

### 🎯 Phase 8: Monetization Route 1 — Recurring VIP Signals Channel & Community (Active)
> **Model**: Real-time algorithmic signal broadcast generated by the Trading Engine scanner to private VIP subscribers, **without exposing proprietary code, weights, or model architectures**.

- [x] **Private VIP Signals Channel Infrastructure** (dual broadcast to operator chat and VIP channel).
- [x] **Unauthorized Visitor Landing on Bot** with links to the Public Trading Journal and founder contact (`@imlast999`).
- [x] **Rich Visual Trading Alerts** with technical charts.
- [x] **Public Transparency & Audit Channels**: [`t.me/LastEdgeJournal`](https://t.me/LastEdgeJournal), Instagram broadcast channel.
- [ ] **Automated Subscription Billing & Stripe Integration**.
- [ ] Launch only after a **verified** track record (Phase 7); review local regulatory requirements for selling signals.

---

### 🏆 Phase 9: Monetization Route 2 — Prop Firm Funded Accounts ($200,000+ Allocation)
> **Model**: Scale managed capital through prop firm evaluations and retain 80–90% of profits **with zero clients and zero personal capital risk**. Linux + broker abstraction enables **multiple funded accounts in parallel** across MT5 and cTrader.

- [ ] **Prop firm shortlist (cTrader-compatible, automation allowed)**: **FTMO** (clearest algorithmic policy), **The5ers**, **E8 Markets**. Written confirmation required that an external Open API bot is permitted.
  - Excluded: FundedNext (prohibits automated trading on cTrader), Maven (EAs prohibited / pre-approval only).
- [ ] **Request budget compliance**: FTMO caps server requests (≈2,000/day) — audit trailing-stop polling (15 s cadence) and order modification frequency before any evaluation.
- [ ] **Specialized Prop Firm Risk Profiles**:
  - Maximum daily loss capped at 3.5% (buffer below the 5% firm limit).
  - Maximum total drawdown capped at 8.0% (buffer below the 10% firm limit).
  - Automatic weekend position squaring via *Weekend Exposure Guard*.
- [ ] **Evaluation Challenge Execution** on validated vault strategies; verify slippage and spread behavior on firm servers.
- [ ] **Capital Allocation & Scaling**: pass Phase 1/2 evaluations, systematic profit withdrawals, then multi-account scaling on Linux.
- [ ] **Broker due diligence before any live capital**: prefer strongly regulated brokers/firms; the current MT5 demo broker should be re-evaluated for live use.

---

<div align="center">
<sub>LastEdge — Precision Quantitative Architecture & Financial Engineering.</sub>
</div>
