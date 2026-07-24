# 🚀 LastEdge Roadmap

> Living document that defines the long-term evolution of the LastEdge ecosystem.

---

# Philosophy

LastEdge is not built around adding features as quickly as possible.

Every improvement must satisfy three conditions:
- Make the platform more reliable
- Make future development easier
- Increase the quality of research or execution

If a feature does not improve one of these areas, it should not be implemented.

---

# Current Project Status (v1.1 LastEdge)

Current maturity:

🟢 **MT5 Execution Engine** ......... Stable (Async watchdog & auto-reconnect)

🟢 **Strategy Framework** .......... Stable (`eurusd_partial`, `xauusd_partial`, `btceur_partial`)

🟢 **Risk Engine v2** .............. Stable (`core/risk/` PositionSizer, MarginChecker, PortfolioRisk)

🟢 **Circuit Breaker** ............. Stable (Auto-pause 168 candles on 4 consecutive losses)

🟢 **Exit Research** .............. Stable (13 variants evaluation & MAE/MFE/MC metrics)

🟢 **Walk-Forward Validator** ...... Stable (4 rolling TRAIN/TEST windows)

🟢 **Monte Carlo Simulator** ...... Stable (2,000 bootstrap simulations & ruin probability)

🟢 **Validation Pipeline** ........ Stable (Phases 3–8 master validation runner `run_validation.py`)

🟢 **Web Dashboard** .............. Stable (`ThreadingHTTPServer`, thread-safe locks, DOM polling)

🟢 **Node.js REST API** ............ Stable (Express server with `/api/risk-dashboard` and `/api/research/*`)

🟢 **Mobile Application** .......... Beta (React Native Expo Android app)

🟢 **Technical Documentation** .... Completed (Comprehensive single source of truth in `docs/`)

---

# Priority Levels

The roadmap is divided into four priorities.

## P0 — Critical (Core Architecture & Research Infrastructure)

*Status: Completed in v1.1. Ongoing maintenance and demo monitoring.*

- **Repository Cleanliness & Structure:** Standardize `core/`, `services/`, `strategies/`, and `strategies/experimental/` isolation.
- **Risk Engine v2 Architecture:** Decouple lot sizing, margin checking, portfolio exposure, and circuit breaker.
- **Web Dashboard Refactor:** `ThreadingHTTPServer` implementation with strict `self.lock` discipline.
- **REST API Extensions:** `/api/risk-dashboard` and `/api/research/*` endpoints for mobile telemetry.
- **Exit Research & Validation Pipeline:** 13 exit variants comparison, Stability Score, decision records.
- **Technical Documentation:** Authoritative single-source-of-truth documentation across `docs/` and `README.md`.

---

## P1 — High Priority (Demo Validation & Operational Automation)

- **Demo MT5 Forward Validation Monitoring:** Monitor live forward execution for `eurusd_partial`, `xauusd_partial`, and `btceur_partial` targeting ≥ 50 closed trades per pair.
- **Automated Go-Live Verification Command (`/go_live_check`):** Discord and CLI command verifying all 6 go-live criteria against MT5 demo results.
- **Enhanced Mobile Telemetry:** Real-time push notifications for circuit breaker auto-pause events and trade entries.
- **Research Lab Analytics:** Interactive comparison UI for historical Exit Research runs in Mobile App and Web Dashboard.

## Execution Quality

Status

🟢 Initial Version Completed

Future improvements

- Better latency measurements
- Better slippage analysis
- Spread monitoring
- Broker quality metrics
- Execution history
- Execution statistics

---

## Research Lab

Status

🟡 In Progress

Goals

- Better experiment management
- Research queue
- Progress tracking
- Historical runs
- Better comparison tools

---

## Mobile Dashboard

Goals

- Better charts
- More statistics
- Live synchronization
- Better notifications
- Portfolio overview

---

## Web Dashboard

Goals

- Complete responsive layout
- Better charts
- Better trade explorer
- Better research visualization
- More filters

---

## Research Framework

Goals

- Better reports
- Better exports
- Better run metadata
- Better reproducibility

---

# P2 — Platform Improvements

## Strategy Management

Ideas

- Better strategy comparison
- Version history
- Strategy metadata
- Promotion workflow

---

## Risk Engine

Ideas

- Portfolio level statistics
- Exposure visualization
- Correlation monitoring
- Drawdown analysis

---

## Repository

Ideas

- More examples
- Better templates
- More automation
- Cleaner scripts

---

## Developer Experience

Ideas

- Better tooling
- Better logging
- Better debugging
- Better CI

---

# P3 — Future

These ideas are intentionally low priority.

They should only be considered after the platform reaches a stable state.

Possible future areas

- Multi-account support

- Portfolio management

- Multi-broker execution

- Advanced analytics

- Cloud synchronization

- Plugin system

---

# Development Rules

Before implementing any feature, ask:

## Does this improve architecture?

If no

→ Don't implement it.

---

## Does this improve research?

If no

→ Probably unnecessary.

---

## Does this increase maintainability?

If no

→ Reconsider.

---

## Is there already a module responsible for this?

If yes

→ Improve it.

Don't create another one.

---

## Can this be measured?

If no

→ It shouldn't exist.

---

# Long-Term Vision

LastEdge aims to become a professional quantitative trading platform where every decision is supported by research.

The objective is not to build the largest platform.

The objective is to build one that remains clean, maintainable and reliable after years of continuous development.

---

# Guiding Principle

> Simplicity over complexity.

> Evidence over assumptions.

> Architecture over shortcuts.

> Quality over quantity.