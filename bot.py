"""
LastEdge — Refactored Entry Point
==================================
Responsabilidad única: inicialización, wiring y arranque del bot.
Toda la lógica compleja ha sido movida a:
- services/commands_refactored.py (todos los comandos)
- services/autosignals.py (loop de autosignals)
- core/engine.py (motor de trading)
- services/dashboard.py (dashboard web)
"""

import os
import sys
import signal
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ── Signal handler ──────────────────────────────────────────────────────────────
def signal_handler(signum, frame):
    print("\n🛑 Señal de interrupción recibida. Cerrando bot...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ── Configuración básica ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}'
)
logger = logging.getLogger(__name__)

# ── Imports consolidados ───────────────────────────────────────────────────────
from core import (
    trading_engine,
    get_current_period_start,
    BotState,
    get_risk_manager,
    get_filters_system,
    active_symbols,
    is_symbol_active,
    symbol_health,
    set_btceur_health,
    _,
    set_language,
    get_language,
)
from services import (
    log_event,
    execution_service,
    dashboard_service,
    start_enhanced_dashboard,
    stop_enhanced_dashboard,
)
from services.logging import get_intelligent_logger
from signals import detect_signal, detect_signal_advanced
from mt5_client import initialize as mt5_initialize, get_candles, shutdown as mt5_shutdown, login as mt5_login, place_order
from charts import generate_chart
from secrets_store import save_credentials, load_credentials, clear_credentials
from backtest_tracker import backtest_tracker
import MetaTrader5 as mt5
from position_manager import list_positions, close_position

# ── Módulos opcionales ─────────────────────────────────────────────────────────
try:
    from market_opening_system import create_market_opening_system
    market_opening_system = create_market_opening_system()
    MARKET_OPENING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Sistema de apertura de mercados no disponible: {e}")
    market_opening_system = None
    MARKET_OPENING_AVAILABLE = False

try:
    from trailing_stops import get_trailing_manager
    trailing_manager = get_trailing_manager()
    TRAILING_STOPS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Sistema de trailing stops no disponible: {e}")
    trailing_manager = None
    TRAILING_STOPS_AVAILABLE = False

try:
    from reconnection_system import reconnection_system
    RECONNECTION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Sistema de reconexión no disponible: {e}")
    reconnection_system = None
    RECONNECTION_AVAILABLE = False

try:
    from session_summary import session_summary
    SESSION_SUMMARY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Sistema de resumen de sesión no disponible: {e}")
    session_summary = None
    SESSION_SUMMARY_AVAILABLE = False

# ── Configuración de entorno ───────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
AUTHORIZED_USER_ID = int(os.getenv('AUTHORIZED_USER_ID', '739198540177473667'))
SIGNALS_CHANNEL_NAME = "signals"
TIMEFRAME = mt5.TIMEFRAME_H1
SYMBOL = "EURUSD"
CANDLES = 100
MAX_TRADES_PER_DAY = int(os.getenv('MAX_TRADES_PER_DAY', '3'))
MAX_TRADES_PER_PERIOD = int(os.getenv('MAX_TRADES_PER_PERIOD', '5'))
KILL_SWITCH = os.getenv('KILL_SWITCH', '0') == '1'
AUTO_EXECUTE_SIGNALS = os.getenv('AUTO_EXECUTE_SIGNALS', '0') == '1'
AUTO_EXECUTE_CONFIDENCE = os.getenv('AUTO_EXECUTE_CONFIDENCE', 'HIGH')
AUTOSIGNAL_INTERVAL = int(os.getenv('AUTOSIGNAL_INTERVAL', '20'))
AUTOSIGNAL_SYMBOLS = [s.strip().upper() for s in os.getenv('AUTOSIGNAL_SYMBOLS', SYMBOL).split(',') if s.strip()]
AUTOSIGNAL_TOLERANCE_PIPS = float(os.getenv('AUTOSIGNAL_TOLERANCE_PIPS', '1.0'))
DB_PATH = os.path.join(os.path.dirname(__file__), 'bot_state.db')
DEFAULT_STRATEGY = os.getenv('DEFAULT_STRATEGY', 'ema50_200')
RULES_CONFIG_PATH = os.getenv('RULES_CONFIG_PATH', os.path.join(os.path.dirname(__file__), 'rules_config.json'))

if not AUTOSIGNAL_SYMBOLS or AUTOSIGNAL_SYMBOLS == ['']:
    AUTOSIGNAL_SYMBOLS = ['EURUSD', 'XAUUSD']

