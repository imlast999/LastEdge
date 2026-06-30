/**
 * Bot routes — reads data from bot_state.db (SQLite written by the Python bot).
 *
 * Endpoints:
 *   GET  /api/status           — MT5 connection state, balance, equity, uptime
 *   GET  /api/signals          — pending + active signals from enhanced_signals
 *   GET  /api/trades           — closed trades from trades_history
 *   GET  /api/equityHistory    — last 48 balance snapshots for the equity chart
 *   POST /api/signals/:id/accept  — mark signal as ACCEPTED (writes back to DB)
 *   POST /api/signals/:id/reject  — mark signal as REJECTED
 *
 * Data strategy: read-only from bot_state.db for GET endpoints.
 * accept/reject write a status flag so the Python bot can pick it up on its
 * next polling cycle (it already reads `session_trades.status`).
 */
import { Router, Request, Response } from "express";
import { query, queryOne, run } from "../lib/db.js";
import { logger } from "../lib/logger.js";

export const botRouter = Router();

// ── Types mirrored from TradingContext ────────────────────────────────────────

interface BotStatus {
  connected: boolean;
  uptime: string;
  balance: number;
  equity: number;
  margin: number;
  freeMargin: number;
}

interface Signal {
  id: string;
  symbol: string;
  type: "BUY" | "SELL";
  entry: number;
  takeProfit: number;
  stopLoss: number;
  status: "pending" | "active" | "closed" | "rejected";
  rrRatio: number;
  timestamp: string;
  lot: number;
}

interface Trade {
  id: string;
  symbol: string;
  type: "BUY" | "SELL";
  openPrice: number;
  closePrice: number;
  pips: number;
  profit: number;
  closeReason: "TAKE_PROFIT" | "STOP_LOSS" | "MANUAL";
  closedAt: string;
  lot: number;
}

