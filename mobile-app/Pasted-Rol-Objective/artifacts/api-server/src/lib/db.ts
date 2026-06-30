/**
 * Lightweight SQLite reader for bot_state.db.
 *
 * We use the built-in `node:sqlite` module (Node 22+).
 * For Node < 22 we fall back to a synchronous open via better-sqlite3
 * (listed as an optional peer).  We keep this file free of Drizzle so
 * the server can run without the workspace lib/db package.
 */
import { DatabaseSync, type SQLInputValue } from "node:sqlite";
import path from "node:path";

// ── Resolve path to bot_state.db ─────────────────────────────────────────────
// Default: same directory as this repo root (c:\BOT-MT5\bot_state.db)
// Override with env var: BOT_DB_PATH=/absolute/path/to/bot_state.db
const DEFAULT_DB_PATH = path.resolve(
  process.env.BOT_DB_PATH ??
    path.join(
      // go up: src/lib -> src -> api-server -> artifacts -> Pasted-Rol-Objective
      // -> mobile-app -> BOT-MT5  (6 levels)
      path.dirname(new URL(import.meta.url).pathname),
      "..",
      "..",
      "..",
      "..",
      "..",
      "..",
      "..",
      "bot_state.db"
    )
);

let _db: DatabaseSync | null = null;

export function getDb(): DatabaseSync {
  if (!_db) {
    _db = new DatabaseSync(DEFAULT_DB_PATH, { open: true });
    ensureSchema(_db);
  }
  return _db;
}

/** Migraciones mínimas para tablas que usa la API móvil. */
export function ensureSchema(db: DatabaseSync = getDb()): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS backtest_tasks (
      id              INTEGER PRIMARY KEY AUTOINCREMENT,
      symbol          TEXT    NOT NULL,
      strategy        TEXT    NOT NULL,
      bars            INTEGER NOT NULL,
      timeframe       TEXT    DEFAULT 'H1',
      cb_losses       INTEGER DEFAULT 4,
      cb_pause        INTEGER DEFAULT 168,
      status          TEXT    NOT NULL DEFAULT 'PENDING',
      results_json    TEXT,
      error_message   TEXT,
      created_at      TEXT    DEFAULT (datetime('now')),
      updated_at      TEXT    DEFAULT (datetime('now'))
    );
  `);

  try {
    const columns = db.prepare("PRAGMA table_info(backtest_tasks)").all() as any[];
    const hasTimeframe = columns.some((col) => col.name === "timeframe");
    if (!hasTimeframe) {
      db.exec("ALTER TABLE backtest_tasks ADD COLUMN timeframe TEXT DEFAULT 'H1'");
    }
  } catch (err) {
    // Ignore error if column already exists
  }
}

/** Run a SELECT and return all rows as plain objects. */
export function query<T = Record<string, unknown>>(
  sql: string,
  params: SQLInputValue[] = []
): T[] {
  const db = getDb();
  const stmt = db.prepare(sql);
  return stmt.all(...params) as T[];
}

/** Run a SELECT that returns a single row (or null). */
export function queryOne<T = Record<string, unknown>>(
  sql: string,
  params: SQLInputValue[] = []
): T | null {
  const db = getDb();
  const stmt = db.prepare(sql);
  return (stmt.get(...params) as T) ?? null;
}

/** Run an INSERT/UPDATE/DELETE. Returns { changes, lastInsertRowid }. */
export function run(
  sql: string,
  params: SQLInputValue[] = []
): { changes: number; lastInsertRowid: number | bigint } {
  const db = getDb();
  const stmt = db.prepare(sql);
  return stmt.run(...params) as { changes: number; lastInsertRowid: number | bigint };
}
