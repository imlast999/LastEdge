# 🗺️ LastEdge Ecosystem — Strategic Roadmap

Central evolution, development phases, and monetization roadmap for the **LastEdge** quantitative ecosystem.

> **Strategic direction (November 2026):** LastEdge is migrating to a **Linux-first, multi-platform architecture**. A single headless Linux server will host both execution stacks side by side: **MetaTrader 5** (headless under Wine) and **cTrader Open API** (native). The 60-day verified challenge is **paused** until both stacks pass stability testing, and will then launch on both platforms at the same time from the same frozen code.

**Team:** **Last** (founder, strategy and MT5 stack) · **co-dev** (infrastructure and cTrader stack).

---

## 📌 Phase Execution Overview

```
  [████████████████████] 100% — Phase 1: Infrastructure & MT5 Execution Engine
  [█████████████████░░░]  85% — Phase 2: Quantitative Laboratory & Six Pillars v2 (real suite built; Lab v2 live-parity in progress)  ← ACTIVE
  [████████████████████] 100% — Phase 3: Web Dashboard Bento Grid & Android Mobile App
  [████████████████████] 100% — Phase 4: Multi-Device Remote Access (being superseded by Phase 6)
  [██████████████████░░]  90% — Phase 5: Consolidation, Global i18n & Audited Track Record
  [███████████████░░░░░]  75% — Phase 6: Linux Migration & Dual-Platform Execution (MT5 + cTrader)  ← ACTIVE
  [░░░░░░░░░░░░░░░░░░░░]   0% — Phase 7: Dual 60-Day Verified Challenge ($10k MT5 + $10k cTrader) — blocked until a strategy passes Six Pillars v2
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
| Main prerequisite before scaling | A **verified edge**. The demo run (22/10–15/11: 60 trades, +$391.89, PF 2.02, +20.2R) was reproduced by a live-faithful backtest (PF 2.01), but the **same logic loses on the preceding months (PF 0.90, −5.7R)** → the demo was most likely a favourable stretch, not proof of edge (see Phase 2 · Lab v2). |

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
- [x] **Six Pillars v2 — real computation suite (Nov 2026 audit)**: the pillar metrics previously displayed in the App were static placeholders, and the legacy replay had a **lookahead in its circuit breaker** that inflated the README figures (reported DSR values > 1 are mathematically impossible). Rebuilt as an event-driven backtester mirroring live execution (spread, commission, slippage, partial close, breakeven, trailing, position overlap, round-down sizing) with every pillar computed for real (equity-based Monte Carlo ruin + prop-limit breach probability, walk-forward/WFE, Deflated Sharpe + PBO with trial counting, cost sensitivity, regime and out-of-period stress, SHA-256 hashed verdicts). The App shows only computed results or an explicit "not computed" state (`lab/docs/SIX_PILLARS.md`).
- [x] **First verdicts (5 challenge strategies, 10,000 H1 bars, UTC)**: **all REJECTED** — eurusd_flow PF 0.81, btceur_trend_surge PF 0.92, btceur_volatility_breakout PF 1.04, xauusd_partial PF 1.17 (85 trades), xauusd_asian_london PF 1.08. To be re-run under Lab v2 (below).
- [x] **Backtester verification**: blind code review, ablation study and **trade-by-trade reconciliation against the real demo** (56/60 trades matched, mostly to the minute; feeding the real entries through the backtester reproduces the exits: +20.4R vs +20.2R real) → the exit engine is validated.

### 🔬 Lab v2 — Live Parity & Honest Research (ACTIVE)
> **Goal**: the Lab and the live Engine must be the *same machine*, so a Lab verdict says exactly what live will do. No `reto-v1` until a strategy passes under these conditions.

**Root causes found for the Lab vs. live gap (demo period):** forming-bar evaluation every 60 s in live (+8.4R in that period, negative before it), Lab scoring gate ≠ Engine gate (Engine scoring changed 12/11; Lab had no ConfidenceSystem) (+7.1R), different cooldowns/limits (+3.5R), costs (+0.3R).

- [x] **One signal gate for both**: new pure module `engine/core/signal_gate.py` (scoring, ConfidenceSystem, thresholds, duplicate filter, per-symbol cooldown in minutes, 3 signals per direction/day, 1 position per symbol, weekend guard, auto-execute tier). The Engine delegates to it with **zero behaviour change** (4,000-case old-vs-new check); the Lab imports it instead of its own copies (parity tests: 250 candidate cases + 400 dispatch events, all identical).
- [x] Lab fixes: XAUUSD point 0.01 → **0.001** (spread was ×10), Lab-only `min_score` filter removed, Lab now reads the Engine's `rules_config.json`, best-candidate-per-symbol selection like live, full weekend rules.
- [⏳] **Closed-bar policy in live** (owner decision): evaluate only closed H1 bars, once per new bar, 1,000 bars for every symbol; configurable `signal_bar_policy` (`closed` default, `forming` legacy).
- [⏳] **Unified strategy config**: the Lab builds each strategy's config with the same merge as live (rules_config symbol block over strategy defaults).
- [⏳] Lab backtester mirrors the new Engine breakeven (R-only trigger, cost-covering buffer).
- [⏳] **Six Pillars re-run on all 16 strategies** (not only the 5 challenge ones) under Lab v2.
- [ ] **Exit policies inside the suite**: Exit Research variants (fixed RR, ATR/EMA/Donchian trailing, breakeven, partials, time exit) ported to the Six Pillars backtester as pluggable exit policies (R-based, real costs, Engine gate, position lock). Every policy tried counts as a trial in DSR/PBO. A policy that wins must also be implemented in the Engine. The standalone Exit Research runner stays as an exploration tool only (pip-based metrics, flat 1.5-pip cost, TP-first same-bar bias, no position lock, dropped open trades, best-of-N selection without trial counting).
- [ ] **New Pillar 6 — Edge Origin & Robustness** (the verdict becomes step 7): entries vs. random entries with the same exits and trade count; robustness to neighbouring exit parameters (plateau, not a spike); MFE capture (are exits wasting a good entry?).
- [ ] **Re-validate the 4 leads** with fresh walk-forward and trial counting: btceur_volatility_breakout with 3×ATR stop + 24-bar time exit (PF 1.43 / 1.22, positive every year), btceur_trend_surge with 48-bar exit, xauusd_asian_london entries (significant entry edge 2022–24 destroyed by its exits), xauusd_partial with the pre-12/11 scoring (PF 1.69 over 2 years, 247 trades).
- [ ] **New strategy research protocol** (`lab/docs/STRATEGY_RESEARCH_PROTOCOL.md`): written hypothesis first → fast **vectorbt screening** (trial budget fixed in advance, every screened combination counted) → Six Pillars v2 → locked final hold-out (last 6 months untouched until the verdict). `backtesting.py` used as an independent second opinion on 1–2 simple strategies.
- [ ] Define **`reto-v1`** only if at least one strategy passes; otherwise keep researching before any challenge.
- [x] **Historical data time-base audit**: Lab datasets mixed true UTC (≤2024-10) with broker time (UTC+2/+3 afterwards). UTC-converted datasets generated; the 5 challenge strategies re-validated on UTC (see Lab `docs/DATA_UTC_AUDIT.md`).

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
- [x] **Sandbox / incubation MT5 demo account** ($5,000 start): used as a zero-cost test bed while building and debugging LastEdge, including manual test trades. After testing it sat at ≈$2,700; it was then left **3 weeks fully autonomous** to see whether the bot could recover to $3,000 — it went beyond that (≈$3,100). Reconciled bot-only result 22/10–15/11: **60 trades, +$391.89, PF 2.02, +20.2R** (btceur_trend_surge +8.0R, eurusd_partial +8.2R, xauusd_partial +3.8R, btceur_partial +0.3R). The same logic loses on the preceding months (PF 0.90) → favourable stretch, not proof of edge → origin of the $10k / 2-month challenge and of Lab v2.
- [x] **Broker access incident (Nov 2026)**: after a weekend-long platform/dashboard migration by the demo broker, Google sign-in stopped working and previously created accounts no longer appeared under the same email. New-account creation and Myfxbook linking on that broker are therefore blocked.
- [x] **Alternative broker search** (requirements below) did not produce a suitable MT5 option yet.
- [⏸️] **60-Day $10k Verified Challenge** → **paused** and moved to **Phase 7** (dual-platform launch after the Linux migration).
- [🔧] **Maintenance mode (since 2026-11-16)**: all LastEdge services stopped on the Windows host; no trading on any server until the Linux cut-over.
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
- [x] **MetaTrader 5 installed under Wine 11** (Debian's Wine 10 fails with MT5's "debugger found" check — Wine bug fixed in 11.6) and Windows-side Python 3.12 (numpy 1.26).
- [x] RPyC bridge (localhost only) + drop-in `MetaTrader5` shim speaking RPyC directly (mt5linux 1.x client requires Docker), so the Engine runs **unchanged** on Linux.
- [x] **Cross-platform watchdog** (Wine process detection, supervised mode, Telegram alerts preserved).
- [x] **supervisord configuration** with ordered startup (display → terminal → bridge → engines → lab/app → watchdog) and helper scripts.
- [x] Unattended login via `/config` startup file (path without spaces; broker server list imported).
- [x] **End-to-end validation on the existing demo account**: login, account, symbols, live ticks, 300 H1 bars per symbol, positions and pandas frames from Linux. Broker offset measured: UTC+2. Algo Trading intentionally disabled during validation.
- [ ] Dedicated **$10k MT5 demo account** (broker meeting the Phase 7 requirements).
- [ ] Boot persistence hook (start `supervisord` on host container restart).
- [ ] 24–72 h stability soak test.

### Workstream B — cTrader Open API *(owner: co-dev)*
- [x] Platform research completed:
  - Recommended demo broker: **Pepperstone (EU entity)** — only broker found with **EURUSD + XAUUSD + BTCEUR** on cTrader. Note: EU crypto leverage is 1:2 (affects BTCEUR sizing). Fallback: IC Markets (London LD5) with synthetic BTCEUR (BTCUSD ÷ EURUSD).
  - Open API facts: demo/live endpoints (`*.ctraderapi.com:5035/5036`), 50 req/s general & 5 req/s historical limits, OAuth2 tokens (~30 days, refresh token rotation).
- [x] **Full cTrader connector (offline-tested)**: own asyncio client (no Twisted) over TLS with vendored official protobuf messages; application/account auth, symbols, spot subscriptions, trendbars, market orders with SL/TP, amend, partial close, reconcile, deal history; heartbeat, auto-reconnect with re-auth/re-subscribe, rate limiting (45/4 req/s), OAuth token refresh with rotation persisted atomically; demo by default (live requires two explicit flags); onboarding CLI `scripts/ctrader_oauth.py`; fake cTrader server test harness (`docs/CTRADER_CONNECTOR.md`).
- [ ] Register LastEdge application at `openapi.ctrader.com` (approval time not published — start early).
- [ ] Open **$10k cTrader demo account** and verify BTCEUR availability via `ProtoOASymbolsListReq`.
- [ ] First real demo session: read-only check, then a 0.01-lot cycle; verify the 10 open points listed in the connector docs.
- [ ] 24–72 h stability soak test.

### Workstream C — Shared Core *(both)*
- [x] **Broker abstraction layer (`core/broker/`)**: `BrokerAdapter` base with neutral data models, unified order path, symbol-precision rounding, `NO_CHANGE` short-circuit; `Mt5Adapter`, deterministic `SimBroker` (Parquet replay, intrabar SL/TP, partial closes, commissions, slippage) and factory `BROKER_BACKEND = mt5 | sim | ctrader`. **+92 tests.**
- [x] Broker usage inventory and step-by-step migration plan (`docs/broker_adapter_inventory.md`, `docs/broker_adapter_migration.md`).
- [x] **All 22 Engine modules migrated** from direct `MetaTrader5` calls to the adapter; a guard test forbids `MetaTrader5` imports outside `core/broker/`.
- [x] **Portfolio risk fail-closed** (owner decision): if the broker cannot report open positions, new trades are rejected (exposure unknown).
- [x] **12-factor instances**: one code folder, two stacks differing only by environment (`BROKER_BACKEND`, `LASTEDGE_DATA_DIR`, ports); per-stack state (DB, logs, backups, caches); runtime config overrides written to the data dir, never to the shipped `rules_config.json`.
- [x] **Native UTC**: dynamic broker offset (`BrokerClock`: measured from fresh ticks, BTCEUR on weekends, periodic re-measure with change confirmation, persisted fallback); strategies receive true UTC bars (`STRATEGY_BAR_TIME=utc`, legacy `broker` mode kept as fallback).
- [x] **Round-down position sizing** (Decimal) — trades below the broker minimum are skipped, never bumped up; partial closes round down too.
- [x] `python-dotenv` and pinned bridge dependencies added to requirements.
- [ ] Off-site encrypted backups and structured (JSON) logs.
- [ ] Dashboard support for two engine stacks.
- [ ] Freeze strategy/config release **`reto-v1`** (git tag) used by both stacks — only after a strategy passes Six Pillars v2 under Lab v2.
- [ ] Mobile app: remove remaining fabricated pillar numbers (`DEMO_PILLARS_ANALYSIS`, Lab screen defaults) and stop reporting an offline promotion as success.

### 🛡️ Security Hardening *(prerequisite for cut-over)*
- [x] Control plane hardening implemented on `linux-support` (App + Engine API): localhost-only binding by default, real session authentication with expiring random tokens and login rate limiting, authentication enforced on all API routes, restricted CORS, request size limits, internal service token between App and Engine, input path validation.
- [x] Equivalent hardening applied to the Strategy Lab API (internal token, localhost binding, CORS allow-list, input validation, resource limits on research jobs).
- [x] Public SSH relay tunnel retired on the Windows host; private mesh access only.
- [ ] Rotate operational secrets at cut-over.
- [ ] Mobile app: send session token, remove offline PIN fallback, handle 401/429/503.

### 🔧 Execution Correctness Fixes *(found during migration audit)*
- [x] **Trailing-stop ratchet loop**: persisted SL with excess decimals vs. broker-rounded SL triggered endless modify requests → fixed (symbol-digit rounding + half-point tolerance) with regression test.
- [x] Portable pytest temp directory (Windows/Linux).
- [x] Trailing minimum stop distance now reads `trade_stops_level` (with fallback).
- [x] Filling mode follows the symbol (IOC → FOK → RETURN) with one retry on unsupported filling.
- [x] SL/TP rounded to symbol digits before sending.
- [x] Lot size rounded **down** (owner decision) — never exceeds the sized risk.
- [x] Broker server time converted to UTC at the boundary (owner decision).
- [x] MT5 `None` responses no longer treated as "no positions" during micro-disconnects.
- [x] Candle fetch only reconnects when the terminal is disconnected.
- [x] `rules_config.json` aligned with the 5-strategy challenge portfolio (eurusd_flow, btceur_trend_surge, btceur_volatility_breakout, xauusd_partial, xauusd_asian_london) and its risk/score settings.
- [x] `xauusd_asian_london` session windows re-expressed in UTC (Asia 00–04, London 05–10) after UTC re-validation.
- [x] **UTC is the default** for strategy bars (`STRATEGY_BAR_TIME=utc`) on both MT5 and cTrader adapters.
- [x] **Breakeven fixed**: it fired at ≈0.53–0.8R (min of R and TP-% thresholds) with a spread-only buffer, so breakeven exits lost money after costs. Now R-only trigger (0.8R; TP-% only without SL) and buffer = spread + round-turn commission + slippage, tick-rounded in the trade's favour; waits instead of pulling the stop back when inside `trade_stops_level`.
- [x] **Trailing config bug**: trailing read a non-existent top-level key and always used hard-coded values; now reads `GLOBAL_SETTINGS.trailing_stops` (per-symbol overrides supported).
- [x] **Trade journal records closes** (previously everything stayed `PENDING`): exit price, UTC time, net P&L with commission/swap, R, exit reason (TP/SL/BE/TRAIL/MANUAL/WEEKEND/STOP_OUT), partial closes; 90-day backfill on first run.
- [x] **Clock-skew guard**: host clock vs. broker tick time (the Windows host ran 1 h behind from 28/10 to 14/11); warning > 30 s, new entries blocked > 5 min, shown in health status. Note: an exact 1 h error is only detectable once `expected_broker_utc_offset_hours` is set.
- [ ] Trailing start still uses min(R, TP-%) thresholds — review together with exit policies.
- [ ] cTrader: trailing registration probably uses the order id instead of the position id — fix before trading on cTrader.
- [ ] Mobile store can close journal rows by price match without exit reason — unify with the journal sync.

### ✅ Test Status (linux-support)
| Repository | Result |
| :--- | :---: |
| Trading Engine (broker layer, cTrader connector, UTC clock, signal gate, breakeven/journal/clock fixes) | **470 / 470** ✅ |
| LastEdge App (incl. security hardening, no fabricated pillar numbers) | **71 / 71** ✅ |
| Strategy Lab (incl. security hardening, UTC audit, Six Pillars v2, Engine-gate parity) | **111 / 111** ✅ |

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