interface EquityPoint {
  time: number;
  value: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function safeFloat(v: unknown, fallback = 0): number {
  const n = parseFloat(String(v ?? ""));
  return isFinite(n) ? n : fallback;
}

function formatUptime(startTimeIso: string | null): string {
  if (!startTimeIso) return "unknown";
  try {
    const start = new Date(startTimeIso).getTime();
    const diffMs = Date.now() - start;
    if (diffMs < 0) return "unknown";
    const h = Math.floor(diffMs / 3600000);
    const m = Math.floor((diffMs % 3600000) / 60000);
    return `${h}h ${m}m`;
  } catch {
    return "unknown";
  }
}

// Map DB signal status to the mobile app's expected values
function mapSignalStatus(dbStatus: string | null): Signal["status"] {
  switch ((dbStatus ?? "").toUpperCase()) {
    case "PROPOSED":
    case "PENDING":
      return "pending";
    case "ACCEPTED":
    case "EXECUTED":
    case "OPEN":
      return "active";
    case "CLOSED":
    case "TAKE_PROFIT":
    case "STOP_LOSS":
      return "closed";
    case "REJECTED":
      return "rejected";
    default:
      return "pending";
  }
}

function mapCloseReason(reason: string | null): Trade["closeReason"] {
  switch ((reason ?? "").toUpperCase()) {
    case "TAKE_PROFIT":
    case "TP":
      return "TAKE_PROFIT";
    case "STOP_LOSS":
    case "SL":
      return "STOP_LOSS";
    default:
      return "MANUAL";
  }
}

// ── GET /api/status (público — montado sin auth en routes/index.ts) ───────────

export function getBotStatus(_req: Request, res: Response): void {
  try {
    // Latest session stats row
    type SessionRow = {
      start_time: string | null;
      current_balance: number | null;
      total_pnl: number | null;
    };
    const session = queryOne<SessionRow>(
      `SELECT start_time, current_balance, total_pnl
       FROM session_stats
       ORDER BY rowid DESC
       LIMIT 1`
    );

    // Latest balance snapshot for equity / margin
    type SnapRow = {
      balance: number | null;
      equity: number | null;
      margin: number | null;
      free_margin: number | null;
    };
    const snap = queryOne<SnapRow>(
      `SELECT balance, equity, margin, free_margin
       FROM balance_snapshots
       ORDER BY rowid DESC
       LIMIT 1`
    );

    const balance = safeFloat(snap?.balance ?? session?.current_balance);
    const equity = safeFloat(snap?.equity ?? balance);
    const margin = safeFloat(snap?.margin);
    const freeMargin = safeFloat(snap?.free_margin ?? equity - margin);

    // Consider "connected" if a snapshot or session update occurred in the last 5 minutes
    type TimeRow = { ts: string | null };
    const recent = queryOne<TimeRow>(
      `SELECT timestamp as ts
       FROM balance_snapshots
       WHERE datetime(timestamp) > datetime('now', '-5 minutes')
       ORDER BY rowid DESC
       LIMIT 1`
    );
    const recentSession = queryOne<TimeRow>(
      `SELECT last_update as ts
       FROM session_stats
       WHERE datetime(last_update) > datetime('now', '-5 minutes')
       ORDER BY rowid DESC
       LIMIT 1`
    );

    const status: BotStatus = {
      connected: recent !== null || recentSession !== null,
      uptime: formatUptime(session?.start_time ?? null),
      balance,
      equity,
      margin,
      freeMargin,
    };

    res.json(status);
  } catch (err) {
    logger.error({ err }, "GET /api/status error");
    res.status(500).json({ error: "Failed to read bot status" });
  }
}

// ── GET /api/signals ──────────────────────────────────────────────────────────

botRouter.get("/signals", (_req: Request, res: Response) => {
  try {
    type SigRow = {
      id: number;
      symbol: string;
      direction: string;
      price: number;
      tp_price: number;
      sl_price: number;
      status: string;
      lot_size: number;
      created_at: string;
      confidence_score: number | null;
    };

    const rows = query<SigRow>(
      `SELECT id, symbol, direction, price, tp_price, sl_price,
              status, lot_size, created_at, confidence_score
       FROM enhanced_signals
       WHERE status NOT IN ('CLOSED')
       ORDER BY created_at DESC
       LIMIT 100`
    );

    const signals: Signal[] = rows.map((r) => {
      const entry = safeFloat(r.price);
      const tp = safeFloat(r.tp_price);
      const sl = safeFloat(r.sl_price);
      const risk = Math.abs(entry - sl);
      const reward = Math.abs(tp - entry);
      const rrRatio = risk > 0 ? parseFloat((reward / risk).toFixed(2)) : 0;

      return {
        id: String(r.id),
        symbol: r.symbol ?? "UNKNOWN",
        type: (r.direction ?? "BUY").toUpperCase() as "BUY" | "SELL",
        entry,
        takeProfit: tp,
        stopLoss: sl,
        status: mapSignalStatus(r.status),
        rrRatio,
        timestamp: r.created_at ?? new Date().toISOString(),
        lot: safeFloat(r.lot_size, 0.01),
      };
    });

    res.json(signals);
  } catch (err) {
    logger.error({ err }, "GET /api/signals error");
    res.status(500).json({ error: "Failed to read signals" });
  }
});

// ── GET /api/trades ───────────────────────────────────────────────────────────

botRouter.get("/trades", (_req: Request, res: Response) => {
  try {
    type TradeRow = {
      id: number;
      symbol: string;
      trade_type: string;
      entry_price: number;
      result: string | null;
      pnl: number | null;
      lot_size: number;
      timestamp: string;
      close_price: number | null;
      closed_at: string | null;
    };

    // Prefer session_trades (richer data), fall back to trades_history
    const rows = query<TradeRow>(
      `SELECT id, pair as symbol, type as trade_type, entry_price,
              status as result, pnl, lot_size, created_at as timestamp,
              close_price, closed_at
       FROM session_trades
       WHERE status IN ('CLOSED', 'TAKE_PROFIT', 'STOP_LOSS')
       ORDER BY closed_at DESC
       LIMIT 200`
    );

    const trades: Trade[] = rows.map((r) => {
      const openPrice = safeFloat(r.entry_price);
      const closePrice = safeFloat(r.close_price ?? r.entry_price);
      const profit = safeFloat(r.pnl);
      // Approximate pips from price difference (symbol-aware would be better)
      const rawPips = closePrice - openPrice;
      const pips = parseFloat(rawPips.toFixed(1));

      return {
        id: String(r.id),
        symbol: r.symbol ?? "UNKNOWN",
        type: (r.trade_type ?? "BUY").toUpperCase() as "BUY" | "SELL",
        openPrice,
        closePrice,
        pips,
        profit,
        closeReason: mapCloseReason(r.result),
        closedAt:
          r.closed_at ?? r.timestamp ?? new Date().toISOString(),
        lot: safeFloat(r.lot_size, 0.01),
      };
    });

    res.json(trades);
  } catch (err) {
    logger.error({ err }, "GET /api/trades error");
    res.status(500).json({ error: "Failed to read trades" });
  }
});

// ── GET /api/equityHistory ────────────────────────────────────────────────────

botRouter.get("/equityHistory", (_req: Request, res: Response) => {
  try {
    type SnapRow = { timestamp: string; equity: number };

    const rows = query<SnapRow>(
      `SELECT timestamp, equity
       FROM balance_snapshots
       ORDER BY rowid DESC
       LIMIT 48`
    );

    // Return in ascending time order for the chart
    const points: EquityPoint[] = rows
      .reverse()
      .map((r) => ({
        time: new Date(r.timestamp).getTime(),
        value: safeFloat(r.equity),
      }));

    res.json(points);
  } catch (err) {
    logger.error({ err }, "GET /api/equityHistory error");
    res.status(500).json({ error: "Failed to read equity history" });
  }
});

// ── POST /api/signals/:id/accept ─────────────────────────────────────────────

botRouter.post("/signals/:id/accept", (req: Request, res: Response) => {
  const rawId = req.params.id;
  const id = parseInt(Array.isArray(rawId) ? rawId[0] ?? "" : rawId ?? "", 10);
  if (isNaN(id)) {
    res.status(400).json({ ok: false, message: "Invalid signal id" });
    return;
  }
  try {
    const result = run(
      `UPDATE enhanced_signals
       SET status = 'ACCEPTED', executed = 1
       WHERE id = ? AND status IN ('PROPOSED', 'PENDING')`,
      [id]
    );
    if (result.changes === 0) {
      res.status(404).json({
        ok: false,
        message: "Signal not found or already actioned",
      });
      return;
    }
    logger.info({ signalId: id }, "Signal accepted via mobile app");
    res.json({ ok: true });
  } catch (err) {
    logger.error({ err, signalId: id }, "POST /api/signals/:id/accept error");
    res.status(500).json({ ok: false, message: "Failed to accept signal" });
  }
});

// ── POST /api/signals/:id/reject ─────────────────────────────────────────────

botRouter.post("/signals/:id/reject", (req: Request, res: Response) => {
  const rawId = req.params.id;
  const id = parseInt(Array.isArray(rawId) ? rawId[0] ?? "" : rawId ?? "", 10);
  if (isNaN(id)) {
    res.status(400).json({ ok: false, message: "Invalid signal id" });
    return;
  }
  try {
    const result = run(
      `UPDATE enhanced_signals
       SET status = 'REJECTED', rejected = 1
       WHERE id = ? AND status IN ('PROPOSED', 'PENDING')`,
      [id]
    );
    if (result.changes === 0) {
      res.status(404).json({
        ok: false,
        message: "Signal not found or already actioned",
      });
      return;
    }
    logger.info({ signalId: id }, "Signal rejected via mobile app");
    res.json({ ok: true });
  } catch (err) {
    logger.error({ err, signalId: id }, "POST /api/signals/:id/reject error");
    res.status(500).json({ ok: false, message: "Failed to reject signal" });
  }
});

// ── GET /api/backtests ────────────────────────────────────────────────────────

botRouter.get("/backtests", (_req: Request, res: Response) => {
  try {
    type TaskRow = {
      id: number;
      symbol: string;
      strategy: string;
      bars: number;
      timeframe: string;
      status: string;
      created_at: string | null;
      updated_at: string | null;
      error_message: string | null;
    };
    const rows = query<TaskRow>(
      `SELECT id, symbol, strategy, bars, timeframe, status, created_at, updated_at, error_message
       FROM backtest_tasks
       ORDER BY id DESC
       LIMIT 30`
    );
    res.json({ ok: true, tasks: rows });
  } catch (err) {
    logger.error({ err }, "GET /api/backtests error");
    res.status(500).json({ ok: false, message: "Failed to list backtest tasks" });
  }
});

// ── POST /api/backtests ───────────────────────────────────────────────────────

botRouter.post("/backtests", (req: Request, res: Response) => {
  const { symbol, strategy, bars, timeframe = "H1", cb_losses = 4, cb_pause = 168 } = req.body;
  if (!symbol || !strategy || !bars || isNaN(parseInt(bars, 10))) {
    res.status(400).json({ ok: false, message: "Missing or invalid parameters" });
    return;
  }

  try {
    const result = run(
      `INSERT INTO backtest_tasks (symbol, strategy, bars, timeframe, cb_losses, cb_pause, status)
       VALUES (?, ?, ?, ?, ?, ?, 'PENDING')`,
      [symbol.toUpperCase(), strategy, parseInt(bars, 10), String(timeframe).toUpperCase(), parseInt(cb_losses, 10), parseInt(cb_pause, 10)]
    );

    res.json({ ok: true, taskId: result.lastInsertRowid });
  } catch (err) {
    logger.error({ err }, "POST /api/backtests error");
    res.status(500).json({ ok: false, message: "Failed to queue backtest task" });
  }
});

// ── GET /api/strategies ────────────────────────────────────────────────────────
// Devuelve la lista de estrategias disponibles.
// Nota: el API server es TypeScript/Node y no puede importar Python directamente,
// así que devolvemos una lista basada en el registry conocido. Si se añaden
// estrategias nuevas en signals.py, actualizar también este array.

botRouter.get("/strategies", (_req: Request, res: Response) => {
  try {
    const strategies = [
      { id: "eurusd_simple",         name: "EURUSD SIMPLE",         symbol: "EURUSD" },
      { id: "eurusd_advanced",       name: "EURUSD ADVANCED",       symbol: "EURUSD" },
      { id: "eurusd_asian_breakout", name: "EURUSD ASIAN BREAKOUT", symbol: "EURUSD" },
      { id: "eurusd_mtf",            name: "EURUSD MTF",            symbol: "EURUSD" },
      { id: "xauusd_simple",         name: "XAUUSD SIMPLE",         symbol: "XAUUSD" },
      { id: "xauusd_advanced",       name: "XAUUSD ADVANCED",       symbol: "XAUUSD" },
      { id: "xauusd_reversal",       name: "XAUUSD REVERSAL",       symbol: "XAUUSD" },
      { id: "xauusd_momentum",       name: "XAUUSD MOMENTUM",       symbol: "XAUUSD" },
      { id: "xauusd_psychological",  name: "XAUUSD PSYCHOLOGICAL",  symbol: "XAUUSD" },
      { id: "btceur_simple",         name: "BTCEUR SIMPLE",         symbol: "BTCEUR" },
      { id: "btceur_advanced",       name: "BTCEUR ADVANCED",       symbol: "BTCEUR" },
      { id: "btc_trend_pullback_v1", name: "BTC TREND PULLBACK",    symbol: "BTCEUR" },
      { id: "btceur_weekly_breakout",name: "BTCEUR WEEKLY BREAKOUT",symbol: "BTCEUR" },
      { id: "btceur_regime_momentum",name: "BTCEUR REGIME MOMENTUM",symbol: "BTCEUR" },
      { id: "btcusdt",               name: "BTCUSDT",               symbol: "BTCEUR" },
      { id: "btc",                   name: "BTC",                   symbol: "BTCEUR" },
      { id: "ema50_200",             name: "EMA 50/200",            symbol: "EURUSD" },
      { id: "rsi",                   name: "RSI REVERSAL",          symbol: "EURUSD" },
      { id: "macd",                  name: "MACD CROSSOVER",        symbol: "EURUSD" },
    ];

    res.json({ ok: true, strategies });
  } catch (err) {
    logger.error({ err }, "GET /api/strategies error");
    res.status(500).json({ ok: false, message: "Failed to list strategies" });
  }
});

// ── GET /api/backtests/:id ────────────────────────────────────────────────────

botRouter.get("/backtests/:id", (req: Request, res: Response) => {
  const rawId = req.params.id;
  const id = parseInt(Array.isArray(rawId) ? rawId[0] ?? "" : rawId ?? "", 10);
  if (isNaN(id)) {
    res.status(400).json({ ok: false, message: "Invalid task id" });
    return;
  }

  try {
    type TaskRow = {
      id: number;
      symbol: string;
      strategy: string;
      bars: number;
      timeframe: string;
      status: string;
      results_json: string | null;
      error_message: string | null;
    };

    const task = queryOne<TaskRow>(
      `SELECT id, symbol, strategy, bars, timeframe, status, results_json, error_message
       FROM backtest_tasks
       WHERE id = ?`,
      [id]
    );

    if (!task) {
      res.status(404).json({ ok: false, message: "Backtest task not found" });
      return;
    }

    let results = null;
    if (task.results_json) {
      try {
        results = JSON.parse(task.results_json);
      } catch (parseErr) {
        logger.error({ parseErr }, "Error parsing results_json from DB");
      }
    }

    res.json({
      ok: true,
      taskId: task.id,
      symbol: task.symbol,
      strategy: task.strategy,
      bars: task.bars,
      timeframe: task.timeframe ?? "H1",
      status: task.status,
      results,
      errorMessage: task.error_message,
    });
  } catch (err) {
    logger.error({ err, taskId: id }, "GET /api/backtests/:id error");
    res.status(500).json({ ok: false, message: "Failed to query backtest task" });
  }
});