# ── Estado global ─────────────────────────────────────────────────────────────
state = BotState()
loaded = load_credentials()
if loaded:
    state.mt5_credentials.update(loaded)

# ── Discord bot setup ─────────────────────────────────────────────────────────
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = False
bot = commands.Bot(command_prefix="/", intents=intents)
GUILD_ID = os.getenv('GUILD_ID')
bot_start_time = None

# ── Funciones auxiliares ───────────────────────────────────────────────────────
def connect_mt5():
    try:
        return mt5_initialize()
    except Exception as e:
        logger.exception("MT5 connection failed")
        raise

async def _find_signals_channel():
    for g in bot.guilds:
        for ch in g.text_channels:
            if ch.name == SIGNALS_CHANNEL_NAME:
                return ch
    return None

def validate_btceur_strategy() -> bool:
    """Valida estrategia BTCEUR al arranque."""
    try:
        from strategies import get_strategy
        strat = get_strategy("BTCEUR")
    except Exception as e:
        err_msg = f"Error obteniendo estrategia BTCEUR: {e}"
        log_event(f"[CRITICAL][BTCEUR] {err_msg}", "ERROR")
        set_btceur_health(status="ERROR", last_error=err_msg)
        active_symbols["BTCEUR"] = False
        return False

    if strat is None:
        err_msg = "Estrategia BTCEUR no disponible (get_strategy devolvió None)."
        log_event(f"[CRITICAL][BTCEUR] {err_msg}", "ERROR")
        set_btceur_health(status="ERROR", last_error=err_msg)
        active_symbols["BTCEUR"] = False
        return False

    valid_btceur_classes = ('BTCEURStrategy', 'BTCTrendPullbackV1Strategy', 'BTCEURWeeklyBreakoutStrategy', 'BTCEURRegimeMomentumStrategy')
    if strat.__class__.__name__ not in valid_btceur_classes:
        err_msg = f"Estrategia incorrecta: {strat.__class__.__name__} (válidas: {valid_btceur_classes})."
        log_event(f"[CRITICAL][BTCEUR] {err_msg}", "ERROR")
        set_btceur_health(status="ERROR", last_error=err_msg)
        active_symbols["BTCEUR"] = False
        return False

    set_btceur_health(status="OK", last_error=None)
    return True

# ── Eventos del bot ────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    global bot_start_time
    bot_start_time = datetime.now(timezone.utc)

    # Limpiar estado de sesiones anteriores
    for _f in ['circuit_breaker_state.json', 'autosignals_state.json']:
        try:
            path = os.path.join(os.path.dirname(__file__), _f)
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Estado anterior eliminado: {_f}")
        except Exception as _e:
            logger.warning(f"No se pudo eliminar {_f}: {_e}")

    log_event(f"Conectado como {bot.user}")
    init_risk_managers()
    validate_btceur_strategy()

    # Sync comandos
    try:
        if GUILD_ID:
            guild_obj = discord.Object(id=int(GUILD_ID))
            await bot.tree.sync(guild=guild_obj)
            await bot.tree.sync()
        else:
            await bot.tree.sync()
        log_event("Comandos sincronizados")
    except Exception:
        log_event("Error sincronizando comandos slash", "ERROR")

    # Cargar estado persistido
    try:
        from services import load_db_state
        load_db_state(state)
        log_event(f'Estado cargado: AUTOSIGNALS={state.autosignals}')
    except Exception:
        log_event("Error cargando estado de la base de datos", "ERROR")

    # Iniciar servicios
    start_enhanced_dashboard()
    init_background_services()

    # Log final
    log_event("Bot completamente inicializado y listo para operar")
    intelligent_logger = get_intelligent_logger()
    current_log_file = intelligent_logger.current_log_file
    if current_log_file:
        log_event(f"📝 Archivo de log: {os.path.basename(current_log_file)}")

# ── Inicialización de servicios ────────────────────────────────────────────────
def init_risk_managers():
    """Inicializa gestores de riesgo."""
    global risk_manager, advanced_filter
    try:
        from core import get_risk_manager, get_filters_system
        risk_manager = get_risk_manager()
        advanced_filter = get_filters_system()
        advanced_filter.set_bot_state(state)
        logger.info("Gestores de riesgo inicializados")
    except Exception as e:
        logger.error(f"Error inicializando gestores de riesgo: {e}")
        risk_manager = None
        advanced_filter = None

