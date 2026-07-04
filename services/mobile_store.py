"""
Persistencia SQLite para la app móvil (api-server Express).

Usa el esquema existente de bot_state.db (session_id, pair, etc.).
"""

from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot_state.db")


def _db_ts() -> str:
    """Timestamp local compatible con datetime('now') de SQLite."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class MobileStore:
    def __init__(self, db_path: str = _DEFAULT_DB):
        self.db_path = db_path
        self._session_id: Optional[str] = None
        self._closed_logged: set[int] = set()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def ensure_tables(self) -> None:
        """Migraciones ligeras sobre el esquema existente del bot."""
        try:
            with self._conn() as conn:
                cols = {r[1] for r in conn.execute("PRAGMA table_info(enhanced_signals)")}
                if cols and "mobile_processed" not in cols:
                    conn.execute(
                        "ALTER TABLE enhanced_signals "
                        "ADD COLUMN mobile_processed INTEGER DEFAULT 0"
                    )
                conn.execute("""
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
                    )
                """)
                cols_bt = {r[1] for r in conn.execute("PRAGMA table_info(backtest_tasks)")}
                if cols_bt and "timeframe" not in cols_bt:
                    conn.execute(
                        "ALTER TABLE backtest_tasks "
                        "ADD COLUMN timeframe TEXT DEFAULT 'H1'"
                    )
            # Garantizar trade_journal
            try:
                from core.journal import get_journal
                get_journal(self.db_path)
            except Exception as journal_err:
                logger.error(f"[MobileStore] Error inicializando trade_journal: {journal_err}")
        except Exception as e:
            logger.error(f"[MobileStore] Error en migración: {e}")

    def start_session(self, balance: float = 0.0) -> None:
        now = _db_ts()
        self._session_id = f"session_{now.replace(' ', '_').replace(':', '')}_{uuid.uuid4().hex[:8]}"
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO session_stats
                       (session_id, start_time, initial_balance, current_balance,
                        peak_balance, total_pnl, last_update)
                       VALUES (?, ?, ?, ?, ?, 0, ?)""",
                    (self._session_id, now, balance, balance, balance, now),
                )
            logger.info(f"[MobileStore] Sesión iniciada: {self._session_id}")
        except Exception as e:
            logger.error(f"[MobileStore] Error iniciando sesión: {e}")
            self._session_id = None

    def update_session(self, balance: float, total_pnl: float) -> None:
        if not self._session_id:
            return
        now = _db_ts()
        try:
            with self._conn() as conn:
                conn.execute(
                    """UPDATE session_stats
                       SET current_balance=?, total_pnl=?, last_update=?,
                           peak_balance=MAX(COALESCE(peak_balance, 0), ?)
                       WHERE session_id=?""",
                    (balance, total_pnl, now, balance, self._session_id),
                )
        except Exception as e:
            logger.warning(f"[MobileStore] update_session: {e}")

    def save_balance_snapshot(
        self,
        balance: float,
        equity: float,
        margin: float = 0.0,
        free_margin: Optional[float] = None,
        open_positions: int = 0,
    ) -> None:
        if not self._session_id:
            return
        if free_margin is None:
            free_margin = max(0.0, equity - margin)
        profit = equity - balance
        now = _db_ts()
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO balance_snapshots
                       (session_id, timestamp, balance, equity, margin,
                        free_margin, profit, open_positions)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        self._session_id,
                        now,
                        balance,
                        equity,
                        margin,
                        free_margin,
                        profit,
                        open_positions,
                    ),
                )
                conn.execute(
                    """DELETE FROM balance_snapshots
                       WHERE id NOT IN (
                         SELECT id FROM balance_snapshots
                         ORDER BY id DESC LIMIT 200
                       )"""
                )
        except Exception as e:
            logger.warning(f"[MobileStore] save_balance_snapshot: {e}")

    def insert_signal(
        self,
        *,
        symbol: str,
        direction: str,
        price: float,
        tp_price: float,
        sl_price: float,
        lot_size: float = 0.01,
        confidence_score: float = 0.0,
        confidence: str = "MEDIUM",
        strategy: str = "",
        status: str = "PROPOSED",
    ) -> Optional[int]:
        if not self._session_id:
            logger.warning("[MobileStore] insert_signal sin session_id activo")
            return None
        now = _db_ts()
        score_int = int(confidence_score * 100) if confidence_score <= 1 else int(confidence_score)
        executed = 1 if status.upper() in ("OPEN", "EXECUTED", "ACCEPTED") else 0
        rejected = 1 if status.upper() == "REJECTED" else 0
        try:
            with self._conn() as conn:
                cur = conn.execute(
                    """INSERT INTO enhanced_signals
                       (session_id, timestamp, symbol, strategy, direction,
                        price, sl_price, tp_price, confidence_level, confidence_score,
                        status, executed, rejected, lot_size, created_at, mobile_processed)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                    (
                        self._session_id,
                        now,
                        symbol.upper(),
                        strategy or "unknown",
                        direction.upper(),
                        price,
                        sl_price,
                        tp_price,
                        confidence,
                        score_int,
                        status.upper(),
                        executed,
                        rejected,
                        lot_size,
                        now,
                    ),
                )
                return cur.lastrowid
        except Exception as e:
            logger.error(f"[MobileStore] insert_signal: {e}")
            return None

    def update_signal_status(self, signal_id: int, status: str) -> None:
        try:
            with self._conn() as conn:
                conn.execute(
                    "UPDATE enhanced_signals SET status=? WHERE id=?",
                    (status.upper(), signal_id),
                )
        except Exception as e:
            logger.debug(f"[MobileStore] update_signal_status: {e}")

    def log_closed_trade(
        self,
        *,
        signal_id: int,
        symbol: str,
        trade_type: str,
        entry_price: float,
        close_price: float,
        sl_price: float,
        tp_price: float,
        pnl: float,
        lot_size: float,
        close_reason: str,
        strategy: str = "",
    ) -> None:
        if signal_id in self._closed_logged or not self._session_id:
            return
        now = _db_ts()
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO session_trades
                       (session_id, timestamp, pair, strategy, type,
                        entry_price, sl_price, tp_price, lot_size, pnl,
                        status, created_at, closed_at, close_price)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        self._session_id,
                        now,
                        symbol.upper(),
                        strategy or "unknown",
                        trade_type.upper(),
                        entry_price,
                        sl_price,
                        tp_price,
                        lot_size,
                        pnl,
                        close_reason.upper(),
                        now,
                        now,
                        close_price,
                    ),
                )
                conn.execute(
                    "UPDATE enhanced_signals SET status=?, pnl=?, closed_at=?, close_price=? WHERE id=?",
                    (close_reason.upper(), pnl, now, close_price, signal_id),
                )

                # Calcular P&L en pips para el diario cuantitativo (trade_journal)
                pip_sizes = {'EURUSD': 0.0001, 'XAUUSD': 0.1, 'BTCEUR': 1.0, 'BTCUSDT': 1.0}
                pip_size = pip_sizes.get(symbol.upper(), 0.0001)
                pips = 0.0
                if entry_price and close_price:
                    if trade_type.upper() == 'BUY':
                        pips = (close_price - entry_price) / pip_size
                    else:
                        pips = (entry_price - close_price) / pip_size

                result = 'WIN' if pnl > 0 else ('LOSS' if pnl < 0 else 'BREAKEVEN')

                try:
                    from core.journal import get_journal
                    closed = get_journal(self.db_path).close_matching_pending(
                        symbol,
                        entry_price=entry_price,
                        close_price=close_price,
                        result=result,
                        pnl_pips=pips,
                        pnl_eur=pnl,
                        notes=f"Cierre MobileStore · signal_id={signal_id}",
                    )
                    if not closed:
                        get_journal(self.db_path).log_entry(
                            {
                                'symbol': symbol,
                                'type': trade_type,
                                'entry': entry_price,
                                'sl': sl_price,
                                'tp': tp_price,
                                'strategy_used': strategy or 'unknown',
                            },
                            lot_size=lot_size,
                            mode='live',
                            notes=f"Apertura+cierre en un paso · signal_id={signal_id}",
                        )
                        get_journal(self.db_path).close_matching_pending(
                            symbol,
                            entry_price=entry_price,
                            close_price=close_price,
                            result=result,
                            pnl_pips=pips,
                            pnl_eur=pnl,
                        )
                except Exception as journal_err:
                    logger.warning(f"[MobileStore] trade_journal: {journal_err}")

            self._closed_logged.add(signal_id)
        except Exception as e:
            logger.warning(f"[MobileStore] log_closed_trade: {e}")

    def get_unprocessed_mobile_actions(self) -> List[Dict[str, Any]]:
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    """SELECT id, symbol, direction, price, tp_price, sl_price,
                              lot_size, status, confidence_score, strategy, created_at
                       FROM enhanced_signals
                       WHERE COALESCE(mobile_processed, 0) = 0
                         AND status IN ('ACCEPTED', 'REJECTED')
                       ORDER BY id ASC"""
                ).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.debug(f"[MobileStore] get_unprocessed_mobile_actions: {e}")
            return []

    def mark_mobile_processed(self, signal_id: int, *, executed: bool = False) -> None:
        try:
            with self._conn() as conn:
                conn.execute(
                    """UPDATE enhanced_signals
                       SET mobile_processed=1, executed=?
                       WHERE id=?""",
                    (1 if executed else 0, signal_id),
                )
        except Exception as e:
            logger.debug(f"[MobileStore] mark_mobile_processed: {e}")

    def process_mobile_actions(self) -> None:
        """Ejecuta señales ACCEPTED desde la app en MT5 demo."""
        if not hasattr(self, "_market_closed_last_log"):
            # Dict[signal_id -> last_log_timestamp]  — throttle de 10 min por señal
            self._market_closed_last_log: dict[int, float] = {}

        for row in self.get_unprocessed_mobile_actions():
            sid = row["id"]
            status = (row["status"] or "").upper()

            if status == "REJECTED":
                self.mark_mobile_processed(sid, executed=False)
                logger.info(f"[MobileStore] Señal {sid} rechazada desde app móvil")
                continue

            if status != "ACCEPTED":
                continue

            symbol = row.get("symbol", "UNKNOWN")

            # ── Expiración de señales antiguas ────────────────────────────────
            # Si la señal fue creada hace más de MAX_PENDING_HOURS y el mercado
            # sigue cerrado, marcarla como EXPIRED para limpiar la cola.
            # Esto evita que señales del viernes bloqueen el bot todo el finde.
            created_at_raw = row.get("created_at") or ""
            if created_at_raw and self._signal_is_expired(sid, created_at_raw, symbol):
                logger.warning(
                    f"[MobileStore] Señal {sid} ({symbol}) expirada sin ejecutar "
                    f"(creada: {created_at_raw}). Marcando como EXPIRED."
                )
                self.mark_mobile_processed(sid, executed=False)
                self.update_signal_status(sid, "EXPIRED")
                self._market_closed_last_log.pop(sid, None)
                continue

            # ── Comprobar si el mercado está abierto ANTES de intentar ────────
            if not self._is_market_open(symbol):
                import time
                now = time.monotonic()
                last = self._market_closed_last_log.get(sid, 0.0)
                if now - last >= 600:  # loguear como máximo 1 vez cada 10 minutos
                    logger.warning(
                        f"[MobileStore] Señal {sid} ({symbol}): mercado cerrado. "
                        f"Se reintentará cuando abra."
                    )
                    self._market_closed_last_log[sid] = now
                continue  # NO marcar como procesada — reintentar cuando abra

            # Mercado abierto — limpiar throttle
            self._market_closed_last_log.pop(sid, None)

            signal = {
                "symbol": symbol,
                "type": row["direction"],
                "entry": row["price"],
                "sl": row["sl_price"],
                "tp": row["tp_price"],
                "strategy_used": row["strategy"] or "mobile_accept",
            }
            try:
                from services.execution import get_execution_service

                result = get_execution_service().execute_signal(signal)
                if result.success:
                    self.mark_mobile_processed(sid, executed=True)
                    self.update_signal_status(sid, "OPEN")
                    logger.info(
                        f"[MobileStore] Señal {sid} ejecutada en MT5 "
                        f"(ticket {result.order_id})"
                    )
                else:
                    msg = result.message or ""
                    if "10018" in msg or "market closed" in msg.lower():
                        # Race condition entre check y send — silenciar y reintentar
                        import time
                        now = time.monotonic()
                        last = self._market_closed_last_log.get(sid, 0.0)
                        if now - last >= 600:
                            logger.warning(
                                f"[MobileStore] Señal {sid} ({symbol}): mercado cerrado "
                                f"durante la ejecución. Esperando reapertura."
                            )
                            self._market_closed_last_log[sid] = now
                    else:
                        # Error genuino no recuperable — marcar para no reintentar
                        logger.warning(
                            f"[MobileStore] Fallo ejecutando señal {sid}: {result.message}"
                        )
                        self.mark_mobile_processed(sid, executed=False)
                        self.update_signal_status(sid, "FAILED")
            except Exception as e:
                logger.error(f"[MobileStore] Error ejecutando señal {sid}: {e}")

    def _mt5_open_positions(self) -> int:
        try:
            import MetaTrader5 as mt5

            positions = mt5.positions_get()
            return len(positions) if positions else 0
        except Exception:
            return 0

    def _is_market_open(self, symbol: str) -> bool:
        """
        Comprueba si el mercado de un símbolo está abierto en MT5.

        Usa mt5.symbol_info() para leer el campo `trade_mode`:
          - SYMBOL_TRADE_MODE_FULL (4)  → mercado abierto
          - cualquier otro valor        → cerrado, solo lectura, etc.

        Si MT5 no está disponible o hay error, devuelve True para no
        bloquear señales en caso de fallo de conexión temporal.
        """
        try:
            import MetaTrader5 as mt5

            info = mt5.symbol_info(symbol)
            if info is None:
                # MT5 no reconoce el símbolo — dejar pasar para que
                # el error se maneje en execute_signal con más contexto
                return True
            # trade_mode == 4 (SYMBOL_TRADE_MODE_FULL) = mercado abierto
            return info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL
        except Exception:
            return True  # fail-open: si no podemos comprobar, intentamos

    def _signal_is_expired(self, sid: int, created_at: str, symbol: str) -> bool:
        """
        Determina si una señal pendiente ha expirado y ya no debe ejecutarse.

        Lógica:
          - BTCEUR / crypto: 72h (mercado 24/7, si lleva 3 días sin ejecutarse
            el precio ha cambiado demasiado)
          - EURUSD / XAUUSD / Forex: 4h (solo tiene sentido en la sesión en que
            se generó; más allá el contexto de la señal ya no es válido)

        Si el mercado está actualmente ABIERTO no se expira (puede que la señal
        esté esperando a que el precio vuelva a ser válido).
        """
        # Solo expirar señales cuyo mercado está cerrado en este momento
        if self._is_market_open(symbol):
            return False

        MAX_PENDING_HOURS: dict[str, float] = {
            "BTCEUR":  72.0,
            "BTCUSDT": 72.0,
            "EURUSD":   4.0,
            "XAUUSD":   4.0,
        }
        max_hours = MAX_PENDING_HOURS.get(symbol.upper(), 4.0)

        try:
            from datetime import datetime
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            # Si created_at no tiene timezone, asumimos local
            if created.tzinfo is None:
                created = created.replace(tzinfo=datetime.now().astimezone().tzinfo)
            age_hours = (datetime.now(created.tzinfo) - created).total_seconds() / 3600
            return age_hours > max_hours
        except Exception:
            return False  # si no podemos parsear la fecha, no expiramos

    def sync_dashboard(self, dashboard) -> None:
        """Sincroniza equity MT5, acciones móviles y trades cerrados."""
        self.process_mobile_actions()

        try:
            snap = dashboard.get_equity_snapshot()
            balance = float(snap.get("balance") or 0)
            equity = float(snap.get("total_equity") or balance)
            change = float(snap.get("change") or 0)
            margin = float(snap.get("margin") or 0)
            free_margin = float(snap.get("free_margin") or max(0.0, equity - margin))
            open_positions = self._mt5_open_positions()

            self.save_balance_snapshot(
                balance, equity, margin, free_margin, open_positions
            )
            self.update_session(equity, change)
        except Exception as e:
            logger.warning(f"[MobileStore] sync equity: {e}")

        # Trades cerrados: solo señales ejecutadas en MT5 (no simulación paper)
        try:
            with dashboard.lock:
                for ev in dashboard.signal_history:
                    if not getattr(ev, "mobile_signal_id", None):
                        continue
                    if not ev.executed:
                        continue
                    if ev.final_status not in ("win", "loss"):
                        continue
                    sid = ev.mobile_signal_id
                    if sid in self._closed_logged:
                        continue

                    pnl = self._estimate_pnl(ev)
                    reason = "TAKE_PROFIT" if ev.final_status == "win" else "STOP_LOSS"
                    close_price = float(ev.tp if ev.final_status == "win" else ev.sl or 0)

                    self.log_closed_trade(
                        signal_id=sid,
                        symbol=ev.symbol,
                        trade_type=ev.signal_type,
                        entry_price=float(ev.entry or 0),
                        close_price=close_price,
                        sl_price=float(ev.sl or 0),
                        tp_price=float(ev.tp or 0),
                        pnl=pnl,
                        lot_size=0.01,
                        close_reason=reason,
                        strategy=ev.strategy,
                    )
        except Exception as e:
            logger.debug(f"[MobileStore] sync closed trades: {e}")

    @staticmethod
    def _estimate_pnl(ev) -> float:
        """Estima P&L en EUR usando MT5 si hay posición; si no, por movimiento de precio."""
        try:
            import MetaTrader5 as mt5

            positions = mt5.positions_get(symbol=ev.symbol)
            if positions:
                return float(sum(p.profit for p in positions))
        except Exception:
            pass
        # Fallback: % del riesgo configurado sobre balance MT5
        try:
            import MetaTrader5 as mt5

            info = mt5.account_info()
            balance = float(info.balance) if info else 5000.0
        except Exception:
            balance = 5000.0
        risk_pct = float(os.getenv("MT5_RISK_PCT", "0.5")) / 100.0
        risk_eur = balance * risk_pct
        if ev.final_status == "win" and ev.entry and ev.sl and ev.tp:
            risk = abs(ev.entry - ev.sl)
            rr = abs(ev.tp - ev.entry) / risk if risk > 0 else 1.0
            return risk_eur * rr
        return -risk_eur


_store: Optional[MobileStore] = None


def get_mobile_store(db_path: str = _DEFAULT_DB) -> MobileStore:
    global _store
    if _store is None:
        _store = MobileStore(db_path)
    return _store
