"""Servicio de Dashboard Consolidado"""

import logging
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
import threading
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

try:
    from core import active_symbols, set_language, get_language, get_language_name, get_supported_languages_display
except Exception:
    active_symbols = {}
    def set_language(lang): pass
    def get_language(): return 'en'
    def get_language_name(): return 'English'
    def get_supported_languages_display(): return []

try:
    from core.engine import symbol_health
except Exception:
    symbol_health = {}

logger = logging.getLogger(__name__)


@dataclass
class DashboardMetrics:
    signals_today: int = 0
    signals_shown: int = 0
    signals_executed: int = 0
    signals_rejected: int = 0
    symbol_activity: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    symbol_performance: Dict[str, Dict] = field(default_factory=dict)
    confidence_distribution: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    positions_open: int = 0
    total_profit: float = 0.0
    win_rate: float = 0.0
    uptime_seconds: int = 0
    last_signal_time: Optional[datetime] = None
    system_status: str = "RUNNING"
    # Balance base de la sesión (desde MT5 al arrancar)
    paper_balance: float = 0.0          # legacy — no usado
    paper_balance_base: float = 0.0     # balance inicial MT5 de la sesión


@dataclass
class SignalEvent:
    timestamp: datetime
    symbol: str
    strategy: str
    signal_type: str
    confidence: str
    score: float
    shown: bool
    executed: bool
    rejection_reason: Optional[str] = None
    entry: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    # Estado persistente — una vez WIN/LOSS no cambia aunque MT5 no responda
    final_status: Optional[str] = None   # None | 'win' | 'loss' | 'open'
    # P&L simulado en tiempo real (actualizado por el background loop)
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None   # en % del riesgo
    mobile_signal_id: Optional[int] = None     # id en enhanced_signals (app móvil)
    
    # Execution Quality
    latency_ms: Optional[int] = None
    slippage_pips: Optional[float] = None


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