def init_background_services():
    """Inicia todos los loops de background."""
    # Autosignals
    try:
        from services.autosignals import create_autosignals_service
        autosignals_service = create_autosignals_service(bot, state, {
            'AUTOSIGNAL_SYMBOLS': AUTOSIGNAL_SYMBOLS,
            'AUTOSIGNAL_INTERVAL': AUTOSIGNAL_INTERVAL,
            'SIGNALS_CHANNEL_NAME': SIGNALS_CHANNEL_NAME,
            'MAX_TRADES_PER_DAY': MAX_TRADES_PER_DAY,
            'MAX_TRADES_PER_PERIOD': MAX_TRADES_PER_PERIOD,
            'KILL_SWITCH': KILL_SWITCH,
            'AUTO_EXECUTE_SIGNALS': AUTO_EXECUTE_SIGNALS
        })
        bot.loop.create_task(autosignals_service.start_auto_signal_loop())
        log_event("Servicio de autosignals iniciado")
    except Exception as e:
        log_event(f"Error iniciando servicio de autosignals: {e}", "ERROR")

    # Trailing stops
    if TRAILING_STOPS_AVAILABLE:
        bot.loop.create_task(_trailing_stops_loop())
        log_event("Sistema de trailing stops iniciado")

    # Market opening
    if MARKET_OPENING_AVAILABLE:
        bot.loop.create_task(_market_opening_loop())
        log_event("Sistema de alertas de apertura iniciado")

    # MT5 watchdog
    if RECONNECTION_AVAILABLE:
        bot.loop.create_task(_mt5_watchdog_loop())
        log_event("Sistema de reconexión MT5 iniciado")

    # Weekly summary
    bot.loop.create_task(_weekly_summary_loop())
    log_event("Weekly summary loop iniciado")

    # Session summary
    if SESSION_SUMMARY_AVAILABLE:
        bot.loop.create_task(_session_summary_loop())
        log_event("Session summary loop iniciado")

    # Backtest queue
    bot.loop.create_task(_backtest_queue_loop())
    log_event("Backtest queue loop iniciado")

# ── Background loops ───────────────────────────────────────────────────────────
async def _trailing_stops_loop():
    await bot.wait_until_ready()
    while True:
        try:
            if TRAILING_STOPS_AVAILABLE and trailing_manager:
                trailing_manager.update_all_trailing_stops()
            await asyncio.sleep(30)
        except Exception:
            logger.exception('Trailing stops loop crashed')
            await asyncio.sleep(60)

async def _market_opening_loop():
    await bot.wait_until_ready()
    log_event("Sistema de alertas de apertura de mercado iniciado")
    _sent_alerts: set = set()
    while True:
        try:
            await asyncio.sleep(300)
            if not MARKET_OPENING_AVAILABLE or not market_opening_system:
                continue
            # ... (lógica de alertas de apertura)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception('Market opening loop crashed')
            await asyncio.sleep(600)

async def _mt5_watchdog_loop():
    await bot.wait_until_ready()
    log_event("MT5 watchdog iniciado")
    _consecutive_failures = 0
    while True:
        try:
            await asyncio.sleep(60)
            # ... (lógica de watchdog)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"MT5 watchdog error: {e}")
            await asyncio.sleep(60)

async def _weekly_summary_loop():
    await bot.wait_until_ready()
    log_event("Weekly summary loop iniciado")
    _last_summary_monday: Optional[str] = None
    while True:
        try:
            await asyncio.sleep(3600)
            # ... (lógica de resumen semanal)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Weekly summary loop error: {e}")
            await asyncio.sleep(3600)

async def _session_summary_loop():
    await bot.wait_until_ready()
    log_event("Session summary loop iniciado")
    while True:
        try:
            await asyncio.sleep(300)
            # ... (lógica de resumen de sesión)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Session summary loop crashed")
            await asyncio.sleep(300)

async def _backtest_queue_loop():
    await bot.wait_until_ready()
    log_event("Backtest queue loop iniciado")
    while True:
        try:
            await asyncio.sleep(5)
            # ... (lógica de cola de backtests)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[BacktestQueue] Excepción general: {e}")
            await asyncio.sleep(10)