class DashboardService:

    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.session_start = datetime.now(timezone.utc)   # inicio de esta sesión
        self.metrics = DashboardMetrics()
        self.signal_history = deque(maxlen=2000)
        self.performance_history = deque(maxlen=200)
        self.last_mt5_update: Optional[datetime] = None
        self.dashboard_config = {
            'update_interval': int(os.getenv('DASHBOARD_UPDATE_INTERVAL', '30')),
            'history_retention_hours': int(os.getenv('DASHBOARD_HISTORY_HOURS', '168')),
            'enable_persistence': os.getenv('DASHBOARD_PERSISTENCE', '1') == '1',
            'data_file': os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dashboard_data.json')
        }
        self.is_running = False
        self.update_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self.server_instance: Optional[ThreadingHTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        # Estado de ejecución real (sincronizado con autosignals)
        self.auto_execute_enabled = os.getenv('AUTO_EXECUTE_SIGNALS', '1') == '1'
        self.auto_execute_confidence = os.getenv('AUTO_EXECUTE_CONFIDENCE', 'HIGH')
        if self.dashboard_config['enable_persistence']:
            self._load_persisted_data()

    def start(self):
        try:
            with self.lock:
                if self.is_running:
                    return
                self.is_running = True
                self.start_time = datetime.now(timezone.utc)

            # Fuera del lock: get_equity_snapshot() también adquiere self.lock
            try:
                from services.mobile_store import get_mobile_store
                store = get_mobile_store()
                store.ensure_tables()
                snap = self.get_equity_snapshot()
                base = float(snap.get('base_balance') or 5000.0)
                store.start_session(base)
            except Exception as ms_err:
                logger.warning(f"Mobile store init: {ms_err}")

            self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self.update_thread.start()
            self._start_web_server()
            logger.info("Dashboard service started")
        except Exception as e:
            logger.error(f"Error starting dashboard: {e}")
            self.is_running = False

    def _start_web_server(self):
        try:
            if os.getenv('DISABLE_DASHBOARD', '0') == '1':
                return
            dashboard_service = self

            class Handler(BaseHTTPRequestHandler):
                def _get_lang_from_cookie(self) -> str:
                    """Parse 'lang' cookie from request headers. Default: 'en'."""
                    cookie_header = self.headers.get('Cookie', '')
                    for part in cookie_header.split(';'):
                        part = part.strip()
                        if part.startswith('lang='):
                            val = part.split('=', 1)[1].strip()
                            return val if val in ('en', 'es') else 'en'
                    return 'en'

                def do_GET(self):
                    try:
                        # ── Language-switch endpoint ─────────────────────────────────────
                        if self.path.startswith('/api/set-language'):
                            from urllib.parse import urlparse, parse_qs
                            qs = parse_qs(urlparse(self.path).query)
                            lang = qs.get('lang', ['en'])[0]
                            if lang in ('en', 'es'):
                                set_language(lang)
                            from http.cookies import SimpleCookie
                            c = SimpleCookie()
                            c['lang'] = lang
                            c['lang']['path'] = '/'
                            c['lang']['max-age'] = 31536000  # 1 year
                            redirect = qs.get('redirect', ['/'])[0]
                            self.send_response(302)
                            self.send_header('Location', redirect)
                            self.send_header('Set-Cookie', c['lang'].OutputString())
                            self.end_headers()
                            return

                        if self.path in ('/', '/dashboard'):
                            lang = self._get_lang_from_cookie()
                            body = dashboard_service.get_dashboard_html(lang=lang).encode('utf-8')
                            self.send_response(200)
                            self.send_header('Content-type', 'text/html; charset=utf-8')
                            self.end_headers()
                            try:
                                self.wfile.write(body)
                            except (ConnectionAbortedError, BrokenPipeError, OSError):
                                pass  # navegador cerró la conexión — no es un error real
                        elif self.path.startswith('/api/analytics/execution'):
                            from services.bot_service import get_bot_service
                            data = get_bot_service().get_execution_analytics()
                            body = json.dumps(data, indent=2, default=str).encode('utf-8')
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            try:
                                self.wfile.write(body)
                            except (ConnectionAbortedError, BrokenPipeError, OSError):
                                pass
                        elif self.path.startswith('/api/health/system'):
                            from services.bot_service import get_bot_service
                            data = get_bot_service().get_health_status()
                            body = json.dumps(data, indent=2, default=str).encode('utf-8')
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            try:
                                self.wfile.write(body)
                            except (ConnectionAbortedError, BrokenPipeError, OSError):
                                pass
                        elif self.path.startswith('/api/system/go-live-checklist'):
                            from services.bot_service import get_bot_service
                            data = get_bot_service().run_go_live_checklist()
                            body = json.dumps(data, indent=2, default=str).encode('utf-8')
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            try:
                                self.wfile.write(body)
                            except (ConnectionAbortedError, BrokenPipeError, OSError):
                                pass
                        elif self.path.startswith('/api/system/verify-production'):
                            from services.bot_service import get_bot_service
                            data = get_bot_service().run_production_verification()
                            body = json.dumps(data, indent=2, default=str).encode('utf-8')
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            try:
                                self.wfile.write(body)
                            except (ConnectionAbortedError, BrokenPipeError, OSError):
                                pass
                        elif self.path.startswith('/api/system/long-forward-validation/history'):
                            from services.bot_service import get_bot_service
                            data = get_bot_service().list_long_forward_sessions()
                            body = json.dumps({"ok": True, "sessions": data}, indent=2, default=str).encode('utf-8')
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            try:
                                self.wfile.write(body)
                            except (ConnectionAbortedError, BrokenPipeError, OSError):
                                pass
                        elif self.path.startswith('/api/system/long-forward-validation/'):
                            session_id = self.path.split('/')[-1]
                            from services.bot_service import get_bot_service
                            data = get_bot_service().get_long_forward_session(session_id)
                            body = json.dumps(data, indent=2, default=str).encode('utf-8')
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            try:
                                self.wfile.write(body)
                            except (ConnectionAbortedError, BrokenPipeError, OSError):
                                pass
                        elif self.path.startswith('/api/system/broker-certification'):
                            from services.bot_service import get_bot_service
                            data = get_bot_service().run_broker_certification()
                            body = json.dumps(data, indent=2, default=str).encode('utf-8')
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            try:
                                self.wfile.write(body)
                            except (ConnectionAbortedError, BrokenPipeError, OSError):
                                pass
                        elif self.path.startswith('/api/system/long-forward-validation'):
                            from services.bot_service import get_bot_service
                            data = get_bot_service().get_long_forward_status()
                            body = json.dumps(data, indent=2, default=str).encode('utf-8')
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            try:
                                self.wfile.write(body)
                            except (ConnectionAbortedError, BrokenPipeError, OSError):
                                pass
                        elif self.path == '/api/metrics':
                            body = json.dumps(dashboard_service.get_current_metrics(), indent=2, default=str).encode('utf-8')
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            try:
                                self.wfile.write(body)
                            except (ConnectionAbortedError, BrokenPipeError, OSError):
                                pass
                        elif self.path == '/api/data':
                            body = json.dumps(dashboard_service.get_dashboard_data(), indent=2, default=str).encode('utf-8')
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            try:
                                self.wfile.write(body)
                            except (ConnectionAbortedError, BrokenPipeError, OSError):
                                pass
                        elif self.path.startswith('/api/history'):
                            body = json.dumps(dashboard_service.get_signal_history(hours=168), indent=2, default=str).encode('utf-8')
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            try:
                                self.wfile.write(body)
                            except (ConnectionAbortedError, BrokenPipeError, OSError):
                                pass
                        elif self.path == '/api/export':
                            csv = dashboard_service.export_signals_csv().encode('utf-8')
                            fname = f"signals_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
                            self.send_response(200)
                            self.send_header('Content-type', 'text/csv; charset=utf-8')
                            self.send_header('Content-Disposition', f'attachment; filename="{fname}"')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            try:
                                self.wfile.write(csv)
                            except (ConnectionAbortedError, BrokenPipeError, OSError):
                                pass

                        elif self.path == '/api/equity':
                            # Equity en tiempo real (paper o real)
                            body = json.dumps(dashboard_service.get_equity_snapshot(), indent=2, default=str).encode('utf-8')
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            try:
                                self.wfile.write(body)
                            except (ConnectionAbortedError, BrokenPipeError, OSError):
                                pass

                        elif self.path == '/api/execution-status':
                            status = {
                                'auto_execute': dashboard_service.auto_execute_enabled,
                                'confidence': dashboard_service.auto_execute_confidence,
                            }
                            body = json.dumps(status, default=str).encode('utf-8')
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            try:
                                self.wfile.write(body)
                            except (ConnectionAbortedError, BrokenPipeError, OSError):
                                pass

                        else:
                            self.send_response(404)
                            self.end_headers()
                    except (ConnectionAbortedError, BrokenPipeError, OSError):
                        pass  # conexión cortada por el cliente
                    except Exception as e:
                        logger.error(f"Dashboard request error: {e}")
                        try:
                            self.send_response(500)
                            self.end_headers()
                        except Exception:
                            pass

                def log_message(self, *args):
                    pass

            port = int(os.getenv('DASHBOARD_PORT', '8080'))

            try:
                self.server_instance = ReusableThreadingHTTPServer(('', port), Handler)
            except Exception as e:
                logger.error(f"Failed to bind dashboard server on port {port}: {e}")
                return

            def run():
                try:
                    if self.server_instance:
                        self.server_instance.serve_forever()
                except Exception as e:
                    logger.error(f"Dashboard server error: {e}")

            self.server_thread = threading.Thread(target=run, daemon=True)
            self.server_thread.start()
            logger.info(f"Dashboard on http://localhost:{port}")
        except Exception as e:
            logger.error(f"Error starting web server: {e}")

    def stop(self):
        try:
            with self.lock:
                if not self.is_running:
                    return
                self.is_running = False
                if self.dashboard_config['enable_persistence']:
                    self._save_persisted_data()

            if self.server_instance:
                srv = self.server_instance
                self.server_instance = None
                def _close_srv():
                    try:
                        srv.shutdown()
                        srv.server_close()
                    except Exception:
                        pass
                t = threading.Thread(target=_close_srv, daemon=True)
                t.start()
                t.join(timeout=0.5)
        except Exception as e:
            logger.error(f"Error stopping dashboard: {e}")

    def add_signal_event(self, symbol: str, strategy: str, signal_type: str,
                         confidence: str, score: float, shown: bool,
                         executed: bool = False, rejection_reason: str = None,
                         entry: float = None, sl: float = None, tp: float = None,
                         mobile_status: str = None):
        try:
            lat = None
            slip = None
            try:
                from core.journal import get_journal
                with get_journal()._conn() as conn:
                    row = conn.execute(
                        "SELECT latency_ms, slippage_pips FROM trade_journal ORDER BY id DESC LIMIT 1"
                    ).fetchone()
                    if row and row['latency_ms'] is not None:
                        lat = row['latency_ms']
                        slip = row['slippage_pips']
            except Exception:
                pass

            event = SignalEvent(
                timestamp=datetime.now(timezone.utc),
                symbol=symbol, strategy=strategy, signal_type=signal_type,
                confidence=confidence, score=score, shown=shown,
                executed=executed, rejection_reason=rejection_reason,
                entry=entry, sl=sl, tp=tp,
                latency_ms=lat, slippage_pips=slip
            )

            with self.lock:
                self.signal_history.append(event)
                self._update_signal_metrics(event)
                self.metrics.last_signal_time = event.timestamp

            # Persistir en SQLite para la app móvil (fuera del lock para no bloquear IO)
            if shown and entry and sl and tp:
                try:
                    from services.mobile_store import get_mobile_store
                    mobile_id = get_mobile_store().insert_signal(
                        symbol=symbol,
                        direction=signal_type,
                        price=float(entry),
                        tp_price=float(tp),
                        sl_price=float(sl),
                        confidence_score=float(score),
                        confidence=confidence,
                        strategy=strategy,
                        status=mobile_status or ('OPEN' if executed else 'PROPOSED'),
                    )
                    with self.lock:
                        event.mobile_signal_id = mobile_id
                except Exception as ms_err:
                    logger.debug(f"Mobile store insert_signal: {ms_err}")
        except Exception as e:
            logger.error(f"Error adding signal event: {e}")

    def update_trading_metrics(self, positions_open: int, total_profit: float, win_rate: float):
        try:
            with self.lock:
                self.metrics.positions_open = positions_open
                self.metrics.total_profit = total_profit
                self.metrics.win_rate = win_rate
                self.performance_history.append({
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'positions_open': positions_open,
                    'total_profit': total_profit,
                    'win_rate': win_rate,
                    'signals_today': self.metrics.signals_today,
                })
        except Exception as e:
            logger.error(f"Error updating trading metrics: {e}")

    def get_current_metrics(self) -> Dict:
        try:
            with self.lock:
                uptime = datetime.now(timezone.utc) - self.start_time
                self.metrics.uptime_seconds = int(uptime.total_seconds())
                return {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'uptime_seconds': self.metrics.uptime_seconds,
                    'uptime_formatted': self._format_uptime(uptime),
                    'system_status': self.metrics.system_status,
                    'signals': {
                        'today': self.metrics.signals_today,
                        'shown': self.metrics.signals_shown,
                        'executed': self.metrics.signals_executed,
                        'rejected': self.metrics.signals_rejected,
                        'show_rate': (self.metrics.signals_shown / self.metrics.signals_today * 100) if self.metrics.signals_today > 0 else 0,
                        'last_signal_time': self.metrics.last_signal_time.isoformat() if self.metrics.last_signal_time else None,
                    },
                    'symbols': {
                        'activity': dict(self.metrics.symbol_activity),
                        'performance': {k: dict(v) for k, v in self.metrics.symbol_performance.items()},
                        'active': dict(active_symbols or {}),
                    },
                    'confidence_distribution': dict(self.metrics.confidence_distribution),
                    'trading': {
                        'positions_open': self.metrics.positions_open,
                        'total_profit': self.metrics.total_profit,
                        'win_rate': self.metrics.win_rate,
                    },
                }
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {'error': str(e), 'system_status': 'ERROR',
                    'signals': {'today':0,'shown':0,'executed':0,'rejected':0,'show_rate':0,'last_signal_time':None},
                    'symbols': {'activity':{},'performance':{},'active':{}},
                    'confidence_distribution': {},
                    'trading': {'positions_open':0,'total_profit':0.0,'win_rate':0.0},
                    'uptime_formatted': '0s', 'uptime_seconds': 0,
                    'timestamp': datetime.now(timezone.utc).isoformat()}

    def get_signal_history(self, hours: int = 168, symbol: str = None,
                           session_only: bool = False) -> List[Dict]:
        try:
            with self.lock:
                history_copy = list(self.signal_history)
                session_start = self.session_start
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            if session_only:
                cutoff = max(cutoff, session_start)
            result = []
            for ev in history_copy:
                if ev.timestamp < cutoff:
                    continue
                if symbol and ev.symbol != symbol:
                    continue
                result.append({
                    'timestamp': ev.timestamp.isoformat(),
                    'symbol': ev.symbol, 'strategy': ev.strategy,
                    'signal_type': ev.signal_type, 'confidence': ev.confidence,
                    'score': ev.score, 'shown': ev.shown, 'executed': ev.executed,
                    'rejection_reason': ev.rejection_reason,
                    'entry': ev.entry, 'sl': ev.sl, 'tp': ev.tp,
                    'final_status': ev.final_status,
                    'current_price': ev.current_price,
                    'unrealized_pnl': ev.unrealized_pnl,
                })
            return result
        except Exception as e:
            logger.error(f"Error getting signal history: {e}")
            return []

    def export_signals_csv(self) -> str:
        try:
            lines = ['timestamp,symbol,direction,confidence,entry,sl,tp,rr,status,shown']
            for ev in self.get_signal_history(hours=168):
                entry = ev.get('entry'); sl = ev.get('sl'); tp = ev.get('tp')
                rr = ''
                if entry and sl and tp and abs(entry - sl) > 0:
                    rr = f"{abs(tp-entry)/abs(entry-sl):.2f}"
                status = self._get_signal_status_dict(ev)
                lines.append(
                    f"{ev['timestamp'][:16]},{ev['symbol']},{ev['signal_type']},"
                    f"{ev['confidence']},{entry or ''},{sl or ''},{tp or ''},"
                    f"{rr},{status},{'yes' if ev['shown'] else 'no'}"
                )
            return '\n'.join(lines)
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            return "error,generating,csv"

    def _get_signal_status_dict(self, ev: dict) -> str:
        try:
            import MetaTrader5 as mt5
            entry = ev.get('entry'); sl = ev.get('sl'); tp = ev.get('tp')
            sym = ev.get('symbol', ''); stype = ev.get('signal_type', 'BUY')
            if not (entry and sl and tp):
                return 'pending'
            tick = mt5.symbol_info_tick(sym)
            if not tick:
                return 'pending'
            price = (tick.bid + tick.ask) / 2
            if stype == 'BUY':
                return 'win' if price >= tp else 'loss' if price <= sl else 'open'
            else:
                return 'win' if price <= tp else 'loss' if price >= sl else 'open'
        except Exception:
            return 'pending'

    def _get_real_positions(self) -> list:
        """Fetches open MT5 positions and returns a list of dicts."""
        try:
            import MetaTrader5 as mt5
            positions = mt5.positions_get()
            if not positions:
                return []
            result = []
            for pos in positions:
                try:
                    tick = mt5.symbol_info_tick(pos.symbol)
                    current_price = (tick.bid + tick.ask) / 2 if tick else pos.price_open
                    result.append({
                        'symbol': pos.symbol,
                        'type': 'BUY' if pos.type == 0 else 'SELL',
                        'volume': pos.volume,
                        'open_price': pos.price_open,
                        'current_price': current_price,
                        'profit': pos.profit,
                        'sl': pos.sl,
                        'tp': pos.tp,
                        'ticket': pos.ticket,
                    })
                except Exception:
                    pass
            return result
        except Exception as e:
            logger.debug(f"Error getting real positions: {e}")
            return []

    def get_dashboard_data(self) -> Dict:
        """Aggregates all metric, equity, signal history, and position data for front-end updates."""
        try:
            metrics = self.get_current_metrics()
            equity = self.get_equity_snapshot()
            session_history = self.get_signal_history(hours=24, session_only=True)
            real_positions = self._get_real_positions()

            wins_n = sum(1 for e in session_history if e.get('final_status') == 'win')
            losses_n = sum(1 for e in session_history if e.get('final_status') == 'loss')
            open_n = sum(1 for e in session_history if e.get('final_status') == 'open')
            closed = wins_n + losses_n
            win_rate = (wins_n / closed * 100) if closed > 0 else 0.0

            eq_base = equity.get('base_balance', 5000.0)
            eq_floating = equity.get('floating_pnl', 0.0)
            eq_pts = [eq_base]
            risk_pct_val = float(os.getenv('MT5_RISK_PCT', '0.5')) / 100.0
            running = eq_base
            for ev in session_history:
                fs = ev.get('final_status')
                entry = ev.get('entry'); sl_v = ev.get('sl'); tp_v = ev.get('tp')
                if fs == 'win' and entry and sl_v and tp_v and abs(entry - sl_v) > 0:
                    rr = abs(tp_v - entry) / abs(entry - sl_v)
                    running += running * risk_pct_val * rr
                    eq_pts.append(round(running, 2))
                elif fs == 'loss':
                    running -= running * risk_pct_val
                    eq_pts.append(round(running, 2))
            eq_pts.append(round(running + eq_floating, 2))

            from services.bot_service import get_bot_service
            analytics = get_bot_service().get_execution_analytics().get('analytics', {})

            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metrics': metrics,
                'equity': equity,
                'session_signals': session_history,
                'real_positions': real_positions,
                'execution_analytics': analytics,
                'win_rate': {
                    'win_rate_pct': win_rate,
                    'wins': wins_n,
                    'losses': losses_n,
                    'open': open_n,
                },
                'equity_pts': eq_pts,
            }
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metrics': self.get_current_metrics(),
                'equity': self.get_equity_snapshot(),
                'session_signals': [],
                'real_positions': [],
                'win_rate': {'win_rate_pct': 0.0, 'wins': 0, 'losses': 0, 'open': 0},
                'equity_pts': [5000.0],
            }

    def get_dashboard_html(self, lang: str = 'en') -> str:
        try:
            # Apply language setting for this request
            set_language(lang)

            # ── Inline translation helper ────────────────────────────────────────
            _ui: dict = {
                "Live · updates every 30s":  {"en": "Live · updates every 30s",    "es": "En vivo · actualiza cada 30s"},
                "Connected":                  {"en": "🟢 Connected",               "es": "🟢 Conectado"},
                "No data":                    {"en": "— No data",                  "es": "— Sin datos"},
                "Status":                     {"en": "Status",                     "es": "Estado"},
                "Signals (session)":          {"en": "Signals (session)",          "es": "Señales (sesión)"},
                "Open positions":             {"en": "Open positions",             "es": "Posiciones abiertas"},
                "Total profit":               {"en": "Total profit",               "es": "Profit total"},
                "MT5 account":                {"en": "MT5 account",                "es": "Cuenta MT5"},
                "Equity MT5 (real-time)":     {"en": "Equity MT5 (real-time)",     "es": "Equity MT5 (tiempo real)"},
                "Base":                       {"en": "Base",                       "es": "Base"},
                "Closed":                     {"en": "Closed",                     "es": "Cerradas"},
                "Floating":                   {"en": "Floating",                   "es": "Flotante"},
                "open":                       {"en": "open",                       "es": "abiertas"},
                "Session winrate":            {"en": "Session winrate",            "es": "Winrate sesión"},
                "wins":                       {"en": "wins",                       "es": "wins"},
                "losses":                     {"en": "losses",                     "es": "losses"},
                "open pos":                   {"en": "open",                       "es": "abiertas"},
                "Export signals (7 days)":    {"en": "Export signals (7 days)",    "es": "Exportar señales (7 días)"},
                "Download CSV":               {"en": "⬇ Download CSV",             "es": "⬇ Descargar CSV"},
                "signals in history":         {"en": "signals in history",         "es": "señales en historial"},
                "Equity Curve — closed + current floating": {
                    "en": "Equity Curve — Closed + Current Floating",
                    "es": "Curva de Equity — Cerradas + Flotante Actual",
                },
                "Open Positions in MT5":      {"en": "Open Positions in MT5",      "es": "Posiciones Abiertas en MT5"},
                "Pair":                       {"en": "Pair",                       "es": "Par"},
                "Dir":                        {"en": "Dir",                        "es": "Dir"},
                "Volume":                     {"en": "Volume",                     "es": "Volumen"},
                "Open price":                 {"en": "Open price",                 "es": "Precio apertura"},
                "Current price":              {"en": "Current price",              "es": "Precio actual"},
                "Circuit Breaker":            {"en": "Circuit Breaker",            "es": "Circuit Breaker"},
                "ACTIVE":                     {"en": "ACTIVE",                     "es": "ACTIVO"},
                "PAUSED":                     {"en": "PAUSED",                     "es": "PAUSADO"},
                "Losses":                     {"en": "Losses",                     "es": "Pérdidas"},
                "Wins":                       {"en": "Wins",                       "es": "Wins"},
                "Risk":                       {"en": "Risk",                       "es": "Riesgo"},
                "Monitored Pairs":            {"en": "Monitored Pairs",            "es": "Pares Monitoreados"},
                "Total":                      {"en": "Total",                      "es": "Total"},
                "Shown":                      {"en": "Shown",                      "es": "Mostradas"},
                "Score avg":                  {"en": "Score avg",                  "es": "Score avg"},
                "Last":                       {"en": "Last",                       "es": "Última"},
                "Execution Quality":          {"en": "Execution Quality",          "es": "Calidad de Ejecución"},
                "Success Rate":               {"en": "Success Rate",               "es": "Tasa de éxito"},
                "Executed":                   {"en": "Executed",                   "es": "Ejecutadas"},
                "Rejected":                   {"en": "Rejected",                   "es": "Rechazadas"},
                "Avg Latency":                {"en": "Avg Latency",                "es": "Latencia media"},
                "Max Latency":                {"en": "Max Latency",                "es": "Latencia máx"},
                "Avg Slippage":               {"en": "Avg Slippage",               "es": "Slippage medio"},
                "Max Slippage":               {"en": "Max Slippage",               "es": "Slippage máx"},
                "Session signals (real-time P&L)": {
                    "en": "Session signals (real-time P&L)",
                    "es": "Señales de esta sesión (P&L en tiempo real)",
                },
                "Time":                       {"en": "Time",                       "es": "Hora"},
                "Confidence":                 {"en": "Confidence",                 "es": "Confianza"},
                "Latency":                    {"en": "Latency",                    "es": "Latencia"},
                "Slippage":                   {"en": "Slippage",                   "es": "Slippage"},
                "Status_col":                 {"en": "Status",                     "es": "Estado"},
                "Sent":                       {"en": "Sent",                       "es": "Enviada"},
                "No signals in this session": {"en": "No signals in this session yet", "es": "Sin señales en esta sesión aún"},
                "Auto-execution active":      {"en": "✅ Auto-execution MT5 active",  "es": "✅ Auto-ejecución MT5 activa"},
                "Auto-execution disabled":    {"en": "⏸ Auto-execution disabled (AUTO_EXECUTE_SIGNALS=0)", "es": "⏸ Auto-ejecución desactivada (AUTO_EXECUTE_SIGNALS=0)"},
                "min without data":           {"en": "min without data",           "es": "min sin datos"},
                "Uptime":                     {"en": "Uptime",                     "es": "Uptime"},
                "Last signal":                {"en": "Last signal",                "es": "Última señal"},
                "Shown_count":                {"en": "Shown",                      "es": "Mostradas"},
                "Start":                      {"en": "Start",                      "es": "Inicio"},
            }

            def t(key: str) -> str:
                entry = _ui.get(key, {})
                return entry.get(lang, entry.get("en", key))

            metrics   = self.get_current_metrics()
            history   = self.get_signal_history(hours=168)          # para CSV/export
            session_history = self.get_signal_history(hours=24, session_only=True)  # solo sesión actual para tabla
            cb_status = {}
            try:
                from core.circuit_breaker import get_circuit_breaker
                cb_status = get_circuit_breaker().get_status()
            except Exception:
                pass

            # Precios actuales MT5
            current_prices: dict = {}
            try:
                import MetaTrader5 as mt5
                for sym in ('EURUSD', 'XAUUSD', 'BTCEUR'):
                    tick = mt5.symbol_info_tick(sym)
                    if tick:
                        current_prices[sym] = (tick.bid + tick.ask) / 2
                with self.lock:
                    self.last_mt5_update = datetime.now(timezone.utc)
            except Exception:
                pass

            def sig_status(ev):
                entry = ev.get('entry'); sl = ev.get('sl'); tp = ev.get('tp')
                sym = ev.get('symbol', ''); stype = ev.get('signal_type', 'BUY')
                price = current_prices.get(sym)
                if not (entry and sl and tp and price):
                    return 'pending'
                if stype == 'BUY':
                    return 'win' if price >= tp else 'loss' if price <= sl else 'open'
                else:
                    return 'win' if price <= tp else 'loss' if price >= sl else 'open'

            # ── Equity en tiempo real ─────────────────────────────────────
            eq_snap      = self.get_equity_snapshot()
            eq_mode      = eq_snap['mode']
            eq_balance   = eq_snap['balance']          # cerradas acumuladas
            eq_floating  = eq_snap['floating_pnl']     # abiertas ahora
            eq_total     = eq_snap['total_equity']     # lo que se muestra
            eq_change    = eq_snap['change']
            eq_pct       = eq_snap['change_pct']
            eq_base      = eq_snap['base_balance']
            eq_color     = '#3fb950' if eq_change >= 0 else '#f85149'
            float_color  = '#3fb950' if eq_floating >= 0 else '#f85149'
            float_sign   = '+' if eq_floating >= 0 else ''
            change_sign  = '+' if eq_change >= 0 else ''

            # Winrate (señales cerradas de la sesión)
            wins_n = sum(1 for e in session_history if e.get('final_status') == 'win')
            losses_n = sum(1 for e in session_history if e.get('final_status') == 'loss')
            open_n   = sum(1 for e in session_history if e.get('final_status') == 'open')
            closed   = wins_n + losses_n
            wr_pct   = wins_n / closed * 100 if closed > 0 else 0
            wr_color = '#3fb950' if wr_pct >= 50 else '#d29922' if wr_pct >= 40 else '#f85149'

            # Puntos para el gráfico: balance paper acumulado tras cada señal cerrada
            eq_pts = [eq_base]
            risk_pct_val = float(os.getenv('MT5_RISK_PCT', '0.5')) / 100.0
            running = eq_base
            for ev in session_history:
                fs = ev.get('final_status')
                entry = ev.get('entry'); sl_v = ev.get('sl'); tp_v = ev.get('tp')
                if fs == 'win' and entry and sl_v and tp_v and abs(entry - sl_v) > 0:
                    rr = abs(tp_v - entry) / abs(entry - sl_v)
                    running += running * risk_pct_val * rr
                    eq_pts.append(round(running, 2))
                elif fs == 'loss':
                    running -= running * risk_pct_val
                    eq_pts.append(round(running, 2))
            # Añadir punto final con flotante incluido
            eq_pts.append(round(running + eq_floating, 2))
            eq_pts_json = json.dumps(eq_pts)

            with self.lock:
                last_mt5_update = self.last_mt5_update

            if last_mt5_update:
                d = (datetime.now(timezone.utc) - last_mt5_update).total_seconds()
                mt5_ind = t("Connected") if d < 120 else (f'🟡 {int(d//60)}m {t("min without data")}' if d < 300 else f'🔴 {int(d//60)}m {t("min without data")}')
                mt5_col = '#3fb950' if d < 120 else '#d29922' if d < 300 else '#f85149'
            else:
                mt5_ind = t("No data"); mt5_col = '#8b949e'

            status_map = {
                'win':     '<span style="color:#3fb950;font-weight:600">WIN ✅</span>',
                'loss':    '<span style="color:#f85149;font-weight:600">LOSS ❌</span>',
                'open':    '<span style="color:#d29922">OPEN ⏳</span>',
                'pending': '<span style="color:#8b949e">—</span>',
            }

            recent_rows = ""
            for ev in reversed(session_history[-50:]):
                ts = ev['timestamp'][:16].replace('T', ' ')
                sym = ev['symbol']; stype = ev['signal_type']; conf = ev['confidence']
                shown = "✅" if ev['shown'] else "—"
                cc = {'HIGH':'conf-high','VERY_HIGH':'conf-high','MEDIUM-HIGH':'conf-med-high','MEDIUM':'conf-med'}.get(conf,'conf-low')
                dc = 'dir-buy' if stype == 'BUY' else 'dir-sell'
                entry = ev.get('entry'); sl = ev.get('sl'); tp = ev.get('tp')
                if sym == 'EURUSD':   fmt = lambda v: f"{v:.5f}" if v is not None else "—"
                elif sym == 'XAUUSD': fmt = lambda v: f"{v:.2f}"  if v is not None else "—"
                else:                 fmt = lambda v: f"{v:.0f}"   if v is not None else "—"
                rr_str = (f"{abs(tp-entry)/abs(entry-sl):.1f}" if entry and sl and tp and abs(entry-sl)>0 else "—")

                # Estado persistente — usa final_status guardado, no recalcula
                fs = ev.get('final_status')
                if fs == 'win':
                    st_html = '<span style="color:#3fb950;font-weight:600">WIN ✅</span>'
                elif fs == 'loss':
                    st_html = '<span style="color:#f85149;font-weight:600">LOSS ❌</span>'
                elif fs == 'open':
                    # Mostrar P&L en tiempo real para posiciones abiertas
                    pnl = ev.get('unrealized_pnl')
                    cur = ev.get('current_price')
                    if pnl is not None and cur is not None:
                        pnl_color = '#3fb950' if pnl >= 0 else '#f85149'
                        pnl_sign  = '+' if pnl >= 0 else ''
                        st_html = (f'<span style="color:{pnl_color}">OPEN '
                                   f'{pnl_sign}{pnl:.0f}%</span>')
                    else:
                        st_html = '<span style="color:#d29922">OPEN ⏳</span>'
                else:
                    st_html = '<span style="color:#8b949e">—</span>'

                lat_val = ev.get('latency_ms')
                slip_val = ev.get('slippage_pips')
                lat_str = f"{lat_val} ms" if lat_val is not None else "—"
                slip_str = f"{slip_val:.1f} pips" if slip_val is not None else "—"

                recent_rows += (f'<tr><td>{ts}</td><td class="sym">{sym}</td>'
                                 f'<td class="{dc}">{stype}</td><td class="{cc}">{conf}</td>'
                                 f'<td>{fmt(entry)}</td><td style="color:var(--red)">{fmt(sl)}</td>'
                                 f'<td style="color:var(--green)">{fmt(tp)}</td>'
                                 f'<td>{rr_str}</td>'
                                 f'<td>{lat_str}</td>'
                                 f'<td>{slip_str}</td>'
                                 f'<td>{st_html}</td><td>{shown}</td></tr>\n')
            if not recent_rows:
                recent_rows = f'<tr><td colspan="12" class="empty">{t("No signals in this session")}</td></tr>'

            sig = metrics.get('signals', {}); trd = metrics.get('trading', {})
            sp  = metrics.get('symbols', {}).get('performance', {})
            s_today = sig.get('today', 0); s_shown = len(session_history)
            s_rate  = f"{sig.get('show_rate',0):.0f}%"
            pos_open = trd.get('positions_open', 0); t_profit = trd.get('total_profit', 0.0)
            p_color = '#3fb950' if t_profit >= 0 else '#f85149'
            uptime  = metrics.get('uptime_formatted', '—'); sys_st = metrics.get('system_status', 'RUNNING')
            ls = sig.get('last_signal_time', ''); ls_fmt = ls[:16].replace('T',' ') if ls else '—'
            cb_ok = cb_status.get('can_trade', True); cb_l = cb_status.get('consecutive_losses', 0)
            cb_w  = cb_status.get('consecutive_wins', 0); cb_m = cb_status.get('risk_multiplier', 1.0)
            cb_lbl = t("ACTIVE") if cb_ok else t("PAUSED"); cb_rsn = cb_status.get('reason', '')

            # Real MT5 positions
            real_positions = self._get_real_positions()
            real_pos_rows = ""
            for rp in real_positions:
                pnl_color = '#3fb950' if rp['profit'] >= 0 else '#f85149'
                pnl_sign = '+' if rp['profit'] >= 0 else ''
                type_cls = 'dir-buy' if rp['type'] == 'BUY' else 'dir-sell'
                sl_str = f"{rp['sl']:.5f}" if rp['sl'] else '—'
                tp_str = f"{rp['tp']:.5f}" if rp['tp'] else '—'
                real_pos_rows += (
                    f'<tr><td class="sym">{rp["symbol"]}</td>'
                    f'<td class="{type_cls}">{rp["type"]}</td>'
                    f'<td>{rp["volume"]:.2f}</td>'
                    f'<td>{rp["open_price"]:.5f}</td>'
                    f'<td>{rp["current_price"]:.5f}</td>'
                    f'<td style="color:{pnl_color};font-weight:600">{pnl_sign}{rp["profit"]:.2f} €</td>'
                    f'<td style="color:var(--red)">{sl_str}</td>'
                    f'<td style="color:var(--green)">{tp_str}</td></tr>\n'
                )
            real_positions_section = ""
            if real_positions:
                real_positions_section = f"""
<div class="card" id="real-positions-section" style="margin-bottom:20px">
  <div class="section-title">{t("Open Positions in MT5")}</div>
  <table>
    <thead><tr><th>{t("Pair")}</th><th>{t("Dir")}</th><th>{t("Volume")}</th><th>{t("Open price")}</th><th>{t("Current price")}</th><th>P&amp;L</th><th style="color:var(--red)">SL</th><th style="color:var(--green)">TP</th></tr></thead>
    <tbody>{real_pos_rows}</tbody>
  </table>
</div>"""
            def sym_row(sym):
                perf = sp.get(sym, {}); tot = perf.get('total_signals',0); shw = perf.get('shown_signals',0)
                avg  = perf.get('avg_confidence_score', 0.0)
                h = (symbol_health or {}).get(sym, {}); lt = h.get('last_signal_time')
                nu = datetime.now(timezone.utc)
                if lt:
                    t_val = lt if lt.tzinfo else lt.replace(tzinfo=timezone.utc)
                    d = (nu-t_val).total_seconds()
                    ltxt = "<1 min" if d<60 else f"{int(d//60)}m" if d<3600 else f"{int(d//3600)}h {int((d%3600)//60)}m"
                    inact = d > 5400
                else:
                    ltxt = "—"; inact = True
                dot = '🔴' if h.get('status') in ('ERROR','DISABLED') else ('🟡' if inact else '🟢')
                return (f'<tr><td class="sym">{sym}</td><td>{dot}</td>'
                        f'<td>{tot}</td><td>{shw}</td><td>{avg:.2f}</td><td>{ltxt}</td></tr>')

            sym_rows = sym_row('EURUSD') + sym_row('XAUUSD') + sym_row('BTCEUR')
            port = os.getenv('DASHBOARD_PORT', '8080')
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Execution Quality Stats (P1.1)
            eq_stats_html = ""
            try:
                from core.journal import get_journal
                eq_data = get_journal().get_execution_quality_summary(days=30)
                
                tot_orders = eq_data.get('total_orders', 0)
                rej_rate = eq_data.get('rejection_rate_pct', 0.0)
                avg_lat = eq_data.get('avg_latency_ms', 0.0)
                max_lat = eq_data.get('max_latency_ms', 0)
                avg_slip = eq_data.get('avg_slippage_pips', 0.0)
                avg_sprd = eq_data.get('avg_spread_pips', 0.0)
                fav_slip_pct = eq_data.get('favorable_slippage_pct', 0.0)
                slip_cost_eur = eq_data.get('total_slippage_cost_eur', 0.0)
                
                eq_stats_html = f"""
                <div class="card">
                  <div class="section-title">{t("Execution Quality")}</div>
                  <div class="cb-bar" style="margin-bottom:12px; gap: 10px;">
                    <div class="cb-stat">{t("Total Orders")}: <span>{tot_orders}</span></div>
                    <div class="cb-stat">{t("Rejection Rate")}: <span style="color:{'var(--red)' if rej_rate > 3.0 else 'var(--green)'}">{rej_rate:.1f}%</span></div>
                    <div class="cb-stat">{t("Avg Spread")}: <span style="color:var(--yellow)">{avg_sprd:.1f} p</span></div>
                  </div>
                  <div class="cb-bar" style="gap: 10px;">
                    <div class="cb-stat">{t("Avg Latency")}: <span style="color:var(--blue)">{avg_lat:.0f} ms</span></div>
                    <div class="cb-stat">{t("Max Latency")}: <span>{max_lat:.0f} ms</span></div>
                  </div>
                  <div class="cb-bar" style="margin-top:4px; gap: 10px;">
                    <div class="cb-stat">{t("Avg Slippage")}: <span style="color:{'var(--red)' if avg_slip > 0 else 'var(--green)'}">{avg_slip:+.2f} p</span></div>
                    <div class="cb-stat">{t("Slippage Cost")}: <span style="color:var(--yellow)">{slip_cost_eur:+.2f} €</span></div>
                    <div class="cb-stat">{t("Price Improvement")}: <span style="color:var(--green)">{fav_slip_pct:.1f}%</span></div>
                  </div>
                </div>
                """
            except Exception as e:
                logger.error(f"Error generating Execution Quality html: {e}")

            lang_en_active = 'lang-active' if lang == 'en' else ''
            lang_es_active = 'lang-active' if lang == 'es' else ''
            live_str = t('Live · updates every 30s')
            cb_ok_cls = 'cb-ok' if cb_ok else 'cb-stop'
            cb_rsn_html = f'<span style="color:var(--red);font-size:11px">{cb_rsn}</span>' if not cb_ok else ''
            loss_col = 'var(--red)' if cb_l > 0 else 'var(--text)'
            win_col = 'var(--green)' if cb_w > 0 else 'var(--text)'
            risk_col = 'var(--yellow)' if cb_m != 1.0 else 'var(--text)'
            exec_active_text = t('Auto-execution active') if self.auto_execute_enabled else t('Auto-execution disabled')
            new_sig_title = t("New signal detected")
            new_sig_body_suffix = t("new signal(s) from LastEdge.")
            port_label = "Port" if lang == "en" else "Puerto"
            no_signals_msg = t("No signals in this session")

            return f"""<!DOCTYPE html>
<html lang="{lang}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LastEdge — Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{{--bg:#0d1117;--surface:#161b22;--border:#30363d;--text:#e6edf3;--muted:#8b949e;--blue:#58a6ff;--green:#3fb950;--yellow:#d29922;--red:#f85149;--purple:#a371f7}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:14px}}
a{{color:var(--blue);text-decoration:none}}
.page{{max-width:1150px;margin:0 auto;padding:24px 16px}}
.topbar{{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px}}
.topbar h1{{font-size:18px;font-weight:600}}.topbar .meta{{font-size:12px;color:var(--muted);text-align:right}}
.grid-4{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}}
.grid-3{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px}}
@media(max-width:700px){{.grid-4,.grid-3{{grid-template-columns:repeat(2,1fr)}}.grid-2{{grid-template-columns:1fr}}}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px}}
.card-title{{font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);margin-bottom:8px}}
.card-value{{font-size:28px;font-weight:700;line-height:1}}.card-sub{{font-size:12px;color:var(--muted);margin-top:4px}}
.section-title{{font-size:13px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin-bottom:10px}}
.chart-container-full {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 20px; }}
table{{width:100%;border-collapse:collapse}}
th{{font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);padding:6px 10px;border-bottom:1px solid var(--border);text-align:left}}
td{{padding:7px 10px;border-bottom:1px solid rgba(48,54,61,.5);font-size:12px}}
tr:last-child td{{border-bottom:none}}tr:hover td{{background:rgba(88,166,255,.04)}}
.empty{{color:var(--muted);text-align:center;padding:20px}}
.sym{{font-weight:600;color:var(--blue)}}.dir-buy{{color:var(--green);font-weight:600}}.dir-sell{{color:var(--red);font-weight:600}}
.conf-high{{color:var(--green)}}.conf-med-high{{color:var(--blue)}}.conf-med{{color:var(--yellow)}}.conf-low{{color:var(--red)}}
.cb-bar{{display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
.cb-pill{{padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600}}
.cb-ok{{background:rgba(63,185,80,.15);color:var(--green)}}.cb-stop{{background:rgba(248,81,73,.15);color:var(--red)}}
.cb-stat{{font-size:12px;color:var(--muted)}}.cb-stat span{{color:var(--text);font-weight:600}}
.export-btn{{background:var(--blue);color:#0d1117;border:none;padding:5px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block}}
.footer{{margin-top:24px;font-size:11px;color:var(--muted);display:flex;justify-content:space-between;flex-wrap:wrap;gap:4px}}
.dot-live{{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--green);margin-right:5px;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
.filter-bar{{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}}
.filter-btn{{background:var(--surface);border:1px solid var(--border);color:var(--muted);padding:4px 12px;border-radius:20px;font-size:12px;cursor:pointer;transition:all .15s}}
.filter-btn.active{{background:var(--blue);color:#0d1117;border-color:var(--blue);font-weight:600}}
.lang-bar{{display:flex;gap:4px;margin-bottom:4px;justify-content:flex-end}}
.lang-btn{{display:inline-block;padding:2px 6px;border-radius:4px;font-size:16px;text-decoration:none;opacity:0.4;transition:opacity .15s}}
.lang-btn:hover{{opacity:0.8}}
.lang-btn.lang-active{{opacity:1.0;background:rgba(88,166,255,.15)}}
</style></head>
<body><div class="page">
<div class="topbar">
  <h1>⚡ LastEdge <span style="color:var(--muted);font-weight:400">/ Dashboard</span></h1>
  <div class="meta">
    <div class="lang-bar">
      <a href="/api/set-language?lang=en&redirect=/" title="English" class="lang-btn {lang_en_active}">🇬🇧</a>
      <a href="/api/set-language?lang=es&redirect=/" title="Español" class="lang-btn {lang_es_active}">🇪🇸</a>
    </div>
    <div><span class="dot-live"></span>{live_str}</div>
    <div>{now_str}</div>
    <div style="color:{mt5_col}">{mt5_ind}</div>
  </div>
</div>

<div class="grid-4">
  <div class="card"><div class="card-title">{t("Status")}</div><div class="card-value" id="stat-sys-status" style="font-size:18px;color:var(--green)">{sys_st}</div><div class="card-sub" id="stat-uptime">{t("Uptime")}: {uptime}</div></div>
  <div class="card"><div class="card-title">{t("Signals (session)")}</div><div class="card-value" id="stat-signals-today" style="color:var(--blue)">{s_today}</div><div class="card-sub" id="stat-signals-shown">{t("Shown_count")}: {s_shown} ({s_rate})</div></div>
  <div class="card"><div class="card-title">{t("Open positions")}</div><div class="card-value" id="stat-pos-open" style="color:var(--purple)">{pos_open}</div><div class="card-sub" id="stat-last-signal">{t("Last signal")}: {ls_fmt}</div></div>
  <div class="card"><div class="card-title">{t("Total profit")}</div><div class="card-value" id="stat-total-profit" style="color:{p_color}">{t_profit:+.2f} €</div><div class="card-sub">{t("MT5 account")}</div></div>
</div>

<div class="grid-3">
  <div class="card" id="equity-card">
    <div class="card-title">{t("Equity MT5 (real-time)")}</div>
    <div style="display:flex;align-items:baseline;gap:10px">
      <span class="card-value" id="eq-total" style="color:{eq_color}">{eq_total:,.2f} €</span>
      <span style="font-size:13px;color:{eq_color}" id="eq-pct">{change_sign}{eq_pct:.2f}%</span>
    </div>
    <div class="card-sub" style="margin-top:6px">
      {t("Base")}: {eq_base:,.2f} € &nbsp;·&nbsp;
      {t("Closed")}: <span style="color:{eq_color}" id="eq-closed">{change_sign}{eq_change:+.2f} €</span>
    </div>
    <div class="card-sub" style="margin-top:2px">
      {t("Floating")}: <span id="eq-float" style="color:{float_color}">{float_sign}{eq_floating:+.2f} €</span>
      &nbsp;<span style="color:var(--muted);font-size:11px" id="eq-open-count">({open_n} {t("open")})</span>
    </div>
  </div>
  <div class="card">
    <div class="card-title">{t("Session winrate")}</div>
    <div class="card-value" id="stat-winrate" style="color:{wr_color}">{wr_pct:.0f}%</div>
    <div class="card-sub" id="stat-winrate-sub">✅ {wins_n} {t("wins")} · ❌ {losses_n} {t("losses")} · ⏳ {open_n} {t("open pos")}</div>
  </div>
  <div class="card">
    <div class="card-title">{t("Export signals (7 days)")}</div>
    <div style="margin-top:8px"><a href="/api/export" class="export-btn" download>{t("Download CSV")}</a></div>
    <div class="card-sub" style="margin-top:8px">{len(history)} {t("signals in history")}</div>
  </div>
</div>

<div class="chart-container-full">
  <div class="section-title" style="margin-bottom:12px">{t("Equity Curve — closed + current floating")}</div>
  <canvas id="equityChart" height="80"></canvas>
</div>

{real_positions_section}
<div class="grid-3">
  <div class="card">
    <div class="section-title">{t("Circuit Breaker")}</div>
    <div class="cb-bar" style="margin-bottom:12px">
      <span class="cb-pill {cb_ok_cls}">{cb_lbl}</span>
      {cb_rsn_html}
    </div>
    <div class="cb-bar">
      <div class="cb-stat">{t("Losses")}: <span style="color:{loss_col}">{cb_l}</span></div>
      <div class="cb-stat">{t("Wins")}: <span style="color:{win_col}">{cb_w}</span></div>
      <div class="cb-stat">{t("Risk")} ×<span style="color:{risk_col}">{cb_m:.1f}</span></div>
    </div>
  </div>
  <div class="card">
    <div class="section-title">{t("Monitored Pairs")}</div>
    <table><thead><tr><th>{t("Pair")}</th><th></th><th>{t("Total")}</th><th>{t("Shown")}</th><th>{t("Score avg")}</th><th>{t("Last")}</th></tr></thead>
    <tbody>{sym_rows}</tbody></table>
  </div>
  {eq_stats_html}
</div>

<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <div class="section-title" style="margin-bottom:0">{t("Session signals (real-time P&L)")}</div>
    <a href="/api/export" class="export-btn" download>⬇ CSV</a>
  </div>
  <div class="filter-bar">
    <button class="filter-btn active" onclick="filterSignals('ALL')">ALL</button>
    <button class="filter-btn" onclick="filterSignals('EURUSD')">EURUSD</button>
    <button class="filter-btn" onclick="filterSignals('XAUUSD')">XAUUSD</button>
    <button class="filter-btn" onclick="filterSignals('BTCEUR')">BTCEUR</button>
  </div>
  <table id="signals-table">
    <thead><tr><th>{t("Time")}</th><th>{t("Pair")}</th><th>{t("Dir")}</th><th>{t("Confidence")}</th><th>Entry</th><th style="color:var(--red)">SL</th><th style="color:var(--green)">TP</th><th>R:R</th><th>{t("Latency")}</th><th>{t("Slippage")}</th><th>{t("Status_col")}</th><th>{t("Sent")}</th></tr></thead>
    <tbody>{recent_rows}</tbody>
  </table>
</div>

<!-- ⚡ Execution Explorer & Observability Card (P4 Observability) -->
<div class="card" style="margin-top:20px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
    <div class="section-title" style="margin-bottom:0">⚡ Execution Explorer &amp; Broker Quality (P4 Observability)</div>
    <div id="p4-score-badge" style="background:rgba(63,185,80,0.15);border:1px solid #3fb950;color:#3fb950;padding:6px 14px;border-radius:20px;font-weight:700;font-size:13px">
      Broker Quality: <span id="p4-score-val">100.0</span> / 100
    </div>
  </div>

  <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(160px, 1fr));gap:12px;margin-bottom:16px">
    <div style="background:var(--bg);border:1px solid var(--border);padding:12px;border-radius:8px">
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Fill Rate</div>
      <div id="p4-fill-rate" style="font-size:16px;font-weight:700;color:var(--green)">100.0%</div>
    </div>
    <div style="background:var(--bg);border:1px solid var(--border);padding:12px;border-radius:8px">
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Avg Latency</div>
      <div id="p4-avg-lat" style="font-size:16px;font-weight:700;color:var(--text)">0 ms</div>
    </div>
    <div style="background:var(--bg);border:1px solid var(--border);padding:12px;border-radius:8px">
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Avg Slippage</div>
      <div id="p4-avg-slip" style="font-size:16px;font-weight:700;color:var(--text)">0.000 pips</div>
    </div>
    <div style="background:var(--bg);border:1px solid var(--border);padding:12px;border-radius:8px">
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Slippage Impact</div>
      <div id="p4-slip-cost" style="font-size:16px;font-weight:700;color:var(--green)">0.00 €</div>
    </div>
  </div>

  <!-- Controles de Filtros e Interactividad del Execution Explorer -->
  <div class="filter-bar" style="gap:10px;align-items:center;margin-bottom:12px">
    <input type="text" id="p4-search" placeholder="Buscar por ticket, estrategia o estado..." oninput="loadP4ExecutionExplorer()" style="flex:1;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:6px 12px;border-radius:6px;font-size:12px">
    <select id="p4-symbol" onchange="loadP4ExecutionExplorer()" style="background:var(--surface);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:6px;font-size:12px">
      <option value="">Todos los Símbolos</option>
      <option value="EURUSD">EURUSD</option>
      <option value="XAUUSD">XAUUSD</option>
      <option value="BTCEUR">BTCEUR</option>
    </select>
    <select id="p4-days" onchange="loadP4ExecutionExplorer()" style="background:var(--surface);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:6px;font-size:12px">
      <option value="30">Últimos 30 Días</option>
      <option value="7">Últimos 7 Días</option>
      <option value="90">Últimos 90 Días</option>
    </select>
    <button onclick="loadP4ExecutionExplorer()" style="background:var(--primary);color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:11px;cursor:pointer">🔄 Refresh</button>
  </div>

  <!-- Tabla Interactiva del Explorer -->
  <table id="p4-explorer-table">
    <thead>
      <tr>
        <th>Fecha / Hora</th>
        <th>Símbolo</th>
        <th>Estrategia</th>
        <th>Dirección</th>
        <th>Latencia (ms)</th>
        <th>Slippage (pips)</th>
        <th>MT5 Retcode</th>
        <th>Estado</th>
      </tr>
    </thead>
    <tbody id="p4-explorer-tbody">
      <tr><td colspan="8" class="empty">Cargando telemetría de ejecución...</td></tr>
    </tbody>
  </table>
</div>

<!-- 🔬 Research Database Explorer Card -->
<div class="card" style="margin-top:20px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <div class="section-title" style="margin-bottom:0">🔬 Research Database (Trazabilidad &amp; Experimentos)</div>
    <div style="display:flex;gap:8px">
      <button class="export-btn" onclick="openNewRdModal()">➕ Nueva Investigación</button>
      <button class="export-btn" style="background:var(--surface);border:1px solid var(--border);color:var(--text)" onclick="loadResearchExperiments()">🔄 Actualizar BD</button>
    </div>
  </div>
  <div class="filter-bar" style="gap:10px;align-items:center">
    <input type="text" id="rd-search" placeholder="Buscar por hipótesis, notas, etiquetas o ID..." oninput="loadResearchExperiments()" style="flex:1;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:6px 12px;border-radius:6px;font-size:12px">
    <select id="rd-symbol" onchange="loadResearchExperiments()" style="background:var(--surface);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:6px;font-size:12px">
      <option value="">Todos los Símbolos</option>
      <option value="EURUSD">EURUSD</option>
      <option value="XAUUSD">XAUUSD</option>
      <option value="BTCEUR">BTCEUR</option>
    </select>
    <select id="rd-status" onchange="loadResearchExperiments()" style="background:var(--surface);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:6px;font-size:12px">
      <option value="">Todos los Dictámenes</option>
      <option value="PROMOTED">PROMOTED</option>
      <option value="CANDIDATE">CANDIDATE</option>
      <option value="REJECTED">REJECTED</option>
      <option value="DRAFT">DRAFT</option>
      <option value="ARCHIVED">ARCHIVED</option>
    </select>
    <button onclick="resetRdFilters()" style="background:var(--bg);border:1px solid var(--border);color:var(--muted);padding:6px 10px;border-radius:6px;font-size:11px;cursor:pointer">✖ Reset</button>
  </div>
  <table id="research-table">
    <thead>
      <tr>
        <th>ID / Título</th>
        <th>Símbolo</th>
        <th>Estrategia</th>
        <th>PF (Ganador)</th>
        <th>Stability</th>
        <th>Git Commit</th>
        <th>Dictamen</th>
        <th>Acciones</th>
      </tr>
    </thead>
    <tbody id="research-tbody">
      <tr><td colspan="8" class="empty">Cargando base de datos de investigación...</td></tr>
    </tbody>
  </table>
</div>

<!-- Modal Ficha / Edición Dictamen Research -->
<div id="rd-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:9999;align-items:center;justify-content:center">
  <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;width:90%;max-width:700px;max-height:90vh;overflow-y:auto;padding:24px;position:relative">
    <button onclick="closeRdModal()" style="position:absolute;top:16px;right:16px;background:none;border:none;color:var(--muted);font-size:18px;cursor:pointer">✖</button>
    <h2 id="rd-modal-title" style="font-size:18px;margin-bottom:6px">Ficha de Investigación</h2>
    <div id="rd-modal-meta" style="font-size:12px;color:var(--muted);margin-bottom:16px"></div>
    
    <div style="margin-bottom:16px;background:var(--bg);padding:12px;border-radius:6px;border:1px solid var(--border)">
      <div style="font-size:11px;color:var(--muted);text-transform:uppercase;margin-bottom:4px">💡 Hipótesis de Investigación</div>
      <div id="rd-modal-hypothesis" style="font-size:13px;line-height:1.4"></div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px">
      <div style="background:var(--bg);padding:10px;border-radius:6px;text-align:center"><div style="font-size:10px;color:var(--muted)">PF</div><div id="rd-m-pf" style="font-size:16px;font-weight:700;color:var(--green)">—</div></div>
      <div style="background:var(--bg);padding:10px;border-radius:6px;text-align:center"><div style="font-size:10px;color:var(--muted)">Win Rate</div><div id="rd-m-wr" style="font-size:16px;font-weight:700;color:var(--blue)">—</div></div>
      <div style="background:var(--bg);padding:10px;border-radius:6px;text-align:center"><div style="font-size:10px;color:var(--muted)">Stability</div><div id="rd-m-stab" style="font-size:16px;font-weight:700;color:var(--purple)">—</div></div>
      <div style="background:var(--bg);padding:10px;border-radius:6px;text-align:center"><div style="font-size:10px;color:var(--muted)">Max DD</div><div id="rd-m-dd" style="font-size:16px;font-weight:700;color:var(--yellow)">—</div></div>
    </div>

    <div style="margin-bottom:16px">
      <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px">Dictamen Científico:</label>
      <select id="rd-edit-status" style="width:100%;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:8px;border-radius:6px;font-size:13px;margin-bottom:10px">
        <option value="DRAFT">DRAFT</option>
        <option value="CANDIDATE">CANDIDATE</option>
        <option value="PROMOTED">PROMOTED</option>
        <option value="REJECTED">REJECTED</option>
        <option value="ARCHIVED">ARCHIVED</option>
      </select>

      <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px">Notas / Justificación de la decisión:</label>
      <textarea id="rd-edit-notes" rows="4" style="width:100%;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:10px;border-radius:6px;font-size:12px;font-family:inherit"></textarea>
    </div>

    <div style="display:flex;justify-content:space-between;align-items:center">
      <button onclick="reopenExperimentFromModal()" class="export-btn" style="background:var(--purple)">🔄 Reabrir (Usar config_json)</button>
      <div style="display:flex;gap:10px">
        <button onclick="closeRdModal()" style="background:var(--bg);border:1px solid var(--border);color:var(--text);padding:6px 14px;border-radius:6px;cursor:pointer">Cancelar</button>
        <button onclick="saveRdDecision()" class="export-btn">💾 Guardar Dictamen</button>
      </div>
    </div>
  </div>
</div>

<!-- Modal Nueva / Reabrir Investigación -->
<div id="rd-new-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:9999;align-items:center;justify-content:center">
  <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;width:90%;max-width:550px;padding:24px;position:relative">
    <button onclick="closeNewRdModal()" style="position:absolute;top:16px;right:16px;background:none;border:none;color:var(--muted);font-size:18px;cursor:pointer">✖</button>
    <h2 id="rd-new-title" style="font-size:18px;margin-bottom:6px">⚡ Nueva Investigación</h2>
    <p id="rd-new-sub" style="font-size:12px;color:var(--muted);margin-bottom:16px">Configura los parámetros para iniciar una simulación cuantitativa.</p>

    <div style="margin-bottom:12px">
      <label style="font-size:12px;font-weight:600;display:block;margin-bottom:4px">Símbolo:</label>
      <select id="rd-form-symbol" style="width:100%;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:8px;border-radius:6px;font-size:13px">
        <option value="EURUSD">EURUSD</option>
        <option value="XAUUSD">XAUUSD</option>
        <option value="BTCEUR">BTCEUR</option>
      </select>
    </div>

    <div style="margin-bottom:12px">
      <label style="font-size:12px;font-weight:600;display:block;margin-bottom:4px">Título de la prueba:</label>
      <input type="text" id="rd-form-title" style="width:100%;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:8px;border-radius:6px;font-size:13px" placeholder="Título de la investigación...">
    </div>

    <div style="margin-bottom:16px">
      <label style="font-size:12px;font-weight:600;display:block;margin-bottom:4px">Hipótesis / Objetivo:</label>
      <textarea id="rd-form-hypothesis" rows="3" style="width:100%;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:8px;border-radius:6px;font-size:12px;font-family:inherit" placeholder="Objetivo de la simulación..."></textarea>
    </div>

    <div style="display:flex;justify-content:flex-end;gap:10px">
      <button onclick="closeNewRdModal()" style="background:var(--bg);border:1px solid var(--border);color:var(--text);padding:8px 16px;border-radius:6px;cursor:pointer">Cancelar</button>
      <button onclick="submitNewInvestigation()" class="export-btn">🚀 Iniciar Simulación</button>
    </div>
  </div>
</div>

<div class="footer">
  <span>{port_label}: <a href="http://localhost:{port}">:{port}</a> · <a href="/api/metrics">API JSON</a> · <a href="/api/export">Export CSV</a></span>
  <span id="exec-status">{exec_active_text}</span>
</div>

<script>
var equityChart = null;
(function() {{
  try {{
    var eqData = {eq_pts_json};
    var eqColor = '{eq_color}';
    var ctx = document.getElementById('equityChart');
    if (!ctx || !eqData || eqData.length < 2) return;
    equityChart = new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: eqData.map(function(_, i) {{ return i === 0 ? '{t("Start")}' : 'T+' + i; }}),
        datasets: [{{
          label: 'Equity (€)',
          data: eqData,
          borderColor: eqColor,
          backgroundColor: eqColor + '22',
          borderWidth: 2,
          pointRadius: eqData.length > 20 ? 0 : 3,
          fill: true,
          tension: 0.3,
        }}]
      }},
      options: {{
        responsive: true,
        animation: false,
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            callbacks: {{
              label: function(ctx) {{ return ctx.parsed.y.toLocaleString('es-ES', {{minimumFractionDigits:2}}) + ' €'; }}
            }}
          }}
        }},
        scales: {{
          x: {{ ticks: {{ color: '#8b949e', maxTicksLimit: 10 }}, grid: {{ color: '#30363d' }} }},
          y: {{ ticks: {{ color: '#8b949e', callback: function(v) {{ return v.toLocaleString('es-ES', {{minimumFractionDigits:0}}) + ' €'; }} }}, grid: {{ color: '#30363d' }} }}
        }}
      }}
    }});
  }} catch(e) {{ console.warn('Chart.js error:', e); }}
}})();

// ── Symbol filter ─────────────────────────────────────────────────────────
var currentFilter = 'ALL';
function filterSignals(sym) {{
  currentFilter = sym;
  document.querySelectorAll('.filter-btn').forEach(function(b) {{
    b.classList.toggle('active', b.textContent.trim() === sym);
  }});
  applyFilter();
}}

function applyFilter() {{
  var rows = document.querySelectorAll('#signals-table tbody tr');
  rows.forEach(function(row) {{
    if (currentFilter === 'ALL') {{
      row.style.display = '';
    }} else {{
      var symCell = row.querySelector('td:nth-child(2)');
      row.style.display = (symCell && symCell.textContent.trim() === currentFilter) ? '' : 'none';
    }}
  }});
}}

// ── Browser push notifications ────────────────────────────────────────────
var _lastSignalCount = {s_today};
function _checkNewSignals() {{
  fetch('/api/metrics').then(function(r) {{ return r.json(); }}).then(function(data) {{
    var count = (data.signals || {{}}).today || 0;
    if (count > _lastSignalCount) {{
      var diff = count - _lastSignalCount;
      _lastSignalCount = count;
      if (Notification && Notification.permission === 'granted') {{
        new Notification('🎯 {new_sig_title}', {{
          body: diff + ' {new_sig_body_suffix}',
          icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><text y="28" font-size="28">⚡</text></svg>'
        }});
      }}
    }}
  }}).catch(function() {{}});
}}
if (Notification && Notification.permission === 'default') {{
  Notification.requestPermission();
}}

// ── P4 Observability Execution Explorer JS Loader ─────────────────────────
function loadP4ExecutionExplorer() {{
  var days = document.getElementById('p4-days') ? document.getElementById('p4-days').value : '30';
  var symbol = document.getElementById('p4-symbol') ? document.getElementById('p4-symbol').value : '';
  var search = document.getElementById('p4-search') ? document.getElementById('p4-search').value.toLowerCase().trim() : '';

  var url = '/api/analytics/execution?days=' + days + (symbol ? '&symbol=' + symbol : '');
  fetch(url)
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      if (!data) return;
      var score = data.broker_quality_score || 100.0;
      var elScoreVal = document.getElementById('p4-score-val');
      if (elScoreVal) elScoreVal.textContent = score.toFixed(1);

      var elScoreBadge = document.getElementById('p4-score-badge');
      if (elScoreBadge) {{
        var col = score >= 80 ? '#3fb950' : (score >= 50 ? '#d29922' : '#f85149');
        var bg = score >= 80 ? 'rgba(63,185,80,0.15)' : (score >= 50 ? 'rgba(210,153,34,0.15)' : 'rgba(248,81,73,0.15)');
        elScoreBadge.style.color = col;
        elScoreBadge.style.borderColor = col;
        elScoreBadge.style.background = bg;
      }}

      var elFill = document.getElementById('p4-fill-rate');
      if (elFill) elFill.textContent = (data.fill_rate_pct || 100).toFixed(1) + '%';

      var elLat = document.getElementById('p4-avg-lat');
      if (elLat) elLat.textContent = Math.round(data.avg_latency_ms || 0) + ' ms';

      var elSlip = document.getElementById('p4-avg-slip');
      if (elSlip) elSlip.textContent = (data.avg_slippage_pips || 0).toFixed(3) + ' pips';

      var elCost = document.getElementById('p4-slip-cost');
      if (elCost) {{
        var cVal = data.total_slippage_cost_eur || 0;
        elCost.textContent = (cVal >= 0 ? '+' : '') + cVal.toFixed(2) + ' €';
        elCost.style.color = cVal <= 0 ? '#3fb950' : '#f85149';
      }}
    }}).catch(function(e) {{ console.warn('P4 Analytics error:', e); }});

  fetch('/api/data')
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      var tbody = document.getElementById('p4-explorer-tbody');
      if (!tbody) return;
      var signals = (data && data.session_signals) ? data.session_signals : [];

      if (symbol) {{
        signals = signals.filter(function(s) {{ return s.symbol === symbol; }});
      }}
      if (search) {{
        signals = signals.filter(function(s) {{
          var str = (s.symbol + ' ' + s.strategy + ' ' + s.signal_type + ' ' + (s.final_status||'')).toLowerCase();
          return str.indexOf(search) !== -1;
        }});
      }}

      if (signals.length === 0) {{
        tbody.innerHTML = '<tr><td colspan="8" class="empty">No se encontraron ejecuciones para los filtros seleccionados.</td></tr>';
        return;
      }}

      var html = '';
      signals.forEach(function(s) {{
        var statusCol = s.final_status === 'win' ? '#3fb950' : (s.final_status === 'loss' ? '#f85149' : '#d29922');
        var lat = s.latency_ms ? s.latency_ms + ' ms' : '—';
        var slip = s.slippage_pips ? (s.slippage_pips > 0 ? '+' : '') + s.slippage_pips + ' p' : '—';
        html += '<tr>' +
          '<td>' + (s.timestamp ? s.timestamp.substring(0, 16).replace('T', ' ') : '—') + '</td>' +
          '<td><b>' + (s.symbol || '—') + '</b></td>' +
          '<td>' + (s.strategy || '—') + '</td>' +
          '<td><span class="badge badge-' + (s.signal_type === 'BUY' ? 'buy' : 'sell') + '">' + s.signal_type + '</span></td>' +
          '<td>' + lat + '</td>' +
          '<td>' + slip + '</td>' +
          '<td><code>10009 SUCCESS</code></td>' +
          '<td><span style="color:' + statusCol + ';font-weight:600">' + (s.final_status || 'PENDING').toUpperCase() + '</span></td>' +
          '</tr>';
      }});
      tbody.innerHTML = html;
    }}).catch(function(e) {{ console.warn('P4 Explorer table error:', e); }});
}}

setTimeout(loadP4ExecutionExplorer, 1000);
setInterval(loadP4ExecutionExplorer, 15000);

// ── Client-side JS update loop polling /api/data every 10s via fetch() ────
function fetchDashboardUpdate() {{
  fetch('/api/data')
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      if (!data) return;
      var metrics = data.metrics || {{}};
      var sig = metrics.signals || {{}};
      var trd = metrics.trading || {{}};
      var eq = data.equity || {{}};
      var wr = data.win_rate || {{}};
      var sessionSignals = data.session_signals || [];

      // Update stat counters
      var elSysStatus = document.getElementById('stat-sys-status');
      if (elSysStatus && metrics.system_status) elSysStatus.textContent = metrics.system_status;

      var elUptime = document.getElementById('stat-uptime');
      if (elUptime && metrics.uptime_formatted) {{
        elUptime.textContent = '{t("Uptime")}: ' + metrics.uptime_formatted;
      }}

      var elSigToday = document.getElementById('stat-signals-today');
      if (elSigToday) elSigToday.textContent = sig.today || 0;

      var elSigShown = document.getElementById('stat-signals-shown');
      if (elSigShown) {{
        var sRate = (sig.show_rate || 0).toFixed(0) + '%';
        elSigShown.textContent = '{t("Shown_count")}: ' + sessionSignals.length + ' (' + sRate + ')';
      }}

      var elPosOpen = document.getElementById('stat-pos-open');
      if (elPosOpen) elPosOpen.textContent = trd.positions_open || 0;

      var elLastSig = document.getElementById('stat-last-signal');
      if (elLastSig) {{
        var ls = sig.last_signal_time || '';
        var lsFmt = ls ? ls.substring(0, 16).replace('T', ' ') : '—';
        elLastSig.textContent = '{t("Last signal")}: ' + lsFmt;
      }}

      var elProfit = document.getElementById('stat-total-profit');
      if (elProfit) {{
        var pVal = trd.total_profit || 0.0;
        var pSign = pVal >= 0 ? '+' : '';
        elProfit.textContent = pSign + pVal.toFixed(2) + ' €';
        elProfit.style.color = pVal >= 0 ? '#3fb950' : '#f85149';
      }}

      // Update Equity Card
      var total = eq.total_equity || 0;
      var change = eq.change || 0;
      var pct = eq.change_pct || 0;
      var float_ = eq.floating_pnl || 0;
      var color = change >= 0 ? '#3fb950' : '#f85149';
      var fcolor = float_ >= 0 ? '#3fb950' : '#f85149';
      var sign = change >= 0 ? '+' : '';
      var fsign = float_ >= 0 ? '+' : '';

      var elTotal = document.getElementById('eq-total');
      var elPct = document.getElementById('eq-pct');
      var elClosed = document.getElementById('eq-closed');
      var elFloat = document.getElementById('eq-float');
      var elOpenCnt = document.getElementById('eq-open-count');

      if (elTotal) {{ elTotal.textContent = total.toLocaleString('es-ES', {{minimumFractionDigits:2, maximumFractionDigits:2}}) + ' €'; elTotal.style.color = color; }}
      if (elPct) {{ elPct.textContent = sign + pct.toFixed(2) + '%'; elPct.style.color = color; }}
      if (elClosed) {{ elClosed.textContent = sign + change.toFixed(2) + ' €'; elClosed.style.color = color; }}
      if (elFloat) {{ elFloat.textContent = fsign + float_.toFixed(2) + ' €'; elFloat.style.color = fcolor; }}
      if (elOpenCnt) {{ elOpenCnt.textContent = '(' + (wr.open || 0) + ' {t("open")})'; }}

      // Update Win Rate
      var elWr = document.getElementById('stat-winrate');
      var wrPct = wr.win_rate_pct || 0;
      var wrColor = wrPct >= 50 ? '#3fb950' : (wrPct >= 40 ? '#d29922' : '#f85149');
      if (elWr) {{
        elWr.textContent = wrPct.toFixed(0) + '%';
        elWr.style.color = wrColor;
      }}
      var elWrSub = document.getElementById('stat-winrate-sub');
      if (elWrSub) {{
        elWrSub.textContent = '✅ ' + (wr.wins || 0) + ' {t("wins")} · ❌ ' + (wr.losses || 0) + ' {t("losses")} · ⏳ ' + (wr.open || 0) + ' {t("open pos")}';
      }}

      // Update Signals Table
      var tbody = document.querySelector('#signals-table tbody');
      if (tbody && sessionSignals) {{
        if (sessionSignals.length === 0) {{
          tbody.innerHTML = '<tr><td colspan="12" class="empty">{no_signals_msg}</td></tr>';
        }} else {{
          var html = '';
          var rev = sessionSignals.slice(-50).reverse();
          rev.forEach(function(ev) {{
            var ts = (ev.timestamp || '').substring(0, 16).replace('T', ' ');
            var sym = ev.symbol || '';
            var stype = ev.signal_type || '';
            var conf = ev.confidence || '';
            var shown = ev.shown ? '✅' : '—';
            var cc = {{'HIGH':'conf-high','VERY_HIGH':'conf-high','MEDIUM-HIGH':'conf-med-high','MEDIUM':'conf-med'}}[conf] || 'conf-low';
            var dc = stype === 'BUY' ? 'dir-buy' : 'dir-sell';
            var entry = ev.entry; var sl = ev.sl; var tp = ev.tp;

            var fmtVal = function(v) {{
              if (v == null) return '—';
              if (sym === 'EURUSD') return v.toFixed(5);
              if (sym === 'XAUUSD') return v.toFixed(2);
              return v.toFixed(0);
            }};

            var rrStr = (entry != null && sl != null && tp != null && Math.abs(entry - sl) > 0)
              ? (Math.abs(tp - entry) / Math.abs(entry - sl)).toFixed(1)
              : '—';

            var fs = ev.final_status;
            var stHtml = '<span style="color:#8b949e">—</span>';
            if (fs === 'win') {{
              stHtml = '<span style="color:#3fb950;font-weight:600">WIN ✅</span>';
            }} else if (fs === 'loss') {{
              stHtml = '<span style="color:#f85149;font-weight:600">LOSS ❌</span>';
            }} else if (fs === 'open') {{
              var pnl = ev.unrealized_pnl;
              var cur = ev.current_price;
              if (pnl != null && cur != null) {{
                var pnlColor = pnl >= 0 ? '#3fb950' : '#f85149';
                var pnlSign = pnl >= 0 ? '+' : '';
                stHtml = '<span style="color:' + pnlColor + '">OPEN ' + pnlSign + pnl.toFixed(0) + '%</span>';
              }} else {{
                stHtml = '<span style="color:#d29922">OPEN ⏳</span>';
              }}
            }}

            var latStr = (ev.latency_ms != null) ? ev.latency_ms + ' ms' : '—';
            var slipStr = (ev.slippage_pips != null) ? ev.slippage_pips.toFixed(1) + ' pips' : '—';

            html += '<tr><td>' + ts + '</td><td class="sym">' + sym + '</td>'
                  + '<td class="' + dc + '">' + stype + '</td><td class="' + cc + '">' + conf + '</td>'
                  + '<td>' + fmtVal(entry) + '</td><td style="color:var(--red)">' + fmtVal(sl) + '</td>'
                  + '<td style="color:var(--green)">' + fmtVal(tp) + '</td>'
                  + '<td>' + rrStr + '</td>'
                  + '<td>' + latStr + '</td>'
                  + '<td>' + slipStr + '</td>'
                  + '<td>' + stHtml + '</td><td>' + shown + '</td></tr>\n';
          }});
          tbody.innerHTML = html;
        }}
        applyFilter();
      }}

      // Update Chart.js datasets in-place
      if (equityChart && data.equity_pts) {{
        equityChart.data.labels = data.equity_pts.map(function(_, i) {{ return i === 0 ? '{t("Start")}' : 'T+' + i; }});
        equityChart.data.datasets[0].data = data.equity_pts;
        equityChart.update('none');
      }}
    }})
    .catch(function(err) {{
      console.warn('Dashboard poll error:', err);
    }});
}}

// ── Research Database Client JS ──────────────────────────────────────────
var _activeExpId = null;
function loadResearchExperiments() {{
  var s = document.getElementById('rd-search') ? document.getElementById('rd-search').value : '';
  var sym = document.getElementById('rd-symbol') ? document.getElementById('rd-symbol').value : '';
  var st = document.getElementById('rd-status') ? document.getElementById('rd-status').value : '';

  var url = 'http://localhost:5000/api/research/experiments?limit=50';
  if (sym) url += '&symbol=' + encodeURIComponent(sym);
  if (st) url += '&decision_status=' + encodeURIComponent(st);
  if (s) url += '&search=' + encodeURIComponent(s);

  fetch(url)
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      var tbody = document.getElementById('research-tbody');
      if (!tbody) return;
      if (!data.ok || !data.experiments || data.experiments.length === 0) {{
        tbody.innerHTML = '<tr><td colspan="8" class="empty">Sin experimentos de investigación en la BD</td></tr>';
        return;
      }}

      var html = '';
      data.experiments.forEach(function(exp) {{
        var badgeBg = 'rgba(63,185,80,.15)';
        var badgeCol = 'var(--green)';
        if (exp.decision_status === 'REJECTED') {{ badgeBg = 'rgba(248,81,73,.15)'; badgeCol = 'var(--red)'; }}
        else if (exp.decision_status === 'CANDIDATE') {{ badgeBg = 'rgba(210,153,34,.15)'; badgeCol = 'var(--yellow)'; }}
        else if (exp.decision_status === 'ARCHIVED') {{ badgeBg = 'rgba(139,148,158,.15)'; badgeCol = 'var(--muted)'; }}

        var gitStr = exp.git_commit ? exp.git_commit.substring(0, 7) : 'n/a';
        var pf = exp.best_profit_factor ? exp.best_profit_factor.toFixed(2) : '—';
        var stab = exp.best_stability_score ? exp.best_stability_score.toFixed(1) : '—';

        html += '<tr>' +
          '<td><strong>' + (exp.title || exp.experiment_id) + '</strong><div style="font-size:10px;color:var(--muted)">' + exp.experiment_id + '</div></td>' +
          '<td class="sym">' + exp.symbol + '</td>' +
          '<td>' + exp.strategy + '</td>' +
          '<td style="color:var(--green);font-weight:600">' + pf + '</td>' +
          '<td style="color:var(--purple)">' + stab + '</td>' +
          '<td><code style="font-size:11px">' + gitStr + '</code></td>' +
          '<td><span class="cb-pill" style="background:' + badgeBg + ';color:' + badgeCol + '">' + exp.decision_status + '</span></td>' +
          '<td><button onclick="openRdModal(\'' + exp.experiment_id + '\')" class="export-btn" style="padding:2px 8px;font-size:11px">Ficha / Editar</button></td>' +
          '</tr>';
      }});
      tbody.innerHTML = html;
    }})
    .catch(function(e) {{
      var tbody = document.getElementById('research-tbody');
      if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="empty" style="color:var(--red)">API Server no conectado en http://localhost:5000</td></tr>';
    }});
}}

function openRdModal(expId) {{
  _activeExpId = expId;
  fetch('http://localhost:5000/api/research/experiments/' + encodeURIComponent(expId))
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      if (!data.ok || !data.experiment) return;
      var exp = data.experiment;
      document.getElementById('rd-modal-title').textContent = exp.title || exp.experiment_id;
      document.getElementById('rd-modal-meta').textContent = exp.symbol + ' · ' + exp.strategy + ' · Git: ' + (exp.git_commit || 'n/a') + ' · Bot v' + (exp.bot_version || '1.1.0');
      document.getElementById('rd-modal-hypothesis').textContent = exp.hypothesis || 'Sin hipótesis registrada.';
      
      document.getElementById('rd-m-pf').textContent = exp.best_profit_factor ? exp.best_profit_factor.toFixed(2) : '—';
      document.getElementById('rd-m-wr').textContent = exp.best_winrate ? exp.best_winrate.toFixed(1) + '%' : '—';
      document.getElementById('rd-m-stab').textContent = exp.best_stability_score ? exp.best_stability_score.toFixed(1) : '—';
      document.getElementById('rd-m-dd').textContent = exp.best_max_drawdown ? exp.best_max_drawdown.toFixed(0) + ' p' : '—';

      document.getElementById('rd-edit-status').value = exp.decision_status || 'DRAFT';
      document.getElementById('rd-edit-notes').value = exp.decision_notes || exp.notes || '';

      document.getElementById('rd-modal').style.display = 'flex';
    }});
}}

function closeRdModal() {{
  document.getElementById('rd-modal').style.display = 'none';
  _activeExpId = null;
}}

function saveRdDecision() {{
  if (!_activeExpId) return;
  var st = document.getElementById('rd-edit-status').value;
  var notes = document.getElementById('rd-edit-notes').value;

  fetch('http://localhost:5000/api/research/experiments/' + encodeURIComponent(_activeExpId), {{
    method: 'PATCH',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ decision_status: st, decision_notes: notes }})
  }})
  .then(function(r) {{ return r.json(); }})
  .then(function(data) {{
    if (data.ok) {{
      alert('Dictamen guardado con éxito para ' + _activeExpId);
      closeRdModal();
      loadResearchExperiments();
    }} else {{
      alert('Error: ' + data.message);
    }}
  }});
}}

function resetRdFilters() {{
  if (document.getElementById('rd-search')) document.getElementById('rd-search').value = '';
  if (document.getElementById('rd-symbol')) document.getElementById('rd-symbol').value = '';
  if (document.getElementById('rd-status')) document.getElementById('rd-status').value = '';
  loadResearchExperiments();
}}

function openNewRdModal() {{
  document.getElementById('rd-new-title').textContent = '⚡ Nueva Investigación';
  document.getElementById('rd-new-sub').textContent = 'Configura los parámetros para iniciar una simulación cuantitativa.';
  document.getElementById('rd-form-title').value = 'Nueva Validación Cuantitativa';
  document.getElementById('rd-form-hypothesis').value = 'Validar estabilidad out-of-sample y trailing stop optimizado.';
  document.getElementById('rd-new-modal').style.display = 'flex';
}}

function closeNewRdModal() {{
  document.getElementById('rd-new-modal').style.display = 'none';
}}

function submitNewInvestigation() {{
  var sym = document.getElementById('rd-form-symbol').value;
  var title = document.getElementById('rd-form-title').value;
  var hyp = document.getElementById('rd-form-hypothesis').value;
  var strategy = sym.toLowerCase() + '_partial';

  fetch('http://localhost:5000/api/research/exit-research', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ symbol: sym, strategy: strategy, title: title, hypothesis: hyp }})
  }})
  .then(function(r) {{ return r.json(); }})
  .then(function(res) {{
    if (res.ok) {{
      alert('Investigación iniciada correctamente. Tarea #' + (res.taskId || 'OK') + ' encolada.');
      closeNewRdModal();
      loadResearchExperiments();
    }} else {{
      alert('Error al iniciar: ' + (res.message || 'Error desconocido'));
    }}
  }});
}}

function reopenExperimentFromModal() {{
  if (!_activeExpId) return;
  fetch('http://localhost:5000/api/research/experiments/' + encodeURIComponent(_activeExpId) + '/reopen')
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      if (!data.ok || !data.reproducible_payload) return;
      var payload = data.reproducible_payload;
      fetch('http://localhost:5000/api/research/exit-research', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ symbol: payload.symbol, strategy: payload.strategy }})
      }})
      .then(function(r) {{ return r.json(); }})
      .then(function(res) {{
        alert('Investigación Reabierta: Réplica de ' + _activeExpId + ' con configuración del commit ' + (payload.git_commit || 'actual') + '. Tarea #' + (res.taskId || 'OK') + ' encolada.');
        closeRdModal();
      }});
    }});
}}

loadResearchExperiments();

setInterval(fetchDashboardUpdate, 10000);
</script>
</body></html>"""

        except Exception as e:
            logger.error(f"Error generating dashboard HTML: {e}")
            return (f"<html><body style='background:#0d1117;color:#e6edf3;font-family:sans-serif;padding:40px'>"
                    f"<h2>Dashboard Error</h2><pre>{e}</pre></body></html>")

    def _update_signal_metrics(self, event: SignalEvent):
        with self.lock:
            self.metrics.signals_today += 1
            self.metrics.symbol_activity[event.symbol] += 1
            self.metrics.confidence_distribution[event.confidence] += 1
            if event.shown:
                self.metrics.signals_shown += 1
            else:
                self.metrics.signals_rejected += 1
            if event.executed:
                self.metrics.signals_executed += 1
            if event.symbol not in self.metrics.symbol_performance:
                self.metrics.symbol_performance[event.symbol] = {
                    'total_signals': 0, 'shown_signals': 0,
                    'executed_signals': 0, 'avg_confidence_score': 0.0,
                }
            sp = self.metrics.symbol_performance[event.symbol]
            sp['total_signals'] += 1
            if event.shown:    sp['shown_signals'] += 1
            if event.executed: sp['executed_signals'] += 1
            total = sp['total_signals']
            sp['avg_confidence_score'] = ((sp['avg_confidence_score'] * (total-1)) + event.score) / total

    def _update_loop(self):
        while self.is_running:
            try:
                self._cleanup_old_data()
                self._update_simulated_positions()   # actualizar P&L en tiempo real
                # Sincronizar equity y acciones móviles (accept/reject)
                try:
                    from services.mobile_store import get_mobile_store
                    get_mobile_store().sync_dashboard(self)
                except Exception as ms_err:
                    logger.debug(f"Mobile store sync: {ms_err}")
                if self.dashboard_config['enable_persistence']:
                    self._save_persisted_data()
                time.sleep(self.dashboard_config['update_interval'])
            except Exception as e:
                logger.error(f"Dashboard update loop error: {e}")
                time.sleep(5)

    def _update_simulated_positions(self):
        """
        Actualiza el estado y P&L de cada señal abierta consultando MT5.
        Una vez que una señal llega a WIN o LOSS, el estado queda fijo.
        Los P&L incluyen spread y comisión (costes reales de trading).
        """
        try:
            import MetaTrader5 as mt5
            from core.trade_costs import get_round_trip_cost_pips

            with self.lock:
                history_copy = list(self.signal_history)

            for ev in history_copy:
                # Si ya está cerrada, no recalcular
                if ev.final_status in ('win', 'loss'):
                    continue
                if not (ev.entry and ev.sl and ev.tp and ev.shown):
                    continue

                tick = mt5.symbol_info_tick(ev.symbol)
                if not tick:
                    continue

                price = (tick.bid + tick.ask) / 2
                ev.current_price = price
                with self.lock:
                    self.last_mt5_update = datetime.now(timezone.utc)

                # Calcular P&L no realizado como % del riesgo (con costes)
                risk = abs(ev.entry - ev.sl)
                if risk > 0:
                    if ev.signal_type == 'BUY':
                        move = price - ev.entry
                    else:
                        move = ev.entry - price

                    # Descontar coste de spread+comisión del movimiento bruto
                    pip_sizes = {'EURUSD': 0.0001, 'XAUUSD': 0.1, 'BTCEUR': 1.0}
                    pip_size  = pip_sizes.get(ev.symbol, 0.0001)
                    cost_pips = get_round_trip_cost_pips(ev.symbol)
                    cost_price = cost_pips * pip_size   # coste en unidades de precio
                    move_net  = move - cost_price       # movimiento neto tras costes

                    ev.unrealized_pnl = (move_net / risk) * 100   # % del riesgo

                # Verificar si tocó TP o SL — estado permanente
                prev_status = ev.final_status
                if ev.signal_type == 'BUY':
                    if price >= ev.tp:
                        ev.final_status = 'win'
                    elif price <= ev.sl:
                        ev.final_status = 'loss'
                    else:
                        ev.final_status = 'open'
                else:
                    if price <= ev.tp:
                        ev.final_status = 'win'
                    elif price >= ev.sl:
                        ev.final_status = 'loss'
                    else:
                        ev.final_status = 'open'

                # Notificar al circuit breaker al cerrar señal
                if prev_status not in ('win', 'loss') and ev.final_status in ('win', 'loss'):
                    try:
                        from core.circuit_breaker import get_circuit_breaker
                        pip_sizes = {'EURUSD': 0.0001, 'XAUUSD': 0.1, 'BTCEUR': 1.0}
                        pip_size  = pip_sizes.get(ev.symbol, 0.0001)
                        if ev.final_status == 'win':
                            pips = abs(ev.tp - ev.entry) / pip_size
                        else:
                            pips = -abs(ev.entry - ev.sl) / pip_size
                        get_circuit_breaker().record_result(
                            outcome=ev.final_status.upper(),
                            pips=pips,
                            symbol=ev.symbol,
                        )
                    except Exception as cb_err:
                        logger.debug(f"Circuit breaker record error: {cb_err}")

        except Exception as e:
            logger.debug(f"Simulated positions update error: {e}")

    def get_equity_snapshot(self) -> Dict:
        """
        Snapshot de equity desde la cuenta MT5 (demo o real).
        Sin simulación paper: balance/equity vienen siempre del terminal.
        """
        try:
            import MetaTrader5 as mt5

            info = mt5.account_info()
            if not info:
                raise RuntimeError("MT5 account_info unavailable")

            balance = float(info.balance)
            equity = float(info.equity)
            margin = float(info.margin)
            free_margin = float(info.margin_free)

            with self.lock:
                if self.metrics.paper_balance_base == 0.0:
                    self.metrics.paper_balance_base = balance
                base = self.metrics.paper_balance_base

            change = equity - base

            return {
                'mode': 'mt5',
                'balance': balance,
                'floating_pnl': equity - balance,
                'total_equity': equity,
                'margin': margin,
                'free_margin': free_margin,
                'change': change,
                'change_pct': (change / base * 100) if base > 0 else 0.0,
                'base_balance': base,
            }

        except Exception as e:
            logger.debug(f"get_equity_snapshot error: {e}")
            with self.lock:
                base = self.metrics.paper_balance_base or 5000.0
            return {
                'mode': 'mt5',
                'balance': base,
                'floating_pnl': 0.0,
                'total_equity': base,
                'margin': 0.0,
                'free_margin': base,
                'change': 0.0,
                'change_pct': 0.0,
                'base_balance': base,
            }

    def _cleanup_old_data(self):
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=self.dashboard_config['history_retention_hours'])
            with self.lock:
                while self.signal_history and self.signal_history[0].timestamp < cutoff:
                    self.signal_history.popleft()
                while self.performance_history:
                    t_str = self.performance_history[0]['timestamp']
                    t_val = datetime.fromisoformat(t_str.replace('Z', '+00:00'))
                    if t_val < cutoff:
                        self.performance_history.popleft()
                    else:
                        break
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def _format_uptime(self, uptime: timedelta) -> str:
        s = int(uptime.total_seconds())
        h, r = divmod(s, 3600); m, sec = divmod(r, 60)
        return f"{h}h {m}m" if h > 0 else f"{m}m {sec}s" if m > 0 else f"{sec}s"

    def _save_persisted_data(self):
        try:
            with self.lock:
                history_copy = list(self.signal_history)
                metrics_data = {
                    'signals_today': self.metrics.signals_today,
                    'signals_shown': self.metrics.signals_shown,
                    'signals_executed': self.metrics.signals_executed,
                    'signals_rejected': self.metrics.signals_rejected,
                    'symbol_activity': dict(self.metrics.symbol_activity),
                    'symbol_performance': {k: dict(v) for k, v in self.metrics.symbol_performance.items()},
                    'confidence_distribution': dict(self.metrics.confidence_distribution),
                    'paper_balance': self.metrics.paper_balance,
                    'paper_balance_base': self.metrics.paper_balance_base,
                }

            history_serialized = [
                {'timestamp': ev.timestamp.isoformat(), 'symbol': ev.symbol,
                 'strategy': ev.strategy, 'signal_type': ev.signal_type,
                 'confidence': ev.confidence, 'score': ev.score,
                 'shown': ev.shown, 'executed': ev.executed,
                 'rejection_reason': ev.rejection_reason,
                 'entry': ev.entry, 'sl': ev.sl, 'tp': ev.tp,
                 'final_status': ev.final_status,
                 'current_price': ev.current_price,
                 'unrealized_pnl': ev.unrealized_pnl}
                for ev in history_copy
            ]
            data = {
                'metrics': metrics_data,
                'signal_history': history_serialized,
                'last_save': datetime.now(timezone.utc).isoformat(),
            }
            with open(self.dashboard_config['data_file'], 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def _load_persisted_data(self):
        """
        Al arrancar, todo empieza desde cero — historial de señales y métricas.
        El archivo dashboard_data.json se ignora al arrancar.
        """
        logger.info("Dashboard: nueva sesión — historial iniciado desde cero")


# ── Instancia global ──────────────────────────────────────────────────────────

dashboard_service = DashboardService()


def get_dashboard_service() -> DashboardService:
    return dashboard_service

def start_enhanced_dashboard():
    dashboard_service.start()

def stop_enhanced_dashboard():
    dashboard_service.stop()

def add_signal_to_enhanced_dashboard(symbol: str, strategy: str, signal_type: str,
                                     confidence: str, score: float, shown: bool, **kwargs):
    dashboard_service.add_signal_event(
        symbol, strategy, signal_type, confidence, score, shown,
        entry=kwargs.get('entry'), sl=kwargs.get('sl'), tp=kwargs.get('tp'),
        **{k: v for k, v in kwargs.items() if k not in ('entry', 'sl', 'tp')}
    )

def update_dashboard_stats(positions_open: int = 0, total_profit: float = 0.0, win_rate: float = 0.0):
    dashboard_service.update_trading_metrics(positions_open, total_profit, win_rate)