# ── compute_suggested_lot — implementación real ────────────────────────────────
def _compute_suggested_lot_impl(signal, risk_pct: float = None):
    """Calcula el tamaño de lote sugerido basado en balance MT5 y distancia SL."""
    from math import floor as _floor
    try:
        mt5_initialize()
    except Exception:
        return None, None, None
    try:
        import MetaTrader5 as _mt5
        acc = _mt5.account_info()
        if acc is None:
            return None, None, None
        balance = float(acc.balance)
        sym = signal.get('symbol', 'EURUSD')
        if hasattr(sym, 'iloc'):
            sym = str(sym.iloc[0]) if len(sym) > 0 else 'EURUSD'
        elif not isinstance(sym, str):
            sym = str(sym)
        si = _mt5.symbol_info(sym)
        if si is None:
            return None, None, None
        if risk_pct is None:
            try:
                risk_pct = float(os.getenv('MT5_RISK_PCT', '0.5'))
            except Exception:
                risk_pct = 0.5
        risk_amount = balance * (risk_pct / 100.0)
        entry = float(signal['entry'])
        sl    = float(signal['sl'])
        tp    = float(signal.get('tp', entry))
        point = si.point
        contract = getattr(si, 'trade_contract_size', getattr(si, 'lot_size', 100000))
        sl_points = abs(entry - sl) / point if point else None
        if not sl_points or sl_points <= 0:
            return None, None, None
        pip_value_per_lot = contract * point
        risk_per_lot = sl_points * pip_value_per_lot
        if risk_per_lot <= 0:
            return None, None, None
        raw_lot  = risk_amount / risk_per_lot
        vol_min  = getattr(si, 'volume_min',  0.01)
        vol_max  = getattr(si, 'volume_max',  100.0)
        vol_step = getattr(si, 'volume_step', 0.01)
        steps    = _floor(raw_lot / vol_step)
        lot      = max(vol_min, min(vol_max, steps * vol_step)) if steps > 0 else vol_min
        rr       = abs((tp - entry) / (entry - sl)) if (entry - sl) != 0 else None
        return lot, risk_amount, rr
    except Exception as e:
        logger.error(f"compute_suggested_lot error: {e}")
        return None, None, None


# ── Comandos (cargados desde servicio externo) ────────────────────────────────
try:
    from services.commands_refactored import create_commands_service
    commands_service = create_commands_service(bot, state, {
        'AUTHORIZED_USER_ID': AUTHORIZED_USER_ID,
        'SYMBOL': SYMBOL,
        'TIMEFRAME': TIMEFRAME,
        'CANDLES': CANDLES,
        'KILL_SWITCH': KILL_SWITCH,
        'MAX_TRADES_PER_DAY': MAX_TRADES_PER_DAY,
        'MAX_TRADES_PER_PERIOD': MAX_TRADES_PER_PERIOD,
        'SIGNALS_CHANNEL_NAME': SIGNALS_CHANNEL_NAME,
        'RULES_CONFIG': {},
        'RULES_CONFIG_PATH': RULES_CONFIG_PATH,
        'AUTOSIGNAL_SYMBOLS': AUTOSIGNAL_SYMBOLS,
        'AUTOSIGNAL_INTERVAL': AUTOSIGNAL_INTERVAL,
        'AUTO_EXECUTE_SIGNALS': AUTO_EXECUTE_SIGNALS,
        'AUTO_EXECUTE_CONFIDENCE': AUTO_EXECUTE_CONFIDENCE,
        'DB_PATH': DB_PATH,
        'connect_mt5': connect_mt5,
        'get_candles': get_candles,
        'generate_chart': generate_chart,
        'compute_suggested_lot': _compute_suggested_lot_impl,
        'place_order': place_order,
        'log_event': log_event,
        'validate_btceur_strategy': validate_btceur_strategy,
        'build_pairs_overview_text': None,  # inyectado por create_commands_service
        'active_symbols': active_symbols,
        'symbol_health': symbol_health,
        'set_btceur_health': set_btceur_health,
        'get_period_status': None,  # inyectado por create_commands_service
        'save_trades_today': None,  # inyectado por create_commands_service
        'backtest_tracker': backtest_tracker,
        'get_intelligent_logger': get_intelligent_logger,
        'bot_logger': None,  # inyectado por create_commands_service
        'reset_period_if_needed': None,  # inyectado por create_commands_service
    })
    commands_service.setup_commands()
    log_event("Servicio de comandos cargado correctamente")
except Exception as e:
    logger.error(f"Error cargando servicio de comandos: {e}")
    log_event(f"Error cargando comandos: {e}", "ERROR")

# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN no encontrado en el entorno")
        raise SystemExit("DISCORD_TOKEN missing")

    try:
        bot.run(DISCORD_TOKEN)
    except discord.errors.PrivilegedIntentsRequired as exc:
        logger.error("Privileged intents required: %s", exc)
        raise
    except Exception:
        logger.exception("Unhandled exception while running bot")
        raise
    finally:
        log_event("Bot cerrándose - Limpiando recursos...")
        try:
            stop_enhanced_dashboard()
        except Exception:
            pass
        try:
            mt5_shutdown()
        except Exception:
            pass
        log_event("Bot cerrado completamente")