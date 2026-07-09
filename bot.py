import os
import logging
import signal
import sys

# Add signal handler for graceful shutdown
def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Señal de interrupción recibida. Cerrando bot...")
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Parche para compatibilidad con Python 3.13
import audioop_patch

# Configurar matplotlib para evitar problemas de threading
import matplotlib
matplotlib.use('Agg')  # Usar backend sin GUI

import discord
import asyncio
import sqlite3
import json
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from math import floor
from typing import Optional

# Configurar logging ANTES de los imports opcionales
logging.basicConfig(
    level=logging.WARNING,  # Cambiar a WARNING para reducir ruido
    format='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}'
)
logger = logging.getLogger(__name__)

# ============================================================================
# IMPORTS CONSOLIDADOS - NUEVA ARQUITECTURA
# ============================================================================

# Core system (consolidado)
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
)

# Services (consolidado)
from services import (
    log_event, 
    log_signal_evaluation, 
    log_command,
    execution_service,
    dashboard_service,
    start_enhanced_dashboard,
    stop_enhanced_dashboard,
    add_signal_to_enhanced_dashboard,
    update_dashboard_stats
)

# Import intelligent logger to access current_log_file
from services.logging import get_intelligent_logger

# Signals dispatcher (simplificado)
from signals import _detect_signal_wrapper, detect_signal, detect_signal_advanced

# Módulos específicos que se mantienen
from mt5_client import initialize as mt5_initialize, get_candles, shutdown as mt5_shutdown, login as mt5_login, place_order
from charts import generate_chart
from secrets_store import save_credentials, load_credentials, clear_credentials
from backtest_tracker import backtest_tracker
import MetaTrader5 as mt5
from position_manager import list_positions, close_position

# ============================================================================
# SISTEMAS OPCIONALES (mantenidos por compatibilidad)
# ============================================================================

# Importar sistema de apertura de mercados
try:
    from market_opening_system import create_market_opening_system
    market_opening_system = create_market_opening_system()
    MARKET_OPENING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Sistema de apertura de mercados no disponible: {e}")
    market_opening_system = None
    MARKET_OPENING_AVAILABLE = False

# Importar sistema de trailing stops
try:
    from trailing_stops import get_trailing_manager
    trailing_manager = get_trailing_manager()
    TRAILING_STOPS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Sistema de trailing stops no disponible: {e}")
    trailing_manager = None
    TRAILING_STOPS_AVAILABLE = False

# Importar sistema de reconexión
try:
    from reconnection_system import reconnection_system
    RECONNECTION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Sistema de reconexión no disponible: {e}")
    reconnection_system = None
    RECONNECTION_AVAILABLE = False

# Importar sistema de resumen de sesión
try:
    from session_summary import session_summary
    SESSION_SUMMARY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Sistema de resumen de sesión no disponible: {e}")
    session_summary = None
    SESSION_SUMMARY_AVAILABLE = False

# ======================
# CONFIGURACIÓN
# ======================

AUTHORIZED_USER_ID = int(os.getenv('AUTHORIZED_USER_ID', '739198540177473667'))
SIGNALS_CHANNEL_NAME = "signals"         # configurable
TIMEFRAME = mt5.TIMEFRAME_H1
SYMBOL = "EURUSD"
CANDLES = 100

# safety / limits
MAX_TRADES_PER_DAY = int(os.getenv('MAX_TRADES_PER_DAY', '3'))
MAX_TRADES_PER_PERIOD = int(os.getenv('MAX_TRADES_PER_PERIOD', '5'))  # 5 trades cada 12 horas
KILL_SWITCH = os.getenv('KILL_SWITCH', '0') == '1'

# auto-execution settings
AUTO_EXECUTE_SIGNALS = os.getenv('AUTO_EXECUTE_SIGNALS', '0') == '1'
AUTO_EXECUTE_CONFIDENCE = os.getenv('AUTO_EXECUTE_CONFIDENCE', 'HIGH')  # FIXED: HIGH instead of LOW

# ============================================================================
# ESTADO GLOBAL CONSOLIDADO
# ============================================================================

# Usar BotState consolidado del core
state = BotState()

# Configurar loggers específicos
mt5_logger = logging.getLogger('mt5_client')
mt5_logger.setLevel(logging.ERROR)  # Solo errores de MT5

signals_logger = logging.getLogger('signals')
signals_logger.setLevel(logging.INFO)  # Mantener info de señales


def validate_btceur_strategy() -> bool:
    """
    Valida en el arranque que BTCEUR use su estrategia específica.
    En caso de problema, desactiva BTCEUR en active_symbols y deja
    trazas claras en los logs.
    """
    try:
        from strategies import get_strategy  # import local para evitar ciclos
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

    valid_btceur_classes = ('BTCEURStrategy', 'BTCTrendPullbackV1Strategy', 'BTCEURWeeklyBreakoutStrategy')
    # eurusd_asian_breakout descartada junio 2026 (PF<1.0 en 10k/15k/20k velas)
    # EURUSD ahora usa eurusd_simple con SL=1.5x ATR, TP=6.0x ATR, CB=3/72
    # btceur_regime_momentum desactivada: requiere H4+Daily, replay_engine usa H1
    if strat.__class__.__name__ not in valid_btceur_classes:
        err_msg = f"Estrategia incorrecta: {strat.__class__.__name__} (válidas: {valid_btceur_classes})."
        log_event(f"[CRITICAL][BTCEUR] {err_msg}", "ERROR")
        set_btceur_health(status="ERROR", last_error=err_msg)
        active_symbols["BTCEUR"] = False
        return False

    set_btceur_health(status="OK", last_error=None)
    return True

# ======================
# FUNCIONES DE PERÍODO (12 HORAS)
# ======================

# get_current_period_start ya está importado desde core

def is_new_period() -> bool:
    """Verifica si estamos en un nuevo período de 12 horas"""
    current_period_start = get_current_period_start()
    return current_period_start > state.current_period_start

def reset_period_if_needed():
    """Resetea el contador de trades si estamos en un nuevo período"""
    if is_new_period():
        old_count = state.trades_current_period
        state.trades_current_period = 0
        state.current_period_start = get_current_period_start()
        
        period_name = "00:00-12:00" if state.current_period_start.hour == 0 else "12:00-24:00"
        log_event(f"🔄 NUEVO PERÍODO: {period_name} UTC | Trades resetados: {old_count} → 0", "INFO", "PERIOD")

def get_period_status() -> dict:
    """Obtiene el estado actual del período"""
    reset_period_if_needed()  # Verificar si necesitamos resetear
    
    period_name = "00:00-12:00" if state.current_period_start.hour == 0 else "12:00-24:00"
    next_reset = state.current_period_start + timedelta(hours=12)
    time_until_reset = next_reset - datetime.now(timezone.utc)
    
    return {
        'current_period': period_name,
        'trades_current_period': state.trades_current_period,
        'max_trades_per_period': MAX_TRADES_PER_PERIOD,
        'trades_remaining': max(0, MAX_TRADES_PER_PERIOD - state.trades_current_period),
        'next_reset': next_reset,
        'time_until_reset': time_until_reset,
        'period_full': state.trades_current_period >= MAX_TRADES_PER_PERIOD
    }


# ======================
# DECORADOR PARA LOGGING DE COMANDOS
# ======================

def log_discord_command(func):
    """Decorador para loggear automáticamente comandos Discord"""
    import functools
    
    @functools.wraps(func)
    async def wrapper(interaction: discord.Interaction, *args, **kwargs):
        # Obtener nombre del comando
        command_name = func.__name__.replace('slash_', '')
        
        # Construir argumentos para el log
        args_str = ' '.join(str(arg) for arg in args if arg)
        kwargs_str = ' '.join(f"{k}={v}" for k, v in kwargs.items() if v)
        full_args = f"{args_str} {kwargs_str}".strip()
        
        # Log inicial del comando
        log_event(f"🎮 COMMAND: /{command_name} {full_args} | User: {interaction.user.id} ({interaction.user.display_name})")
        
        try:
            # Ejecutar el comando original
            result = await func(interaction, *args, **kwargs)
            
            # Log de éxito (solo si no hubo excepción)
            log_event(f"✅ COMMAND SUCCESS: /{command_name} {full_args}")
            return result
            
        except Exception as e:
            # Log de error
            log_event(f"❌ COMMAND ERROR: /{command_name} {full_args} | Error: {e}")
            
            # Re-lanzar la excepción para que Discord la maneje
            raise
    
    return wrapper


# ======================
# LOGGING SYSTEM
# ======================
# get_intelligent_logger ya importado arriba
bot_logger = get_intelligent_logger()

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
# Use slash commands to avoid the Message Content privileged intent
intents.message_content = False
bot = commands.Bot(command_prefix="/", intents=intents)

# Optional: fast command registration to a test guild to avoid global sync delay
GUILD_ID = os.getenv('GUILD_ID')

# Global variables for session tracking
bot_start_time = None

AUTOSIGNAL_INTERVAL = int(os.getenv('AUTOSIGNAL_INTERVAL', '20'))  # seconds between scans
AUTOSIGNAL_SYMBOLS = [s.strip().upper() for s in os.getenv('AUTOSIGNAL_SYMBOLS', SYMBOL).split(',') if s.strip()]
# AUTOSIGNAL_TOLERANCE_PIPS used to detect duplicates
AUTOSIGNAL_TOLERANCE_PIPS = float(os.getenv('AUTOSIGNAL_TOLERANCE_PIPS', '1.0'))
DB_PATH = os.path.join(os.path.dirname(__file__), 'bot_state.db')
# default strategy name (can be overridden via .env)
DEFAULT_STRATEGY = os.getenv('DEFAULT_STRATEGY', 'ema50_200')
# default autosignal symbols: EURUSD and XAUUSD; BTCEUR can be added via env
if not AUTOSIGNAL_SYMBOLS or AUTOSIGNAL_SYMBOLS == ['']:
    AUTOSIGNAL_SYMBOLS = ['EURUSD', 'XAUUSD']  # Removed BTCEUR due to strategy issues

# parse per-symbol rules from env, format: EURUSD:ema,XAUUSD:macd
_rules_raw = os.getenv('AUTOSIGNAL_RULES', '')
AUTOSIGNAL_RULES = {}
if _rules_raw:
    for part in _rules_raw.split(','):
        if ':' in part:
            s, r = part.split(':', 1)
            AUTOSIGNAL_RULES[s.strip().upper()] = r.strip().lower()

# Optional per-symbol strategy config file (JSON). Keys should be symbol uppercased.
RULES_CONFIG_PATH = os.getenv('RULES_CONFIG_PATH', os.path.join(os.path.dirname(__file__), 'rules_config.json'))
RULES_CONFIG = {}
try:
    if os.path.exists(RULES_CONFIG_PATH):
        with open(RULES_CONFIG_PATH, 'r', encoding='utf-8') as f:
            rc = json.load(f)
            # normalize keys to upper
            for k, v in rc.items():
                try:
                    RULES_CONFIG[k.strip().upper()] = dict(v or {})
                except Exception:
                    RULES_CONFIG[k.strip().upper()] = {}
except Exception:
    logger.exception('Failed to load rules config from %s', RULES_CONFIG_PATH)

# Inicializar gestores después de cargar configuración
risk_manager = None
advanced_filter = None

def init_risk_managers():
    """Inicializa los gestores de riesgo después de cargar la configuración"""
    global risk_manager, advanced_filter
    try:
        from core import get_risk_manager, get_filters_system
        risk_manager = get_risk_manager()
        advanced_filter = get_filters_system()
        # Unificar contadores: ConsolidatedFilters leerá/escribirá desde BotState
        advanced_filter.set_bot_state(state)
        logger.info("Gestores de riesgo inicializados correctamente")
    except Exception as e:
        logger.error(f"Error inicializando gestores de riesgo: {e}")
        # Crear gestores dummy para evitar errores
        risk_manager = None
        advanced_filter = None


# Funciones de base de datos ahora están en services/database.py
# Importar funciones de compatibilidad
from services import (
    init_db, load_db_state, save_autosignals_state, 
    save_last_auto_sent, save_trades_today, reset_trades_today
)

# Funciones get_symbol_tolerance y signals_similar ahora están en core/filters.py

# ======================
# UTILIDADES MT5
# ======================

def connect_mt5():
    try:
        return mt5_initialize()
    except Exception as e:
        logger.exception("MT5 connection failed")
        raise

# ======================
# GRÁFICOS
# ======================

# Use `generate_chart` imported from `charts` module above.

# ======================
# LÓGICA DE SEÑALES (EJEMPLO)
# ======================

# _detect_signal_wrapper ya está importado desde signals.py - función eliminada para evitar duplicación
def compute_suggested_lot(signal, risk_pct: float = None):
    """Compute a suggested lot size given a signal dict.

    Uses MT5 account balance and symbol info. This is an approximation and
    should be reviewed by the user before executing.
    Returns (lot, risk_amount, rr_ratio) or (None, None, None) on failure.
    """
    try:
        mt5_initialize()
    except Exception as e:
        logger.error(f"MT5 initialization failed in compute_suggested_lot: {e}")
        return None, None, None

    try:
        acc = mt5.account_info()
        if acc is None:
            logger.error("No account info available in compute_suggested_lot")
            return None, None, None
        
        balance = float(acc.balance)
        
        # Ensure symbol is a string
        symbol = signal.get('symbol')
        if hasattr(symbol, 'iloc'):  # Es una Serie de pandas
            symbol = str(symbol.iloc[0]) if len(symbol) > 0 else 'EURUSD'
        elif not isinstance(symbol, str):
            symbol = str(symbol)
        
        logger.debug(f"Computing lot for symbol: {symbol}")
        
        si = mt5.symbol_info(symbol)
        if si is None:
            logger.error(f"No symbol info for {symbol} in compute_suggested_lot")
            return None, None, None

        # default risk percent from env if not provided
        if risk_pct is None:
            try:
                risk_pct = float(os.getenv('MT5_RISK_PCT', '0.5'))
            except Exception:
                risk_pct = 0.5

        risk_amount = balance * (risk_pct / 100.0)

        entry = float(signal['entry'])
        sl = float(signal['sl'])
        
        # point value and contract size
        point = si.point
        contract = getattr(si, 'trade_contract_size', getattr(si, 'lot_size', 100000))

        # compute SL in pips (in points)
        sl_points = abs(entry - sl) / point if point and point != 0 else None
        if not sl_points or sl_points <= 0:
            logger.error(f"Invalid SL points calculation: {sl_points}")
            return None, None, None

        # approximate pip value per lot in account currency
        pip_value_per_lot = contract * point
        # risk per lot = sl_points * pip_value_per_lot
        risk_per_lot = sl_points * pip_value_per_lot
        if risk_per_lot <= 0:
            logger.error(f"Invalid risk per lot calculation: {risk_per_lot}")
            return None, None, None

        raw_lot = risk_amount / risk_per_lot

        # clamp to symbol min/max and step
        vol_min = getattr(si, 'volume_min', 0.01)
        vol_max = getattr(si, 'volume_max', 100.0)
        vol_step = getattr(si, 'volume_step', 0.01)

        # round down to nearest step
        steps = floor(raw_lot / vol_step)
        lot = max(vol_min, min(vol_max, steps * vol_step)) if steps > 0 else vol_min

        # risk/reward ratio approx
        tp = float(signal.get('tp', entry))
        rr = abs((tp - entry) / (entry - sl)) if (entry - sl) != 0 else None

        logger.debug(f"Computed lot: {lot}, risk_amount: {risk_amount}, rr: {rr}")
        return lot, risk_amount, rr
        
    except Exception as e:
        logger.error(f"Error in compute_suggested_lot: {e}")
        return None, None, None

# Load persisted credentials if available
loaded = load_credentials()
if loaded:
    state.mt5_credentials.update(loaded)

# ======================
# BOT EVENTS
# ======================

@bot.event
async def on_ready():
    global bot_start_time
    bot_start_time = datetime.now(timezone.utc)

    # ── Limpiar estado de sesiones anteriores ─────────────────────────────────
    # Cada reinicio del bot es una sesión nueva y limpia.
    # Se borran: circuit breaker (pausa activa), cooldowns de autosignals.
    _session_state_files = [
        os.path.join(os.path.dirname(__file__), 'circuit_breaker_state.json'),
        os.path.join(os.path.dirname(__file__), 'autosignals_state.json'),
    ]
    for _f in _session_state_files:
        try:
            if os.path.exists(_f):
                os.remove(_f)
                logger.info(f"Estado de sesión anterior eliminado: {os.path.basename(_f)}")
        except Exception as _e:
            logger.warning(f"No se pudo eliminar {_f}: {_e}")

    log_event(f"Conectado como {bot.user}")

    # Inicializar gestores de riesgo
    init_risk_managers()
    log_event("Gestores de riesgo inicializados correctamente")

    # Validar configuración de BTCEUR (fail-safe)
    try:
        if not validate_btceur_strategy():
            log_event("[BTCEUR FIX] BTCEUR desactivado automáticamente por configuración inválida.", "ERROR")
    except Exception as e:
        logger.error(f"Error validando estrategia BTCEUR: {e}")
    
    # Sync application commands (slash commands). If GUILD_ID is set, sync only to that guild for fast registration.
    try:
        if GUILD_ID:
            guild_obj = discord.Object(id=int(GUILD_ID))
            # Sincronizar primero solo al guild (definición actual = única fuente de verdad)
            await bot.tree.sync(guild=guild_obj)
            log_event(f"Comandos sincronizados al servidor {GUILD_ID}")
            # Sincronizar también a global para que no quede versión antigua de comandos (ej. /autosignals con "enabled")
            await bot.tree.sync()
            log_event("Comandos sincronizados globalmente (evitar sugerencias antiguas)")
        else:
            await bot.tree.sync()
            log_event("Comandos sincronizados globalmente")
    except Exception:
        log_event("Error sincronizando comandos slash", "ERROR")
        logger.exception("Failed to sync slash commands")
    
    # load persisted autosignals state and last sent info
    try:
        load_db_state(state)
        log_event(f'Estado cargado: AUTOSIGNALS={state.autosignals}')
    except Exception:
        log_event("Error cargando estado de la base de datos", "ERROR")
        logger.exception('Failed to load DB state')
    
    # start autosignal background task using services
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
        logger.exception("Failed to start autosignals service")
    
    # start trailing stops background task
    if TRAILING_STOPS_AVAILABLE:
        bot.loop.create_task(_trailing_stops_loop_simple())
        log_event("Sistema de trailing stops iniciado")
    
    # start market opening alerts background task
    if MARKET_OPENING_AVAILABLE:
        bot.loop.create_task(_market_opening_loop_simple())
        log_event("Sistema de alertas de apertura iniciado")
    
    # start enhanced dashboard
    try:
        start_enhanced_dashboard()
        log_event("Dashboard inteligente iniciado - Sistema de confianza integrado")
    except Exception as e:
        log_event(f"Error iniciando dashboard inteligente: {e}", "ERROR")
        logger.exception("Failed to start enhanced dashboard")
    
    # start reconnection system — lightweight watchdog que no bloquea el event loop
    if RECONNECTION_AVAILABLE:
        bot.loop.create_task(_mt5_watchdog_loop())
        log_event("Sistema de reconexión MT5 iniciado (watchdog ligero)")

    # start weekly summary background task
    bot.loop.create_task(_weekly_summary_loop())
    log_event("Weekly summary loop iniciado (lunes 08:00 UTC)")

    # start session summary background task
    if SESSION_SUMMARY_AVAILABLE:
        bot.loop.create_task(_session_summary_loop())
        log_event("Session summary loop iniciado (cierre London 17h, NY 22h UTC)")
    
    # start backtest queue background task
    bot.loop.create_task(_backtest_queue_loop())
    log_event("Backtest queue loop iniciado (polling cada 5s)")
    
    # Print helpful invite URL for adding the bot with application commands scope
    try:
        app_id = bot.application_id or bot.user.id
        invite_url = f"https://discord.com/oauth2/authorize?client_id={app_id}&scope=bot%20applications.commands&permissions=8"
        logger.info(f"Invite URL: {invite_url}")
        log_event("URL de invitación generada correctamente")
    except Exception:
        log_event("Error generando URL de invitación", "WARNING")
        logger.debug("Could not build invite URL")
    
    # Log configuración importante
    log_event(f"AUTO_EXECUTE_SIGNALS: {AUTO_EXECUTE_SIGNALS}")
    log_event(f"AUTO_EXECUTE_CONFIDENCE: {AUTO_EXECUTE_CONFIDENCE}")
    log_event(f"AUTOSIGNAL_INTERVAL: {AUTOSIGNAL_INTERVAL} segundos")
    log_event(f"Símbolos monitoreados: {AUTOSIGNAL_SYMBOLS}")
    
    # Log estado de módulos opcionales
    if TRAILING_STOPS_AVAILABLE:
        log_event("Módulo trailing stops: DISPONIBLE")
    else:
        log_event("Módulo trailing stops: NO DISPONIBLE", "WARNING")
    
    if MARKET_OPENING_AVAILABLE:
        log_event("Módulo market opening: DISPONIBLE")
    else:
        log_event("Módulo market opening: NO DISPONIBLE", "WARNING")
    
    if RECONNECTION_AVAILABLE:
        log_event("Módulo reconexión: DISPONIBLE")
    else:
        log_event("Módulo reconexión: NO DISPONIBLE", "WARNING")
    
    if SESSION_SUMMARY_AVAILABLE:
        log_event("Módulo resumen de sesión: DISPONIBLE")
    else:
        log_event("Módulo resumen de sesión: NO DISPONIBLE", "WARNING")
    
    log_event("Bot completamente inicializado y listo para operar")
    
    # Mostrar información del archivo de log
    intelligent_logger = get_intelligent_logger()
    current_log_file = intelligent_logger.current_log_file
    if current_log_file:
        log_filename = os.path.basename(current_log_file)
        log_event(f"📝 Archivo de log: {log_filename}")
        log_event(f"📁 Ruta completa: {current_log_file}")


# Simplified background loops for compatibility
async def _trailing_stops_loop_simple():
    """Simplified trailing stops loop"""
    await bot.wait_until_ready()
    logger.info('Trailing stops loop started')
    
    while True:
        try:
            if TRAILING_STOPS_AVAILABLE and trailing_manager:
                trailing_manager.update_all_trailing_stops()
            await asyncio.sleep(30)
        except Exception:
            logger.exception('Trailing stops loop crashed; retrying in 60s')
            await asyncio.sleep(60)


async def _market_opening_loop_simple():
    """
    Loop de alertas de apertura de mercado.
    Verifica cada 5 minutos si hay una apertura próxima y envía alertas
    al canal de signals en tres momentos: 30 min antes, 15 min antes,
    y 15 min después de abrir.
    """
    await bot.wait_until_ready()
    log_event("Sistema de alertas de apertura de mercado iniciado (verificación cada 5 min)")

    # Rastrear qué alertas ya se enviaron para no repetirlas
    # Clave: "{market}_{alert_type}_{fecha_hora_apertura_redondeada}"
    _sent_alerts: set = set()

    while True:
        try:
            await asyncio.sleep(300)  # verificar cada 5 minutos

            if not MARKET_OPENING_AVAILABLE or not market_opening_system:
                continue

            # Obtener próxima apertura en un thread separado (llama a MT5)
            def _get_opening():
                return market_opening_system.get_next_market_opening()

            market_name, opening_time, minutes_until = await asyncio.to_thread(_get_opening)

            if market_name is None or minutes_until is None:
                continue

            # ¿Hay que enviar alerta ahora?
            should_alert, alert_type = market_opening_system.should_send_alert(
                market_name, minutes_until
            )

            if not should_alert or alert_type is None:
                continue

            # Clave de deduplicación: misma alerta no se envía dos veces
            # Usamos la hora de apertura redondeada al minuto más cercano
            opening_key = opening_time.strftime('%Y%m%d%H%M') if opening_time else 'UNK'
            alert_key = f"{market_name}_{alert_type}_{opening_key}"

            if alert_key in _sent_alerts:
                continue  # ya enviada, saltar

            # Generar análisis pre-mercado para los pares activos de esta sesión
            session_info = market_opening_system.market_sessions.get(market_name, {})
            main_pairs = session_info.get('main_pairs', [])

            # Filtrar solo pares que tenemos activos en el bot
            active_pairs = [p for p in main_pairs if active_symbols.get(p, False)]

            def _generate_strategies():
                strategies = []
                for pair in active_pairs:
                    try:
                        result = market_opening_system.generate_opening_strategy(pair, market_name)
                        strategies.append(result)
                    except Exception as e:
                        logger.warning(f"Error generando estrategia de apertura para {pair}: {e}")
                return strategies

            strategies = await asyncio.to_thread(_generate_strategies)

            # Formatear y enviar mensaje
            message = market_opening_system.format_opening_alert(
                market_name, alert_type, strategies
            )

            channel = await _find_signals_channel()
            if channel:
                # Discord limita mensajes a 2000 chars; truncar si hace falta
                if len(message) > 1950:
                    message = message[:1950] + "\n…*(mensaje truncado)*"
                await channel.send(message)
                log_event(
                    f"📢 Alerta de apertura enviada: {market_name} | {alert_type} | "
                    f"{minutes_until:+d} min | pares: {active_pairs}"
                )
            else:
                logger.warning(
                    f"Market opening: no se encontró el canal '{SIGNALS_CHANNEL_NAME}'"
                )

            # Registrar como enviada para no repetir
            _sent_alerts.add(alert_key)

            # Limpiar alertas antiguas (más de 24h) para no acumular indefinidamente
            if len(_sent_alerts) > 100:
                _sent_alerts.clear()

        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception('Market opening loop crashed; retrying in 10 minutes')
            await asyncio.sleep(600)



async def _mt5_watchdog_loop():
    """
    Watchdog ligero para MT5: verifica la conexión cada 60s y reconecta
    si es necesario, sin bloquear el event loop de Discord.
    """
    await bot.wait_until_ready()
    log_event("MT5 watchdog iniciado (verificación cada 60s)")

    _consecutive_failures = 0

    while True:
        try:
            await asyncio.sleep(60)

            # Verificar conexión MT5 en un thread separado para no bloquear
            def _check_mt5():
                try:
                    import MetaTrader5 as mt5
                    info = mt5.terminal_info()
                    return info is not None
                except Exception:
                    return False

            is_connected = await asyncio.to_thread(_check_mt5)

            if not is_connected:
                _consecutive_failures += 1
                log_event(
                    f"⚠️ MT5 desconectado (intento {_consecutive_failures}). Reconectando...",
                    "WARNING"
                )

                def _reconnect():
                    try:
                        from mt5_client import initialize as mt5_init
                        creds = state.mt5_credentials
                        if creds.get('login') and creds.get('password') and creds.get('server'):
                            import MetaTrader5 as mt5
                            return mt5.initialize(
                                login=int(creds['login']),
                                password=creds['password'],
                                server=creds['server']
                            )
                        return mt5_init()
                    except Exception as e:
                        logger.error(f"MT5 reconnect error: {e}")
                        return False

                success = await asyncio.to_thread(_reconnect)

                if success:
                    _consecutive_failures = 0
                    log_event("✅ MT5 reconectado exitosamente")
                elif _consecutive_failures >= 5:
                    log_event(
                        "❌ MT5: 5 fallos de reconexión consecutivos. "
                        "Verifica que MT5 esté abierto.",
                        "ERROR"
                    )
                    # Send Discord notification to signals channel
                    try:
                        channel = await _find_signals_channel()
                        if channel:
                            await channel.send(
                                "🔴 **ALERTA MT5**: El bot ha fallado **5 veces consecutivas** al "
                                "intentar reconectarse a MetaTrader 5.\n"
                                "Las señales automáticas pueden estar interrumpidas. "
                                "Por favor verifica que MT5 esté abierto y conectado."
                            )
                    except Exception as notify_err:
                        logger.error(f"MT5 watchdog Discord notification error: {notify_err}")
                    _consecutive_failures = 0  # reset para no spamear
            else:
                _consecutive_failures = 0  # conexión ok

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"MT5 watchdog error: {e}")
            await asyncio.sleep(60)

# ======================
# WEEKLY SUMMARY LOOP
# ======================

async def _weekly_summary_loop():
    """
    Background task: sends a weekly summary embed to the signals channel
    every Monday between 08:00-09:00 UTC.
    """
    await bot.wait_until_ready()
    log_event("Weekly summary loop iniciado")

    _last_summary_monday: Optional[str] = None  # ISO date of last Monday we sent

    while True:
        try:
            await asyncio.sleep(3600)  # check every hour

            now = datetime.now(timezone.utc)
            # Monday = weekday 0, between 08:00 and 09:00
            if now.weekday() != 0 or not (8 <= now.hour < 9):
                continue

            today_str = now.date().isoformat()
            if _last_summary_monday == today_str:
                continue  # already sent this Monday

            # Gather last 7 days of signal history
            try:
                from services.dashboard import get_dashboard_service
                history = get_dashboard_service().get_signal_history(hours=168)
            except Exception as e:
                logger.error(f"Weekly summary: error getting history: {e}")
                continue

            total = len(history)
            wins = sum(1 for s in history if s.get('final_status') == 'win')
            losses = sum(1 for s in history if s.get('final_status') == 'loss')
            closed = wins + losses
            winrate = (wins / closed * 100) if closed > 0 else 0.0

            # Best/worst pair by win rate
            pair_stats: dict = {}
            for s in history:
                sym = s.get('symbol', 'UNKNOWN')
                fs = s.get('final_status')
                if sym not in pair_stats:
                    pair_stats[sym] = {'wins': 0, 'losses': 0}
                if fs == 'win':
                    pair_stats[sym]['wins'] += 1
                elif fs == 'loss':
                    pair_stats[sym]['losses'] += 1

            best_pair = worst_pair = '—'
            best_wr = -1.0; worst_wr = 101.0
            for sym, ps in pair_stats.items():
                c = ps['wins'] + ps['losses']
                if c == 0:
                    continue
                wr = ps['wins'] / c * 100
                if wr > best_wr:
                    best_wr = wr; best_pair = f"{sym} ({wr:.0f}%)"
                if wr < worst_wr:
                    worst_wr = wr; worst_pair = f"{sym} ({wr:.0f}%)"

            channel = await _find_signals_channel()
            if channel:
                embed = discord.Embed(
                    title="📊 Resumen Semanal — Trading Bot",
                    description=f"Semana del {(now - timedelta(days=7)).strftime('%d/%m')} al {now.strftime('%d/%m/%Y')}",
                    color=0x58a6ff,
                    timestamp=now,
                )
                embed.add_field(name="📈 Señales totales", value=str(total), inline=True)
                embed.add_field(name="✅ Wins", value=str(wins), inline=True)
                embed.add_field(name="❌ Losses", value=str(losses), inline=True)
                embed.add_field(name="🎯 Winrate", value=f"{winrate:.1f}%", inline=True)
                embed.add_field(name="🏆 Mejor par", value=best_pair, inline=True)
                embed.add_field(name="📉 Peor par", value=worst_pair, inline=True)
                embed.set_footer(text="Auto-Signal System | Resumen semanal automático")
                await channel.send(embed=embed)
                log_event(f"📊 Resumen semanal enviado: {total} señales, WR={winrate:.1f}%")

            _last_summary_monday = today_str

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Weekly summary loop error: {e}")
            await asyncio.sleep(3600)


# ======================
# SESSION SUMMARY LOOP
# ======================

async def _session_summary_loop():
    """
    Background task: envía un resumen de señales al final de cada sesión
    de mercado (London 17h UTC, New York 22h UTC).
    Verifica cada 5 minutos si alguna sesión acaba de cerrar.
    """
    await bot.wait_until_ready()
    log_event("Session summary loop iniciado")

    from session_summary import SESSIONS, session_summary as _ss

    while True:
        try:
            await asyncio.sleep(300)  # verificar cada 5 minutos

            for session_name in SESSIONS:
                should_send, key = _ss.should_send_summary(session_name)
                if not should_send:
                    continue

                # Obtener historial de señales de las últimas 24h
                try:
                    from services.dashboard import get_dashboard_service
                    # Obtenemos las horas de la sesión para filtrar
                    session_info = SESSIONS[session_name]
                    duration_h = session_info["close_utc"] - session_info["open_utc"]
                    history = get_dashboard_service().get_signal_history(
                        hours=max(duration_h, 10)
                    )
                except Exception as e:
                    logger.error(f"Session summary: error getting history: {e}")
                    history = []

                # Obtener estado del circuit breaker
                cb_status = None
                try:
                    from core.circuit_breaker import get_circuit_breaker
                    cb_status = get_circuit_breaker().get_status()
                except Exception as e:
                    logger.warning(f"Session summary: no se pudo obtener CB status: {e}")

                # Construir mensaje
                message = _ss.build_summary_message(
                    session_name=session_name,
                    signal_history=history,
                    circuit_breaker_status=cb_status,
                )

                # Enviar al canal
                channel = await _find_signals_channel()
                if channel:
                    await channel.send(message)
                    log_event(
                        f"📋 Resumen de sesión enviado: {session_name} | "
                        f"{len(history)} señales en historial"
                    )
                else:
                    logger.warning(
                        f"Session summary: no se encontró el canal '{SIGNALS_CHANNEL_NAME}'"
                    )

                # Marcar como enviado para no repetir
                _ss.mark_sent(key)

        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Session summary loop crashed; retrying in 5 minutes")
            await asyncio.sleep(300)


# ======================
# BACKTEST QUEUE LOOP
# ======================

async def _backtest_queue_loop():
    """
    Loop que procesa las tareas de backtesting y Monte Carlo que la app móvil
    o cualquier otro cliente inserte en la tabla backtest_tasks de SQLite.
    Verifica la cola cada 5 segundos.
    """
    await bot.wait_until_ready()
    log_event("Backtest queue loop iniciado (verificación cada 5 segundos)")

    db_path = os.path.join(os.path.dirname(__file__), 'bot_state.db')

    while True:
        try:
            await asyncio.sleep(5)

            # Buscar tareas PENDING
            def _check_queue():
                try:
                    conn = sqlite3.connect(db_path, timeout=10)
                    conn.row_factory = sqlite3.Row
                    c = conn.cursor()
                    c.execute(
                        "SELECT id, symbol, strategy, bars, cb_losses, cb_pause "
                        "FROM backtest_tasks WHERE status='PENDING' ORDER BY id ASC LIMIT 1"
                    )
                    row = c.fetchone()
                    if row:
                        task = dict(row)
                        # Cambiar a PROCESSING para reclamarla
                        c.execute(
                            "UPDATE backtest_tasks SET status='PROCESSING', updated_at=(datetime('now')) WHERE id=?",
                            (task['id'],)
                        )
                        conn.commit()
                        conn.close()
                        return task
                    conn.close()
                except Exception as e:
                    logger.error(f"[BacktestQueue] Error revisando cola: {e}")
                return None

            task = await asyncio.to_thread(_check_queue)
            if not task:
                continue

            log_event(f"🔄 Procesando backtest remoto ID {task['id']} ({task['symbol']} - {task['strategy']})")

            # Ejecutar el backtest en un hilo separado
            def _run_backtest(t):
                from core.replay_engine import ReplayEngine
                import json as _json

                try:
                    engine = ReplayEngine(
                        max_forward_bars=120,
                        cb_consecutive_losses=t['cb_losses'],
                        cb_pause_bars=t['cb_pause'],
                    )

                    stats = engine.run_replay(
                        symbol=t['symbol'],
                        bars=t['bars'],
                        strategy=t['strategy'],
                        timeframe='H1',
                        skip_duplicate_filter=True,
                    )

                    signals = engine.get_signals()
                    wins = [s for s in signals if s.result == 'WIN']
                    losses = [s for s in signals if s.result == 'LOSS']
                    closed = len(wins) + len(losses)
                    gp = sum(s.profit_pips or 0 for s in wins)
                    gl = abs(sum(s.profit_pips or 0 for s in losses))
                    pf = gp / gl if gl > 0 else float('inf')
                    pf_str = f"{pf:.2f}" if pf != float('inf') else "∞"

                    # Racha máxima de pérdidas
                    max_streak = cur = 0
                    for s in signals:
                        if s.result == 'LOSS':
                            cur += 1
                            max_streak = max(max_streak, cur)
                        elif s.result == 'WIN':
                            cur = 0

                    # Simulación Monte Carlo
                    mc_data = {"status": "omitted", "reason": "less_than_5_trades"}
                    if closed >= 5:
                        try:
                            from core.montecarlo import MonteCarlo, TradeRecord
                            mc_records = [TradeRecord.from_replay_signal(s) for s in signals if s.result in ('WIN', 'LOSS')]
                            ruin_threshold = -3000.0 if t['symbol'] == 'BTCEUR' else -300.0
                            mc = MonteCarlo(n_simulations=5000, ruin_threshold=ruin_threshold)
                            mc_report = mc.run(mc_records, symbol=t['symbol'])
                            
                            mc_data = {
                                "status": "success",
                                "prob_profitable": mc_report.prob_profitable,
                                "prob_ruin": mc_report.prob_ruin,
                                "ruin_threshold": ruin_threshold,
                                "p50_drawdown": mc_report.p50_drawdown,
                                "p75_drawdown": mc_report.p75_drawdown,
                                "p95_drawdown": mc_report.p95_drawdown,
                                "p5_equity": mc_report.p5_equity,
                                "p50_equity": mc_report.p50_equity,
                                "p95_equity": mc_report.p95_equity,
                            }
                        except Exception as mc_err:
                            logger.error(f"[BacktestQueue] Error MonteCarlo: {mc_err}")
                            mc_data = {"status": "error", "message": str(mc_err)}

                    # Serializar resultados
                    results = {
                        "symbol": t['symbol'],
                        "strategy": t['strategy'],
                        "bars_analyzed": stats.bars_analyzed,
                        "signals_final": stats.signals_final,
                        "buy_signals": stats.buy_signals,
                        "sell_signals": stats.sell_signals,
                        "tp_hits": stats.tp_hits,
                        "sl_hits": stats.sl_hits,
                        "pending": stats.pending,
                        "winrate": stats.winrate,
                        "profit_factor": pf_str,
                        "total_pips": stats.total_pips,
                        "avg_rr": stats.avg_rr,
                        "max_streak": max_streak,
                        "cb_activations": stats.cb_activations,
                        "bars_paused": stats.bars_paused,
                        "signals_blocked_by_cb": stats.signals_blocked_by_cb,
                        "monte_carlo": mc_data,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    # Guardar en base de datos como COMPLETED
                    conn = sqlite3.connect(db_path, timeout=10)
                    c = conn.cursor()
                    c.execute(
                        "UPDATE backtest_tasks "
                        "SET status='COMPLETED', results_json=?, updated_at=(datetime('now')) "
                        "WHERE id=?",
                        (_json.dumps(results, ensure_ascii=False), t['id'])
                    )
                    conn.commit()
                    conn.close()
                    return True
                except Exception as run_err:
                    logger.error(f"[BacktestQueue] Error ejecutando backtest ID {t['id']}: {run_err}")
                    try:
                        conn = sqlite3.connect(db_path, timeout=10)
                        c = conn.cursor()
                        c.execute(
                            "UPDATE backtest_tasks "
                            "SET status='FAILED', error_message=?, updated_at=(datetime('now')) "
                            "WHERE id=?",
                            (str(run_err), t['id'])
                        )
                        conn.commit()
                        conn.close()
                    except Exception as db_err:
                        logger.error(f"[BacktestQueue] Error guardando fallo en BD: {db_err}")
                    return False

            success = await asyncio.to_thread(_run_backtest, task)
            if success:
                log_event(f"✅ Backtest remoto ID {task['id']} procesado exitosamente")
            else:
                log_event(f"❌ Falló el backtest remoto ID {task['id']}", "ERROR")

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[BacktestQueue] Excepción general en el loop: {e}")
            await asyncio.sleep(10)


# ======================
# COMANDOS
# ======================

@bot.command()
async def signal(ctx, symbol: str = None):
    if ctx.author.id != AUTHORIZED_USER_ID:
        await ctx.send("⛔ No autorizado")
        return

    if KILL_SWITCH:
        await ctx.send("⛔ Kill switch activado. No se generan señales.")
        return

    # allow overriding the symbol from the command: `/signal BTCUSDT` or `!signal BTCUSDT`
    sym = (symbol or SYMBOL).upper()
    try:
        connect_mt5()
        df = get_candles(sym, TIMEFRAME, CANDLES)
    except Exception as e:
        await ctx.send(f"❌ Error conectando a MT5: {e}")
        return

    signal, df = _detect_signal_wrapper(df, symbol=sym)

    if not signal:
        await ctx.send("❌ No hay señal válida")
        return

    signal_id = max(state.pending_signals.keys(), default=0) + 1
    state.pending_signals[signal_id] = signal

    try:
        # Asegurar que el símbolo sea un string
        chart_symbol = signal.get('symbol', SYMBOL)
        if hasattr(chart_symbol, 'iloc'):
            chart_symbol = str(chart_symbol.iloc[0]) if len(chart_symbol) > 0 else SYMBOL
        elif not isinstance(chart_symbol, str):
            chart_symbol = str(chart_symbol)
        
        logger.debug(f"Generating chart for symbol: {chart_symbol}")
        chart = generate_chart(df, symbol=chart_symbol, signal=signal)
    except Exception as e:
        logger.error(f"Chart generation failed: {e}")
        chart = None

    text = (
        f"🟡 **SEÑAL DETECTADA** (ID {signal_id})\n"
        f"Activo: {signal['symbol']}\n"
        f"Tipo: {signal['type']}\n"
        f"Entrada: {signal['entry']:.5f}\n"
        f"SL: {signal['sl']:.5f}\n"
        f"TP: {signal['tp']:.5f}\n"
        f"⏱ Válida por 1 minuto\n"
        f"Explicación: {signal.get('explanation','-')}\n\n"
        "Comandos:\n"
        f"`/accept {signal_id}`\n"
        f"`/reject {signal_id}`\n"
    )

    if chart:
        await ctx.send(text, file=discord.File(chart))
        try:
            os.remove(chart)
        except Exception:
            pass
    else:
        await ctx.send(text)

@bot.command()
async def accept(ctx, signal_id: int):
    if ctx.author.id != AUTHORIZED_USER_ID:
        return
    # trades counter moved into `state`

    signal = state.pending_signals.get(signal_id)
    if not signal:
        await ctx.send("❌ Señal no encontrada")
        return

    if datetime.now(timezone.utc) > signal.get("expires", datetime.now(timezone.utc)):
        await ctx.send("⌛ Señal expirada")
        # BACKTEST TRACKING: Marcar como expirada
        if 'backtest_id' in signal:
            try:
                backtest_tracker.update_signal_status(signal['backtest_id'], "REJECTED", 
                                                    result="EXPIRED", notes="Señal expirada")
            except Exception as e:
                logger.error(f"Error actualizando backtest (expirada): {e}")
        del state.pending_signals[signal_id]
        return

    # Verificar límites antes de aceptar
    reset_period_if_needed()  # Verificar si necesitamos resetear período
    
    if state.trades_today >= MAX_TRADES_PER_DAY:
        await ctx.send("⛔ Límite de trades diarios alcanzado")
        # BACKTEST TRACKING: Marcar como rechazada por límite
        if 'backtest_id' in signal:
            try:
                backtest_tracker.update_signal_status(signal['backtest_id'], "REJECTED", 
                                                    result="LIMIT_REACHED", notes="Límite diario alcanzado")
            except Exception as e:
                logger.error(f"Error actualizando backtest (límite): {e}")
        del state.pending_signals[signal_id]
        return
    
    if state.trades_current_period >= MAX_TRADES_PER_PERIOD:
        period_status = get_period_status()
        await ctx.send(f"⛔ Límite de período alcanzado ({state.trades_current_period}/{MAX_TRADES_PER_PERIOD})\n"
                      f"📅 Período actual: {period_status['current_period']} UTC\n"
                      f"⏰ Próximo reinicio: {period_status['time_until_reset'].total_seconds()/3600:.1f}h")
        # BACKTEST TRACKING: Marcar como rechazada por límite de período
        if 'backtest_id' in signal:
            try:
                backtest_tracker.update_signal_status(signal['backtest_id'], "REJECTED", 
                                                    result="PERIOD_LIMIT", notes="Límite de período alcanzado")
            except Exception as e:
                logger.error(f"Error actualizando backtest (período): {e}")
        del state.pending_signals[signal_id]
        return
    # Incrementar contadores y persistir
    state.trades_today += 1
    state.trades_current_period += 1
    try:
        save_trades_today(state.trades_today)
    except Exception:
        logger.exception('Failed to save trades_today')

    # BACKTEST TRACKING: Marcar como aceptada
    if 'backtest_id' in signal:
        try:
            backtest_tracker.update_signal_status(signal['backtest_id'], "ACCEPTED", 
                                                notes="Señal aceptada manualmente")
        except Exception as e:
            logger.error(f"Error actualizando backtest (aceptada): {e}")

    # Aquí solo confirmamos; ejecución automática vendrá más tarde y solo tras confirmación adicional
    await ctx.send(f"✅ Señal {signal_id} aceptada (lista para ejecución/manual). Trades hoy: {state.trades_today}/{MAX_TRADES_PER_DAY}")
    del state.pending_signals[signal_id]

@bot.command()
async def reject(ctx, signal_id: int):
    if ctx.author.id != AUTHORIZED_USER_ID:
        return
    if signal_id in state.pending_signals:
        signal = state.pending_signals[signal_id]
        # BACKTEST TRACKING: Marcar como rechazada
        if 'backtest_id' in signal:
            try:
                backtest_tracker.update_signal_status(signal['backtest_id'], "REJECTED", 
                                                    result="USER_REJECTED", notes="Señal rechazada manualmente")
            except Exception as e:
                logger.error(f"Error actualizando backtest (rechazada): {e}")
        del state.pending_signals[signal_id]
        await ctx.send(f"❌ Señal {signal_id} rechazada")

@bot.command()
async def close_signal(ctx, backtest_id: int, result: str, profit_loss: float = 0.0, close_price: float = 0.0):
    """Simula el cierre de una señal para testing del backtesting (WIN/LOSS/BREAKEVEN)"""
    if ctx.author.id != AUTHORIZED_USER_ID:
        return
    
    if result.upper() not in ['WIN', 'LOSS', 'BREAKEVEN']:
        await ctx.send("❌ Resultado debe ser WIN, LOSS o BREAKEVEN")
        return
    
    try:
        success = backtest_tracker.update_signal_status(
            backtest_id, 
            "CLOSED", 
            result=result.upper(),
            profit_loss=profit_loss,
            close_price=close_price,
            notes=f"Cerrada manualmente para testing"
        )
        
        if success:
            await ctx.send(f"✅ Señal {backtest_id} cerrada: {result.upper()} | P&L: {profit_loss} EUR")
        else:
            await ctx.send(f"❌ No se encontró la señal {backtest_id}")
            
    except Exception as e:
        await ctx.send(f"❌ Error cerrando señal: {e}")

# Backtest stats command moved to services/commands.py

# Backtest report command moved to services/commands.py

@bot.command()
async def chart(ctx):
    if ctx.author.id != AUTHORIZED_USER_ID:
        return
    try:
        connect_mt5()
        df = get_candles(SYMBOL, TIMEFRAME, CANDLES)
    except Exception as e:
        await ctx.send(f"❌ Error obteniendo datos: {e}")
        return

    try:
        filename = generate_chart(df)
        await ctx.send("📊 Gráfico actual", file=discord.File(filename))
    except Exception as e:
        await ctx.send(f"❌ Error generando gráfico: {e}")


@bot.command(name="pairs")
async def pairs_command(ctx):
    """Muestra y permite alternar pares activos mediante botones (solo usuario autorizado)."""
    if ctx.author.id != AUTHORIZED_USER_ID:
        return

    content = await build_pairs_overview_text()
    view = PairToggleView(timeout=300)
    msg = await ctx.send(content, view=view)
    view.message = msg


# ======================
# Slash commands (app commands)
# ======================

# Large slash commands moved to services/commands.py


async def _find_signals_channel():
    # find first channel matching SIGNALS_CHANNEL_NAME across guilds
    for g in bot.guilds:
        for ch in g.text_channels:
            if ch.name == SIGNALS_CHANNEL_NAME:
                return ch
    return None


# Auto-signal loop moved to services/autosignals.py


@bot.tree.command(name="status")
async def slash_status(interaction: discord.Interaction):
    """Muestra estado del bot, aplicación y sincronización de comandos."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    app_id = bot.application_id or bot.user.id
    in_guild = False
    guild_info = "(no GUILD_ID configured)"
    if GUILD_ID:
        try:
            gid = int(GUILD_ID)
            guild = bot.get_guild(gid)
            in_guild = guild is not None
            guild_info = f"Guild ID configured: {gid}. Bot is in guild: {in_guild}"
        except Exception:
            guild_info = f"Configured GUILD_ID is invalid: {GUILD_ID}"

    # fetch registered commands for the guild if possible
    cmds = []
    try:
        if GUILD_ID and in_guild:
            cmds = await bot.tree.fetch_commands(guild=discord.Object(id=int(GUILD_ID)))
        else:
            cmds = await bot.tree.fetch_commands()
    except Exception:
        cmds = []

    cmd_names = ", ".join([c.name for c in cmds]) if cmds else "(no commands found or fetch failed)"

    lines = [
        f"Application ID: {app_id}",
        guild_info,
        f"Registered commands: {cmd_names}",
        "\nIf the commands are not visible in the server, ensure the bot was invited with the `applications.commands` scope using the invite URL printed in the bot logs."
    ]

    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@bot.tree.command(name="autosignals")
@discord.app_commands.describe(mode="on, off o status (por defecto: status)")
async def slash_autosignals(
    interaction: discord.Interaction,
    mode: str = "status",
):
    """Ver o cambiar el estado del escaneo automático de señales (solo admin)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    m = mode.lower().strip()

    if m in ("on", "off"):
        new_value = (m == "on")
        state.autosignals = new_value
        try:
            save_autosignals_state(new_value)
        except Exception as e:
            await interaction.response.send_message(
                f"⚠️ Autosignals cambiado a **{m}**, pero falló al guardar en BD: {e}",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"✅ Autosignals ahora está **{'ON' if new_value else 'OFF'}**",
            ephemeral=True,
        )
        return

    # modo "status" (o cualquier otra cosa)
    status_str = "ON" if state.autosignals else "OFF"
    await interaction.response.send_message(
        f"🔍 Autosignals está actualmente **{status_str}**",
        ephemeral=True,
    )


async def build_pairs_overview_text() -> str:
    symbols = ["EURUSD", "XAUUSD", "BTCEUR"]
    lines: list[str] = []

    # Intentar conectar a MT5 una sola vez
    mt5_error: Optional[str] = None
    try:
        connect_mt5()
    except Exception as e:
        mt5_error = str(e)

    for sym in symbols:
        active = active_symbols.get(sym, False)
        status_emoji = "✅" if active else "❌"
        line = f"{sym} {status_emoji}"
        if sym == "BTCEUR":
            btceur_status = symbol_health.get("BTCEUR", {}).get("status", "OK")
            if btceur_status in ("ERROR", "DISABLED"):
                line += f" ⚠️ ({btceur_status})"
        lines.append(line)

        if not active:
            lines.append("  • Estado: Inactivo (no se evalúan señales)")
            lines.append("")
            continue

        if mt5_error is not None:
            lines.append(f"  • Error conectando a MT5: {mt5_error}")
            lines.append("")
            continue

        # Obtener datos de mercado
        try:
            df = get_candles(sym, TIMEFRAME, CANDLES)
        except Exception as e:
            lines.append(f"  • Error obteniendo datos: {e}")
            lines.append("")
            continue

        try:
            cfg = RULES_CONFIG.get(sym.upper(), {}) or {}
            strat = cfg.get("strategy", "ema50_200")

            # HARDENING BTCEUR: evitar estrategias genéricas
            if sym == "BTCEUR" and "btceur" not in strat.lower():
                logger.error("[BTCEUR FIX] Strategy corregida automáticamente en /pairs: %s → btceur_simple", strat)
                strat = "btceur_simple"

            # Señal básica
            basic_signal, df_with_indicators = detect_signal(
                df, strategy=strat, config=cfg, symbol=sym
            )

            # Señal avanzada (engine completo)
            advanced_signal, df2, adv_info = detect_signal_advanced(
                df,
                strategy=strat,
                config=cfg,
                current_balance=5000.0,
                symbol=sym,
            )
        except Exception as e:
            lines.append(f"  • Error evaluando señal: {e}")
            lines.append("")
            continue

        # Precio actual formateado por símbolo
        try:
            last_price = float(df["close"].iloc[-1])
            if sym == "XAUUSD":
                price_str = f"{last_price:.2f}"
            elif sym == "BTCEUR":
                price_str = f"{last_price:.0f}"
            else:
                price_str = f"{last_price:.5f}"
        except Exception:
            price_str = "N/A"

        basic_ok = basic_signal is not None
        adv_ok = advanced_signal is not None

        confidence = "N/A"
        score = 0.0
        reason = None
        if isinstance(adv_info, dict):
            confidence = adv_info.get("confidence", "N/A")
            score = float(adv_info.get("score", 0.0))
            reason = adv_info.get("rejection_reason") or adv_info.get("reason")

        lines.append(f"  • Precio: {price_str}")
        lines.append(f"  • Estrategia: {strat}")
        lines.append(f"  • Señal básica: {'✅' if basic_ok else '❌'}")
        lines.append(f"  • Señal avanzada: {'✅' if adv_ok else '❌'}")
        lines.append(f"  • Confianza: {confidence} | Score: {score:.2f}")
        if not adv_ok and reason:
            lines.append(f"  • Motivo rechazo: {str(reason)[:100]}")
        lines.append("")

    if mt5_error is not None:
        lines.append(
            "⚠️ No se pudo conectar a MT5; solo se muestra el estado de activación de los pares."
        )

    return "\n".join(lines).strip()


class PairToggleView(discord.ui.View):
    """Vista con botones para activar/desactivar pares principales."""

    def __init__(self, *, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.message: Optional[discord.Message] = None

    async def _toggle_symbol(self, interaction: discord.Interaction, symbol: str):
        if interaction.user.id != AUTHORIZED_USER_ID:
            await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
            return

        try:
            current = active_symbols.get(symbol.upper(), False)
            new_value = not current
            active_symbols[symbol.upper()] = new_value
            if symbol.upper() == "BTCEUR":
                if not new_value:
                    set_btceur_health(status="DISABLED")
                else:
                    validate_btceur_strategy()
        except Exception as e:
            logger.error(f"Error alternando estado de {symbol}: {e}")
            await interaction.response.send_message(
                f"❌ Error cambiando estado de {symbol}", ephemeral=True
            )
            return

        # Recalcular el resumen completo para reflejar el nuevo estado
        try:
            content = await build_pairs_overview_text()
            await interaction.response.edit_message(content=content, view=self)
        except Exception as e:
            logger.error(f"Error actualizando mensaje de pares: {e}")
            # Fallback para no dejar la interacción sin respuesta
            await interaction.followup.send(
                "❌ No se pudo actualizar el mensaje de pares.", ephemeral=True
            )

    @discord.ui.button(label="EURUSD", style=discord.ButtonStyle.primary)
    async def eurusd_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_symbol(interaction, "EURUSD")

    @discord.ui.button(label="XAUUSD", style=discord.ButtonStyle.primary)
    async def xauusd_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_symbol(interaction, "XAUUSD")

    @discord.ui.button(label="BTCEUR", style=discord.ButtonStyle.primary)
    async def btceur_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_symbol(interaction, "BTCEUR")

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except Exception as e:
                logger.error(f"Error desactivando botones de pares tras timeout: {e}")


@bot.tree.command(name="pairs")
async def slash_pairs(interaction: discord.Interaction):
    """Muestra y permite alternar los pares activos del bot (solo admin)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)

    content = await build_pairs_overview_text()
    view = PairToggleView(timeout=300)
    msg = await interaction.followup.send(content, view=view)
    view.message = msg


@bot.tree.command(name="logs_info")
async def slash_logs_info(interaction: discord.Interaction):
    """Muestra información del archivo de logs actual (solo admin)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    intelligent_logger = get_intelligent_logger()
    current_log_file = intelligent_logger.current_log_file
    if current_log_file and os.path.exists(current_log_file):
        # Obtener información del archivo
        file_size = os.path.getsize(current_log_file)
        file_size_mb = file_size / (1024 * 1024)
        
        # Obtener timestamp de creación del archivo
        creation_time = datetime.fromtimestamp(os.path.getctime(current_log_file))
        
        # Contar líneas del archivo
        try:
            with open(current_log_file, 'r', encoding='utf-8') as f:
                line_count = sum(1 for _ in f)
        except Exception:
            line_count = "Error contando líneas"
        
        lines = [
            "📝 **INFORMACIÓN DEL ARCHIVO DE LOGS**",
            "",
            f"📁 **Archivo:** `{os.path.basename(current_log_file)}`",
            f"📂 **Ruta:** `{current_log_file}`",
            f"📊 **Tamaño:** {file_size_mb:.2f} MB ({file_size:,} bytes)",
            f"📄 **Líneas:** {line_count:,}" if isinstance(line_count, int) else f"📄 **Líneas:** {line_count}",
            f"🕐 **Creado:** {creation_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"⏱️ **Duración:** {datetime.now() - creation_time}",
            "",
            "💡 **Nota:** Este archivo contiene TODA la salida de la terminal del bot."
        ]
        
        await interaction.response.send_message("\n".join(lines), ephemeral=True)
    else:
        await interaction.response.send_message("❌ No se encontró información del archivo de logs actual", ephemeral=True)


@bot.tree.command(name="positions")
async def slash_positions(interaction: discord.Interaction):
    """Lista posiciones abiertas (solo usuario autorizado)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    try:
        connect_mt5()
        pos = list_positions()
        if not pos:
            await interaction.followup.send("(Sin posiciones abiertas)", ephemeral=True)
            return
        lines = [f"Tickets abiertos: {len(pos)}"]
        for p in pos:
            lines.append(f"- #{p['ticket']} {p['symbol']} {p['type']} vol={p['volume']} open={p['price_open']:.5f} profit={p['profit']:.2f}")
        await interaction.followup.send("\n".join(lines), ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error obteniendo posiciones: {e}")


@bot.tree.command(name="close_position")
@discord.app_commands.describe(ticket="Ticket de la posición a cerrar (número)")
async def slash_close_position(interaction: discord.Interaction, ticket: int):
    """Cierra una posición por ticket (solo usuario autorizado)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    try:
        connect_mt5()
        res = close_position(ticket)
        await interaction.followup.send(f"✅ Close request submitted: {res}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error cerrando posición: {e}", ephemeral=True)


@bot.tree.command(name="close_positions_ui")
async def slash_close_positions_ui(interaction: discord.Interaction):
    """Muestra un desplegable con posiciones abiertas y permite cerrar una (solo autorizado)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    try:
        connect_mt5()
        pos = list_positions()
        if not pos:
            await interaction.followup.send("(Sin posiciones abiertas)", ephemeral=True)
            return

        # Build select options
        options = []
        for p in pos:
            label = f"#{p['ticket']} {p['symbol']} {p['type']} vol={p['volume']}"
            desc = f"open={p['price_open']:.5f} profit={p['profit']:.2f}"
            options.append(discord.SelectOption(label=label, description=desc, value=str(p['ticket'])))

        class PositionSelect(discord.ui.Select):
            def __init__(self, opts):
                super().__init__(placeholder='Selecciona una posición a cerrar...', min_values=1, max_values=1, options=opts)

            async def callback(self, select_interaction: discord.Interaction):
                if select_interaction.user.id != AUTHORIZED_USER_ID:
                    await select_interaction.response.send_message('⛔ No autorizado', ephemeral=True)
                    return
                ticket = int(self.values[0])

                # confirmation view
                class ConfirmCloseView(discord.ui.View):
                    def __init__(self, ticket):
                        super().__init__(timeout=60)
                        self.ticket = ticket

                    @discord.ui.button(label='Confirmar cierre', style=discord.ButtonStyle.danger)
                    async def confirm(self, button_inter: discord.Interaction, btn: discord.ui.Button):
                        if button_inter.user.id != AUTHORIZED_USER_ID:
                            await button_inter.response.send_message('⛔ No autorizado', ephemeral=True)
                            return
                        await button_inter.response.defer(thinking=True)
                        try:
                            res = close_position(self.ticket)
                            await button_inter.followup.send(f'✅ Close request submitted: {res}', ephemeral=True)
                        except Exception as e:
                            await button_inter.followup.send(f'❌ Error cerrando posición: {e}', ephemeral=True)

                    @discord.ui.button(label='Cancelar', style=discord.ButtonStyle.secondary)
                    async def cancel(self, button_inter: discord.Interaction, btn: discord.ui.Button):
                        await button_inter.response.send_message('Operación cancelada', ephemeral=True)

                await select_interaction.response.send_message(f'¿Cerrar posición #{ticket}?', view=ConfirmCloseView(ticket), ephemeral=True)

        view = discord.ui.View()
        view.add_item(PositionSelect(options))
        await interaction.followup.send('Selecciona la posición a cerrar:', view=view, ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ Error mostrando posiciones: {e}", ephemeral=True)


@bot.tree.command(name="signal")
@discord.app_commands.describe(symbol="Símbolo/activo (ej: EURUSD, BTCUSDT). Si se omite usa DEFAULT_STRATEGY simbolo por defecto en .env")
@log_discord_command
async def slash_signal(interaction: discord.Interaction, symbol: str = ''):
    """Detecta una señal usando MT5 y publica la propuesta (solo admin)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    if KILL_SWITCH:
        await interaction.response.send_message("⛔ Kill switch activado. No se generan señales.", ephemeral=True)
        return

    # defer only if the interaction hasn't been responded to yet
    if not interaction.response.is_done():
        await interaction.response.defer(thinking=True)

    sym = (symbol or SYMBOL).upper()
    try:
        connect_mt5()
        df = get_candles(sym, TIMEFRAME, CANDLES)
    except Exception as e:
        await interaction.followup.send(f"❌ Error conectando a MT5: {e}")
        return

    signal, df, risk_info = _detect_signal_wrapper(df, symbol=sym)
    if not signal:
        rejection_reason = risk_info.get('reason', 'No hay señal válida')
        await interaction.followup.send(f"❌ {rejection_reason}")
        return

    signal_id = max(state.pending_signals.keys(), default=0) + 1
    state.pending_signals[signal_id] = signal

    # compute suggested lot and risk/reward
    lot, risk_amount, rr = compute_suggested_lot(signal)
    lot_text = f"Sugerido: {lot:.2f} lot" if lot else "Sugerido: N/A"
    risk_text = f"Riesgo aprox: {risk_amount:.2f} ({os.getenv('MT5_RISK_PCT','0.5')}%)" if risk_amount else "Riesgo aprox: N/A"
    rr_text = f"RR ≈ {rr:.2f}" if rr else "RR: N/A"

    def _fmt(v, nd=5):
        try:
            return f"{float(v):.{nd}f}"
        except Exception:
            return "N/A"

    entry_s = _fmt(signal.get('entry'))
    sl_s = _fmt(signal.get('sl'))
    tp_s = _fmt(signal.get('tp'))

    text = (
        f"🟡 **SEÑAL DETECTADA** (ID {signal_id})\n"
        f"Activo: {signal.get('symbol')}\n"
        f"Tipo: {signal.get('type')}\n"
        f"Entrada: {entry_s}\n"
        f"SL: {sl_s}\n"
        f"TP: {tp_s}\n"
        f"{lot_text} | {risk_text} | {rr_text}\n"
        f"⏱ Válida por 1 minuto\n"
        f"Explicación: {signal.get('explanation','-')}\n\n"
        "Decide:"
    )

    # Buttons view
    class SignalView(discord.ui.View):
        def __init__(self, sid):
            super().__init__(timeout=60)
            self.sid = sid

        @discord.ui.button(label='Aceptar', style=discord.ButtonStyle.success)
        async def accept_button(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
            if interaction_btn.user.id != AUTHORIZED_USER_ID:
                await interaction_btn.response.send_message('⛔ No autorizado', ephemeral=True)
                return
            sig = state.pending_signals.get(self.sid)
            if not sig:
                await interaction_btn.response.send_message('❌ Señal no encontrada o ya procesada', ephemeral=True)
                return
            if datetime.now(timezone.utc) > sig.get('expires', datetime.now(timezone.utc)):
                del state.pending_signals[self.sid]
                await interaction_btn.response.send_message('⌛ Señal expirada', ephemeral=True)
                return

            # Show execution choices: Ejecutar ahora / Personalizar / Cancelar
            class ExecModal(discord.ui.Modal, title='Ejecutar señal - Personalizar'):
                lot = discord.ui.TextInput(label='Lot (ej: 0.01)', required=False, style=discord.TextStyle.short, placeholder='Dejar vacío para usar % de riesgo')
                risk_pct = discord.ui.TextInput(label='Riesgo % (ej: 0.5)', required=False, style=discord.TextStyle.short, placeholder='Porcentaje de balance a arriesgar')

                def __init__(self, sid):
                    super().__init__()
                    self.sid = sid

                async def on_submit(self, interaction_modal: discord.Interaction):
                    # perform execution with custom params
                    s = state.pending_signals.get(self.sid)
                    if not s:
                        await interaction_modal.response.send_message('❌ Señal no encontrada', ephemeral=True)
                        return
                    # determine lot
                    lot_val = None
                    try:
                        if self.risk_pct.value:
                            rp = float(self.risk_pct.value)
                            lot_val, _, _ = compute_suggested_lot(s, risk_pct=rp)
                        elif self.lot.value:
                            lot_val = float(self.lot.value)
                    except Exception as e:
                        await interaction_modal.response.send_message(f'❌ Parámetros inválidos: {e}', ephemeral=True)
                        return

                    if not lot_val:
                        await interaction_modal.response.send_message('❌ No se pudo calcular un lot válido', ephemeral=True)
                        return

                    # place order
                    try:
                        # Asegurar que el símbolo sea un string válido
                        symbol_str = s.get('symbol', 'EURUSD')
                        if hasattr(symbol_str, 'iloc'):
                            symbol_str = str(symbol_str.iloc[0]) if len(symbol_str) > 0 else 'EURUSD'
                        elif not isinstance(symbol_str, str):
                            symbol_str = str(symbol_str)
                        
                        logger.debug(f"Ejecutando orden: {symbol_str} {s.get('type')} {lot_val}")
                        res = place_order(symbol_str, s['type'], lot_val, price=s.get('entry'), sl=s.get('sl'), tp=s.get('tp'))
                        # increment trades_today and remove pending
                        state.trades_today += 1
                        try:
                            save_trades_today(state.trades_today)
                        except Exception:
                            logger.exception('Failed to save trades_today')
                        if self.sid in state.pending_signals:
                            del state.pending_signals[self.sid]
                        await interaction_modal.response.send_message(f'✅ Orden ejecutada: {res}', ephemeral=True)
                    except Exception as e:
                        await interaction_modal.response.send_message(f'❌ Error ejecutando orden: {e}', ephemeral=True)

            class ExecView(discord.ui.View):
                def __init__(self, sid):
                    super().__init__(timeout=60)
                    self.sid = sid

                @discord.ui.button(label='Ejecutar ahora', style=discord.ButtonStyle.success)
                async def execute_now(self, interaction_exec: discord.Interaction, button: discord.ui.Button):
                    if interaction_exec.user.id != AUTHORIZED_USER_ID:
                        await interaction_exec.response.send_message('⛔ No autorizado', ephemeral=True)
                        return
                    s = state.pending_signals.get(self.sid)
                    if not s:
                        await interaction_exec.response.send_message('❌ Señal no encontrada', ephemeral=True)
                        return
                    # compute default risk per type env override
                    type_key = s.get('type','').upper()
                    env_key = f'MT5_RISK_{type_key}'
                    try:
                        rp = float(os.getenv(env_key, os.getenv('MT5_RISK_PCT', '0.5')))
                    except Exception:
                        rp = 0.5
                    lot_val, _, _ = compute_suggested_lot(s, risk_pct=rp)
                    if not lot_val:
                        await interaction_exec.response.send_message('❌ No se pudo calcular lot sugerido', ephemeral=True)
                        return
                    try:
                        # Asegurar que el símbolo sea un string válido
                        symbol_str = s.get('symbol', 'EURUSD')
                        if hasattr(symbol_str, 'iloc'):
                            symbol_str = str(symbol_str.iloc[0]) if len(symbol_str) > 0 else 'EURUSD'
                        elif not isinstance(symbol_str, str):
                            symbol_str = str(symbol_str)
                        
                        logger.debug(f"Ejecutando orden automática: {symbol_str} {s.get('type')} {lot_val}")
                        res = place_order(symbol_str, s['type'], lot_val, price=s.get('entry'), sl=s.get('sl'), tp=s.get('tp'))
                        state.trades_today += 1
                        try:
                            save_trades_today(state.trades_today)
                        except Exception:
                            logger.exception('Failed to save trades_today')
                        if self.sid in state.pending_signals:
                            del state.pending_signals[self.sid]
                        await interaction_exec.response.send_message(f'✅ Orden ejecutada: {res}', ephemeral=True)
                    except Exception as e:
                        await interaction_exec.response.send_message(f'❌ Error ejecutando orden: {e}', ephemeral=True)

                @discord.ui.button(label='Personalizar', style=discord.ButtonStyle.primary)
                async def customize(self, interaction_exec: discord.Interaction, button: discord.ui.Button):
                    if interaction_exec.user.id != AUTHORIZED_USER_ID:
                        await interaction_exec.response.send_message('⛔ No autorizado', ephemeral=True)
                        return
                    await interaction_exec.response.send_modal(ExecModal(self.sid))

                @discord.ui.button(label='Cancelar', style=discord.ButtonStyle.secondary)
                async def cancel(self, interaction_exec: discord.Interaction, button: discord.ui.Button):
                    await interaction_exec.response.send_message('Acción cancelada. La señal permanece pendiente.', ephemeral=True)

            await interaction_btn.response.send_message('Selecciona acción: ejecutar ahora, personalizar lotaje o cancelar.', view=ExecView(self.sid), ephemeral=True)

        @discord.ui.button(label='Rechazar', style=discord.ButtonStyle.danger)
        async def reject_button(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
            if interaction_btn.user.id != AUTHORIZED_USER_ID:
                await interaction_btn.response.send_message('⛔ No autorizado', ephemeral=True)
                return
            if self.sid in state.pending_signals:
                del state.pending_signals[self.sid]
                await interaction_btn.response.send_message(f'❌ Señal {self.sid} rechazada', ephemeral=True)
            else:
                await interaction_btn.response.send_message('❌ Señal no encontrada', ephemeral=True)

    view = SignalView(signal_id)

    try:
        # Asegurar que el símbolo sea un string
        chart_symbol = signal.get('symbol', SYMBOL)
        if hasattr(chart_symbol, 'iloc'):
            chart_symbol = str(chart_symbol.iloc[0]) if len(chart_symbol) > 0 else SYMBOL
        elif not isinstance(chart_symbol, str):
            chart_symbol = str(chart_symbol)
        
        logger.debug(f"Generating slash signal chart for symbol: {chart_symbol}")
        chart_file = generate_chart(df, symbol=chart_symbol, signal=signal)
    except Exception as e:
        logger.error(f"Slash signal chart generation failed: {e}")
        chart_file = None

    if chart_file:
        await interaction.followup.send(text, file=discord.File(chart_file), view=view)
        try:
            os.remove(chart_file)
        except Exception:
            pass
    else:
        await interaction.followup.send(text, view=view)


@bot.tree.command(name="chart")
@discord.app_commands.describe(symbol="Símbolo/activo (ej: EURUSD, XAUUSD, BTCEUR)", timeframe="Timeframe (M1,M5,M15,M30,H1,H4,D1)", candles="Número de velas a mostrar")
async def slash_chart(interaction: discord.Interaction, symbol: str = 'EURUSD', timeframe: str = 'H1', candles: int = 100):
    """Genera un gráfico PNG con las últimas velas (solo admin)."""
    # Log del comando ejecutado
    log_event(f"🎮 COMMAND: /chart {symbol} {timeframe} {candles} | User: {interaction.user.id} ({interaction.user.display_name})")
    
    if interaction.user.id != AUTHORIZED_USER_ID:
        log_event(f"❌ COMMAND REJECTED: /chart | User: {interaction.user.id} | Reason: No autorizado")
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    symbol = symbol.upper()
    # restrict charts to symbols that have rules (only show charts for these pairs)
    ALLOWED = ['EURUSD','XAUUSD','BTCEUR']
    if symbol not in ALLOWED:
        log_event(f"❌ COMMAND REJECTED: /chart | Symbol: {symbol} | Reason: Símbolo no soportado")
        await interaction.response.send_message(f"Símbolo no soportado o no disponible: {symbol}", ephemeral=True)
        return

    TF_MAP = {
        'M1': mt5.TIMEFRAME_M1,
        'M5': mt5.TIMEFRAME_M5,
        'M15': mt5.TIMEFRAME_M15,
        'M30': mt5.TIMEFRAME_M30,
        'H1': mt5.TIMEFRAME_H1,
        'H4': mt5.TIMEFRAME_H4,
        'D1': mt5.TIMEFRAME_D1,
    }

    tf = TF_MAP.get(timeframe.upper())
    if tf is None:
        await interaction.response.send_message(f"Timeframe no reconocido: {timeframe}", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)

    try:
        connect_mt5()
        df = get_candles(symbol, tf, candles)
    except Exception as e:
        await interaction.followup.send(f"❌ Error obteniendo datos: {e}")
        return

    try:
        filename = generate_chart(df, symbol=symbol, title=f"{symbol} {timeframe}")
        await interaction.followup.send("📊 Gráfico actual", file=discord.File(filename))
        log_event(f"✅ COMMAND SUCCESS: /chart {symbol} {timeframe} | Chart generated and sent")
        # remove file after sending to avoid stale reuse
        try:
            import os
            os.remove(filename)
        except Exception:
            pass
    except Exception as e:
        log_event(f"❌ COMMAND ERROR: /chart {symbol} {timeframe} | Error: {e}")
        await interaction.followup.send(f"❌ Error generando gráfico: {e}")


# Large autosignals command moved to services/commands.py


@bot.tree.command(name="set_mt5_credentials")
async def slash_set_mt5_credentials(interaction: discord.Interaction):
    """Abre un modal para introducir credenciales MT5 (slash)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    # show the same modal class used for the text command
    await interaction.response.send_modal(MT5CredentialsModal())


# Pairs config command moved to services/commands.py


# Market overview command moved to services/commands.py


@bot.tree.command(name="set_strategy")
@discord.app_commands.describe(
    symbol="Símbolo (EURUSD, XAUUSD, BTCEUR)",
    strategy="Estrategia disponible"
)
@discord.app_commands.choices(
    symbol=[
        discord.app_commands.Choice(name="🇪🇺 EURUSD", value="EURUSD"),
        discord.app_commands.Choice(name="🥇 XAUUSD", value="XAUUSD"),
        discord.app_commands.Choice(name="₿ BTCEUR", value="BTCEUR")
    ],
    strategy=[
        discord.app_commands.Choice(name="EURUSD Avanzada", value="eurusd_advanced"),
        discord.app_commands.Choice(name="XAUUSD Avanzada", value="xauusd_advanced"),
        discord.app_commands.Choice(name="BTCEUR Avanzada", value="btceur_advanced"),
        discord.app_commands.Choice(name="Breakout Confirmación", value="breakout_confirmation"),
        discord.app_commands.Choice(name="Reversión Media", value="mean_reversion"),
        discord.app_commands.Choice(name="EMA 50/200", value="ema50_200")
    ]
)
async def slash_set_strategy(interaction: discord.Interaction, symbol: str, strategy: str):
    """Cambia la estrategia para un símbolo específico (solo admin)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    symbol = symbol.upper()
    strategy = strategy.lower()
    
    # Verificar que es uno de los pares principales
    main_pairs = ['EURUSD', 'XAUUSD', 'BTCEUR']
    if symbol not in main_pairs:
        await interaction.response.send_message(
            f"❌ Solo se pueden configurar los pares principales: {', '.join(main_pairs)}", 
            ephemeral=True
        )
        return
    
    # Actualizar configuración
    if symbol not in RULES_CONFIG:
        RULES_CONFIG[symbol] = {}
    
    old_strategy = RULES_CONFIG[symbol].get('strategy', 'N/A')
    RULES_CONFIG[symbol]['strategy'] = strategy
    
    # Guardar en archivo
    try:
        with open(RULES_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(RULES_CONFIG, f, indent=2, ensure_ascii=False)
        
        embed = discord.Embed(
            title="✅ Estrategia Actualizada",
            description=f"Configuración cambiada para **{symbol}**",
            color=0x00ff00
        )
        
        emoji = {"EURUSD": "🇪🇺", "XAUUSD": "🥇", "BTCEUR": "₿"}.get(symbol, "📈")
        
        embed.add_field(
            name=f"{emoji} **{symbol}**",
            value=(
                f"**Estrategia anterior:** `{old_strategy}`\n"
                f"**Nueva estrategia:** `{strategy}`\n"
                f"**Estado:** {'🟢 Activo' if RULES_CONFIG[symbol].get('enabled', False) else '🔴 Inactivo'}"
            ),
            inline=False
        )
        
        embed.set_footer(text="Los cambios se aplicarán en la próxima señal automática")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error guardando configuración: {e}", ephemeral=True)


@bot.tree.command(name="strategy_performance")
@discord.app_commands.describe(days="Días para analizar (por defecto: 7)")
async def slash_strategy_performance(interaction: discord.Interaction, days: int = 7):
    """Muestra performance por estrategia (solo admin)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    
    if risk_manager is None:
        await interaction.followup.send("❌ Gestor de riesgo no disponible")
        return
    
    try:
        # Obtener trades por estrategia
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        conn = sqlite3.connect(risk_manager.db_path)
        c = conn.cursor()
        
        c.execute('''SELECT strategy, COUNT(*) as total_trades,
                            SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                            SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
                            SUM(COALESCE(pnl, 0)) as total_pnl,
                            AVG(CASE WHEN result = 'win' THEN pnl END) as avg_win,
                            AVG(CASE WHEN result = 'loss' THEN pnl END) as avg_loss
                     FROM trades_history 
                     WHERE timestamp > ? AND strategy IS NOT NULL
                     GROUP BY strategy''', (cutoff_date,))
        
        results = c.fetchall()
        conn.close()
        
        if not results:
            await interaction.followup.send("❌ No hay datos de estrategias en el período seleccionado")
            return
        
        lines = [f"📊 **PERFORMANCE POR ESTRATEGIA ({days} días)**", ""]
        
        for row in results:
            strategy, total, wins, losses, pnl, avg_win, avg_loss = row
            win_rate = (wins / total * 100) if total > 0 else 0
            
            lines.extend([
                f"🎯 **{strategy.upper()}**",
                f"• Trades: {total} | Ganadores: {wins} | Perdedores: {losses}",
                f"• Tasa acierto: {win_rate:.1f}%",
                f"• PnL total: {pnl:.2f}",
                f"• Ganancia promedio: {avg_win:.2f}" if avg_win else "• Ganancia promedio: N/A",
                f"• Pérdida promedio: {avg_loss:.2f}" if avg_loss else "• Pérdida promedio: N/A",
                ""
            ])
        
        await interaction.followup.send("\n".join(lines))
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error obteniendo performance: {e}")


# Demo stats command moved to services/commands.py


@bot.tree.command(name="force_autosignal")
@discord.app_commands.describe(symbol="Símbolo para forzar señal automática (por defecto: EURUSD)")
async def slash_force_autosignal(interaction: discord.Interaction, symbol: str = 'EURUSD'):
    """Fuerza la generación de una señal automática para pruebas (solo admin)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    
    try:
        # Buscar canal de señales
        ch = await _find_signals_channel()
        if ch is None:
            await interaction.followup.send(f"❌ No se encontró el canal '{SIGNALS_CHANNEL_NAME}'. Créalo primero.")
            return
        
        # Obtener datos y generar señal
        connect_mt5()
        df = get_candles(symbol.upper(), TIMEFRAME, CANDLES)
        
        # Usar la misma lógica que el auto-signal loop
        cfg = RULES_CONFIG.get(symbol.upper(), {}) or {}
        strat = cfg.get('strategy', 'ema50_200')
        
        sig, df2, risk_info = _detect_signal_wrapper(df, symbol=symbol.upper())
        
        if sig:
            # Crear ID de señal
            sid = max(state.pending_signals.keys(), default=0) + 1
            state.pending_signals[sid] = sig
            
            # Crear mensaje
            text = (
                f"🔧 **SEÑAL FORZADA** (ID {sid})\n"
                f"Activo: {sig['symbol']}\n"
                f"Tipo: {sig['type']}\n"
                f"Entrada: {sig['entry']:.5f}\n"
                f"SL: {sig['sl']:.5f}\n"
                f"TP: {sig['tp']:.5f}\n"
                f"Explicación: {sig.get('explanation','-')}\n"
                f"(Usa `/accept {sid}` para procesar)\n\n"
                f"**Información de Riesgo:**\n"
            )
            
            # Añadir información de riesgo si está disponible
            if risk_info and 'suggested_lot' in risk_info:
                text += f"Lot sugerido: {risk_info['suggested_lot']:.2f}\n"
            if risk_info and 'rr_ratio' in risk_info:
                text += f"R:R: {risk_info['rr_ratio']:.2f}\n"
            
            # Generar gráfico
            try:
                # Asegurar que el símbolo sea un string
                chart_symbol = sig.get('symbol', symbol.upper())
                if hasattr(chart_symbol, 'iloc'):
                    chart_symbol = str(chart_symbol.iloc[0]) if len(chart_symbol) > 0 else symbol.upper()
                elif not isinstance(chart_symbol, str):
                    chart_symbol = str(chart_symbol)
                
                logger.debug(f"Generating force autosignal chart for symbol: {chart_symbol}")
                chart = generate_chart(df2, symbol=chart_symbol, signal=sig)
                await ch.send(text, file=discord.File(chart))
                await interaction.followup.send(f"✅ Señal forzada enviada al canal #{ch.name}")
                
                # Limpiar archivo
                try:
                    os.remove(chart)
                except Exception:
                    pass
                    
            except Exception as chart_error:
                logger.error(f"Force autosignal chart generation failed: {chart_error}")
                await ch.send(text)
                await interaction.followup.send(f"✅ Señal enviada (sin gráfico): {chart_error}")
                
        else:
            reason = risk_info.get('reason', 'No hay señal válida') if risk_info else 'No hay señal válida'
            await interaction.followup.send(f"❌ No se pudo generar señal: {reason}")
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error forzando señal: {e}")


@bot.tree.command(name="debug_signals")
@discord.app_commands.describe(symbol="Símbolo para debug (EURUSD, XAUUSD, BTCEUR)")
@discord.app_commands.choices(symbol=[
    discord.app_commands.Choice(name="🇪🇺 EURUSD", value="EURUSD"),
    discord.app_commands.Choice(name="🥇 XAUUSD", value="XAUUSD"),
    discord.app_commands.Choice(name="₿ BTCEUR", value="BTCEUR")
])
async def slash_debug_signals(interaction: discord.Interaction, symbol: str = 'EURUSD'):
    """Debug detallado del sistema de señales con pipeline completo (solo admin)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        bot_logger.command_used(interaction.user.id, f"debug_signals {symbol}", False)
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    
    try:
        bot_logger.command_used(interaction.user.id, f"debug_signals {symbol}")
        
        # Obtener datos
        connect_mt5()
        df = get_candles(symbol, TIMEFRAME, CANDLES)
        
        # Configuración
        cfg = RULES_CONFIG.get(symbol.upper(), {}) or {}
        strat = cfg.get('strategy', 'ema50_200')

        # HARDENING BTCEUR: evitar estrategias no BTCEUR
        if symbol.upper() == 'BTCEUR' and 'btceur' not in strat.lower():
            logger.error("[BTCEUR FIX] Strategy corregida automáticamente en /debug_signals: %s → btceur_simple", strat)
            strat = 'btceur_simple'
        
        # Usar SOLO detect_signal_advanced (pipeline completo)
        advanced_signal, df_with_indicators, evaluation_info = detect_signal_advanced(
            df, 
            strategy=strat, 
            config=cfg, 
            current_balance=5000.0,
            symbol=symbol.upper(),
        )
        
        embed = discord.Embed(
            title=f"🔍 Debug de Señales: {symbol}",
            description="Análisis con pipeline completo (engine + scoring + filtros)",
            color=0xff9500
        )
        
        # Formatear precio según símbolo
        if symbol == 'XAUUSD':
            current_price_str = f"{df['close'].iloc[-1]:.2f}"
        elif symbol == 'BTCEUR':
            current_price_str = f"{df['close'].iloc[-1]:.0f}"
        else:  # EURUSD
            current_price_str = f"{df['close'].iloc[-1]:.5f}"
        
        # Información básica
        strategy_used = evaluation_info.get('strategy_used', strat)
        embed.add_field(
            name="📊 **Datos Básicos**",
            value=(
                f"**Símbolo:** {symbol}\n"
                f"**Estrategia:** {strategy_used}\n"
                f"**Velas:** {len(df)}\n"
                f"**Precio:** {current_price_str}"
            ),
            inline=True
        )
        
        # Pipeline completo
        confidence = evaluation_info.get('confidence', 'NONE')
        score = evaluation_info.get('score', 0.0)
        should_show = evaluation_info.get('should_show', False)
        
        embed.add_field(
            name="🎯 **Pipeline Completo**",
            value=(
                f"**Señal:** {'✅ DETECTADA' if advanced_signal else '❌ NO DETECTADA'}\n"
                f"**Confianza:** {confidence}\n"
                f"**Score:** {score:.2f}\n"
                f"**Mostrar:** {'✅ SÍ' if should_show else '❌ NO'}"
            ),
            inline=True
        )
        
        # Detalles de evaluación
        details = evaluation_info.get('details', {})
        rejection_reason = evaluation_info.get('rejection_reason', 'N/A')
        
        embed.add_field(
            name="🔧 **Evaluación**",
            value=(
                f"**Engine:** {'✅ EJECUTADO' if details else '❌ NO'}\n"
                f"**Auto-exec:** {'✅ SÍ' if evaluation_info.get('can_auto_execute', False) else '❌ NO'}\n"
                f"**Aprobado:** {'✅ SÍ' if evaluation_info.get('approved', False) else '❌ NO'}"
            ),
            inline=True
        )
        
        # Resultado y razón de rechazo
        if advanced_signal:
            signal_type = advanced_signal.get('type', 'N/A')
            explanation = advanced_signal.get('explanation', 'N/A')[:80]
            embed.add_field(
                name="✅ **Señal Generada**",
                value=(
                    f"**Tipo:** {signal_type}\n"
                    f"**Explicación:** {explanation}..."
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="❌ **Razón de Rechazo**",
                value=f"{rejection_reason[:200] if rejection_reason != 'N/A' else 'Sin información de rechazo'}",
                inline=False
            )
        
        # Detalles adicionales del engine
        if details:
            detail_lines = []
            
            if 'setup_found' in details:
                detail_lines.append(f"**Setup:** {'✅' if details['setup_found'] else '❌'}")
            
            if 'confirmations' in details:
                confs = details['confirmations']
                if isinstance(confs, dict):
                    passed = confs.get('passed', 0)
                    total = confs.get('total', 0)
                    detail_lines.append(f"**Confirmaciones:** {passed}/{total}")
            
            if 'filters_passed' in details:
                detail_lines.append(f"**Filtros:** {'✅ PASADOS' if details['filters_passed'] else '❌ FALLADOS'}")
            
            if detail_lines:
                embed.add_field(
                    name="🔍 **Detalles del Engine**",
                    value="\n".join(detail_lines),
                    inline=False
                )
        
        # Configuración actual
        embed.add_field(
            name="⚙️ **Configuración**",
            value=(
                f"**Min Score:** {cfg.get('min_score', 'N/A')}\n"
                f"**Min R:R:** {cfg.get('min_rr_ratio', 'N/A')}\n"
                f"**Habilitado:** {cfg.get('enabled', True)}"
            ),
            inline=True
        )
        
        # Sugerencias
        suggestions = []
        if not advanced_signal:
            if rejection_reason and rejection_reason != 'N/A':
                suggestions.append(f"• {rejection_reason[:100]}")
            else:
                suggestions.append("• Revisa logs para ver rechazos detallados")
                suggestions.append("• Verifica que el símbolo esté activo")
                suggestions.append("• Comprueba condiciones de mercado")
        else:
            suggestions.append("✅ Señal válida generada correctamente")
        
        embed.add_field(
            name="💡 **Diagnóstico**",
            value="\n".join(suggestions),
            inline=False
        )
        
        embed.set_footer(text="💡 Tip: Revisa los logs del bot para ver detalles de [BTCEUR][REJECT]")
        
        await interaction.followup.send(embed=embed)
        bot_logger.command_used(interaction.user.id, f"debug_signals {symbol}")
        
    except Exception as e:
        bot_logger.command_used(interaction.user.id, f"debug_signals {symbol}", False)
        logger.error(f"Error en debug_signals: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error en debug: {e}")


@bot.tree.command(name="diagnose_signals")
async def slash_diagnose_signals(interaction: discord.Interaction, symbol: str = 'EURUSD', iterations: int = 20):
    """Diagnóstico completo del pipeline de señales analizando ventanas históricas distintas (solo admin)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    
    try:
        from core.replay_engine import get_replay_engine
        
        symbol = symbol.upper()
        
        # Límite de seguridad: máximo 10000 iteraciones
        if iterations > 10000:
            await interaction.followup.send(f"⚠️ Maximum iterations allowed: 10000\nUsando 10000 iteraciones.")
            iterations = 10000
        
        # Obtener configuración del símbolo
        import json
        try:
            with open('rules_config.json', 'r') as f:
                rules = json.load(f)
            symbol_config = rules.get(symbol, {})
            strategy_name = symbol_config.get('strategy', 'ema50_200')
            min_score = symbol_config.get('min_score', 0.60)
        except Exception:
            strategy_name = 'ema50_200'
            min_score = 0.60
        
        # Usar replay engine en modo diagnóstico
        # Esto analiza diferentes ventanas históricas del mercado
        replay_engine = get_replay_engine()
        
        # Ejecutar replay (analiza ventanas históricas distintas)
        stats_obj = replay_engine.run_replay(
            symbol=symbol,
            bars=iterations,
            strategy=strategy_name,
            skip_duplicate_filter=True  # Desactivar filtro de duplicados en diagnóstico
        )
        
        # Calcular estadísticas de diagnóstico
        total_evaluated = stats_obj.bars_analyzed
        setup_detected = stats_obj.setups_detected
        final_signals = stats_obj.signals_final
        
        # Analizar señales para obtener más detalles
        signals = replay_engine.get_signals()
        passed_scoring = 0
        passed_confidence = 0
        
        for sig in signals:
            passed_scoring += 1  # Si llegó a ser señal final, pasó scoring
            if sig.confidence in ['HIGH', 'VERY_HIGH', 'MEDIUM-HIGH']:
                passed_confidence += 1
        
        # Generar reporte
        report = f"🔍 **DIAGNÓSTICO DE SEÑALES - {symbol}**\n\n"
        report += f"**Configuración:**\n"
        report += f"- Estrategia: `{strategy_name}`\n"
        report += f"- Min Score: `{min_score}`\n"
        report += f"- Ventanas analizadas: `{iterations}`\n"
        report += f"- Lookback: `100 velas`\n\n"
        
        report += f"**Análisis de Ventanas Históricas:**\n"
        report += f"- Total evaluado: `{total_evaluated}` ventanas distintas\n"
        report += f"- Setup detectado: `{setup_detected}` ({setup_detected/total_evaluated*100:.1f}%)\n"
        report += f"- Pasó scoring: `{passed_scoring}` ({passed_scoring/total_evaluated*100:.1f}%)\n"
        report += f"- Alta confianza: `{passed_confidence}` ({passed_confidence/total_evaluated*100:.1f}%)\n"
        report += f"- Señales finales: `{final_signals}` ({final_signals/total_evaluated*100:.1f}%)\n\n"
        
        # Desglose por tipo
        if final_signals > 0:
            report += f"**Desglose de Señales:**\n"
            report += f"- BUY: `{stats_obj.buy_signals}` ({stats_obj.buy_signals/final_signals*100:.1f}%)\n"
            report += f"- SELL: `{stats_obj.sell_signals}` ({stats_obj.sell_signals/final_signals*100:.1f}%)\n\n"
        
        # Análisis de confianza
        if signals:
            confidence_counts = {}
            for sig in signals:
                conf = sig.confidence
                confidence_counts[conf] = confidence_counts.get(conf, 0) + 1
            
            report += f"**Distribución de Confianza:**\n"
            for conf, count in sorted(confidence_counts.items(), key=lambda x: x[1], reverse=True):
                report += f"- {conf}: `{count}` ({count/len(signals)*100:.1f}%)\n"
            report += "\n"
        
        # Interpretación
        report += f"**Interpretación:**\n"
        
        if final_signals == 0:
            report += f"⚠️ No se detectaron señales finales en {iterations} ventanas históricas.\n"
            report += f"Posibles causas:\n"
            report += f"- Estrategia demasiado restrictiva\n"
            report += f"- Condiciones de mercado no favorables en el período\n"
            report += f"- Min score muy alto ({min_score})\n"
        elif final_signals / total_evaluated < 0.01:
            report += f"⚠️ Tasa de señales muy baja ({final_signals/total_evaluated*100:.2f}%)\n"
            report += f"La estrategia es extremadamente selectiva.\n"
        elif final_signals / total_evaluated > 0.10:
            report += f"⚠️ Tasa de señales muy alta ({final_signals/total_evaluated*100:.1f}%)\n"
            report += f"Riesgo de sobretrading. Considerar aumentar filtros.\n"
        else:
            report += f"✅ Tasa de señales en rango óptimo ({final_signals/total_evaluated*100:.1f}%)\n"
        
        report += f"\n💡 **Nota:** Este diagnóstico analiza {iterations} ventanas históricas DISTINTAS del mercado.\n"
        report += f"Tiempo de ejecución: `{stats_obj.execution_time:.2f}s`\n"
        
        await interaction.followup.send(report)
        
    except Exception as e:
        logger.error(f"Error en diagnóstico: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error en diagnóstico: {e}")


@bot.tree.command(name="performance")
@discord.app_commands.describe(days="Número de días para el reporte (por defecto: 30)")
async def slash_performance(interaction: discord.Interaction, days: int = 30):
    """Muestra un reporte de performance del bot (solo admin)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    
    if risk_manager is None:
        await interaction.followup.send("❌ Gestor de riesgo no disponible")
        return
    
    try:
        report = risk_manager.get_performance_report(days)
        
        if 'error' in report:
            await interaction.followup.send(f"❌ {report['error']}")
            return
        
        # Formatear el reporte
        lines = [
            f"📊 **REPORTE DE PERFORMANCE ({days} días)**",
            f"",
            f"🔢 **Estadísticas Generales:**",
            f"• Total de trades: {report['total_trades']}",
            f"• Trades ganadores: {report['wins']}",
            f"• Trades perdedores: {report['losses']}",
            f"• Tasa de acierto: {report['win_rate']}%",
            f"",
            f"💰 **Resultados Financieros:**",
            f"• PnL total: {report['total_pnl']}",
            f"• Ganancia promedio: {report['avg_win']}",
            f"• Pérdida promedio: {report['avg_loss']}",
            f"• Factor de beneficio: {report['profit_factor']}",
            f"",
            f"📈 **Análisis:**"
        ]
        
        # Añadir análisis cualitativo
        if report['win_rate'] >= 60:
            lines.append("✅ Excelente tasa de acierto")
        elif report['win_rate'] >= 50:
            lines.append("🟡 Tasa de acierto aceptable")
        else:
            lines.append("🔴 Tasa de acierto baja - revisar estrategias")
        
        if report['profit_factor'] >= 1.5:
            lines.append("✅ Buen factor de beneficio")
        elif report['profit_factor'] >= 1.0:
            lines.append("🟡 Factor de beneficio marginal")
        else:
            lines.append("🔴 Factor de beneficio negativo")
        
        await interaction.followup.send("\n".join(lines))
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error generando reporte: {e}")


# Trailing status command moved to services/commands.py


# Risk status command moved to services/commands.py


# ----------------------
# MT5 credential helpers (Modal)
# ----------------------
from discord import ui


class MT5CredentialsModal(ui.Modal, title="MT5 Credentials"):
    login = ui.TextInput(label="Login (numeric)", style=discord.TextStyle.short, placeholder="123456", required=True)
    password = ui.TextInput(label="Password", style=discord.TextStyle.short, required=True)
    server = ui.TextInput(label="Server", style=discord.TextStyle.short, placeholder="BrokerServer", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            state.mt5_credentials['login'] = int(self.login.value)
        except Exception:
            state.mt5_credentials['login'] = self.login.value
        state.mt5_credentials['password'] = self.password.value
        state.mt5_credentials['server'] = self.server.value
        # try to persist encrypted (save_credentials espera login, password, server)
        ok = save_credentials(
            state.mt5_credentials['login'],
            state.mt5_credentials['password'],
            state.mt5_credentials['server'],
        )
        if ok:
            await interaction.response.send_message("Credenciales MT5 almacenadas y cifradas en disco. Usa `mt5_login` para intentar iniciar sesión.", ephemeral=True)
        else:
            await interaction.response.send_message("Credenciales almacenadas en memoria (no cifradas). Define MT5_MASTER_KEY en .env para cifrarlas en disco.", ephemeral=True)


@bot.command()
async def set_mt5_credentials(ctx):
    """Abre un modal para introducir credenciales MT5. Sólo usuario autorizado."""
    if ctx.author.id != AUTHORIZED_USER_ID:
        return
    await ctx.send_modal(MT5CredentialsModal())


@bot.command()
async def mt5_login(ctx):
    """Intenta iniciar sesión en MT5 con las credenciales guardadas en memoria."""
    if ctx.author.id != AUTHORIZED_USER_ID:
        return

    if not state.mt5_credentials.get('login'):
        await ctx.send("No hay credenciales guardadas. Usa `set_mt5_credentials` primero.")
        return

    try:
        connect_mt5()
        ok = mt5_login(state.mt5_credentials.get('login'), state.mt5_credentials.get('password'), state.mt5_credentials.get('server'))
        if ok:
            await ctx.send("✅ Conectado y logueado en MT5.")
        else:
            # mt5.last_error might be available
            err = None
            try:
                import MetaTrader5 as _mt5
                err = _mt5.last_error()
            except Exception:
                pass
            await ctx.send(f"❌ Login falló: {err}")
    except Exception as e:
        await ctx.send(f"❌ Error al loguear en MT5: {e}")

# Background loops moved to services/autosignals.py


# Next opening command moved to services/commands.py


# Pre-market analysis command moved to services/commands.py


# Opening alerts command moved to services/commands.py


# Period status command moved to services/commands.py


# Backtest summary command moved to services/commands.py


# Cooldown status command moved to services/commands.py


# Live dashboard command moved to services/commands.py


# ── Modal para configurar el backtest desde Discord ───────────────────────────

class ReplayConfigModal(discord.ui.Modal, title="⚙️ Configurar Backtest"):
    """Modal que recoge los parámetros del backtest antes de ejecutarlo."""

    symbol = discord.ui.TextInput(
        label="Par (EURUSD / XAUUSD / BTCEUR)",
        placeholder="EURUSD",
        default="EURUSD",
        max_length=10,
        required=True,
    )
    strategy = discord.ui.TextInput(
        label="Estrategia (dejar vacío = activa del par)",
        placeholder="eurusd_asian_breakout / xauusd_simple / btceur_simple",
        required=False,
        max_length=40,
    )
    bars = discord.ui.TextInput(
        label="Velas H1 a analizar (100 – 10000)",
        placeholder="3000",
        default="3000",
        max_length=5,
        required=True,
    )
    cb_losses = discord.ui.TextInput(
        label="Circuit Breaker: pérdidas consecutivas (0=off)",
        placeholder="4",
        default="4",
        max_length=2,
        required=False,
    )
    cb_pause = discord.ui.TextInput(
        label="Circuit Breaker: velas de pausa",
        placeholder="168",
        default="168",
        max_length=4,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        # ── Parsear y validar parámetros ──────────────────────────────────────
        sym = self.symbol.value.strip().upper()
        if sym not in ('EURUSD', 'XAUUSD', 'BTCEUR'):
            await interaction.followup.send(
                f"❌ Símbolo `{sym}` no válido. Usa EURUSD, XAUUSD o BTCEUR.", ephemeral=True
            )
            return

        try:
            n_bars = int(self.bars.value.strip())
            n_bars = max(100, min(10000, n_bars))
        except ValueError:
            n_bars = 3000

        try:
            n_cb_losses = int(self.cb_losses.value.strip()) if self.cb_losses.value.strip() else 4
            n_cb_losses = max(0, n_cb_losses)
        except ValueError:
            n_cb_losses = 4

        try:
            n_cb_pause = int(self.cb_pause.value.strip()) if self.cb_pause.value.strip() else 168
            n_cb_pause = max(1, n_cb_pause)
        except ValueError:
            n_cb_pause = 168

        # Estrategia: usar la del rules_config si no se especifica
        strat_input = self.strategy.value.strip().lower() if self.strategy.value.strip() else None
        strategy_map = {
            'EURUSD': ['eurusd_partial', 'eurusd_simple', 'eurusd_advanced', 'eurusd_mtf', 'eurusd_asian_breakout'],
            'XAUUSD': ['xauusd_partial', 'xauusd_simple', 'xauusd_reversal', 'xauusd_momentum', 'xauusd_psychological'],
            'BTCEUR': ['btceur_partial', 'btceur_simple', 'btc_trend_pullback_v1', 'btceur_weekly_breakout'],
        }
        default_strategy = {
            'EURUSD': 'eurusd_partial',
            'XAUUSD': 'xauusd_partial',
            'BTCEUR': 'btceur_partial',
        }
        if strat_input and strat_input not in strategy_map.get(sym, []):
            await interaction.followup.send(
                f"❌ Estrategia `{strat_input}` no válida para {sym}.\n"
                f"Disponibles: `{'`, `'.join(strategy_map[sym])}`",
                ephemeral=True
            )
            return
        strat = strat_input or default_strategy[sym]

        cb_label = f"CB {n_cb_losses}L/{n_cb_pause}v" if n_cb_losses > 0 else "sin CB"
        await interaction.followup.send(
            f"⏳ Ejecutando backtest...\n"
            f"**{sym}** · `{strat}` · **{n_bars}** velas · {cb_label}"
        )

        # ── Ejecutar backtest en thread para no bloquear el event loop ────────
        try:
            import asyncio
            from core.replay_engine import ReplayEngine

            engine = ReplayEngine(
                max_forward_bars=120,
                cb_consecutive_losses=n_cb_losses,
                cb_pause_bars=n_cb_pause,
            )

            def _run():
                return engine.run_replay(
                    symbol=sym,
                    bars=n_bars,
                    strategy=strat,
                    timeframe='H1',
                    skip_duplicate_filter=True,
                )

            stats = await asyncio.to_thread(_run)

        except Exception as e:
            logger.error(f"Error en /replay: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error ejecutando backtest: {e}")
            return

        # ── Calcular métricas extra ───────────────────────────────────────────
        signals = engine.get_signals()
        wins   = [s for s in signals if s.result == 'WIN']
        losses = [s for s in signals if s.result == 'LOSS']
        closed = len(wins) + len(losses)
        gp = sum(s.profit_pips or 0 for s in wins)
        gl = abs(sum(s.profit_pips or 0 for s in losses))
        pf = gp / gl if gl > 0 else float('inf')
        pf_str = f"{pf:.2f}" if pf != float('inf') else "∞"

        # Racha máxima de pérdidas
        max_streak = cur = 0
        for s in signals:
            if s.result == 'LOSS': cur += 1; max_streak = max(max_streak, cur)
            elif s.result == 'WIN': cur = 0

        # ── Simulación Monte Carlo ─────────────────────────────────────────────
        mc_summary = "Simulación omitida (menos de 5 trades cerrados)"
        if closed >= 5:
            try:
                from core.montecarlo import MonteCarlo, TradeRecord
                # Convertir ReplaySignal a TradeRecord
                mc_records = [TradeRecord.from_replay_signal(s) for s in signals if s.result in ('WIN', 'LOSS')]
                # Umbral de ruina: -300 pips (Forex) y -3000 pips (Bitcoin/Crypto)
                ruin_threshold = -3000.0 if sym == 'BTCEUR' else -300.0
                mc = MonteCarlo(n_simulations=5000, ruin_threshold=ruin_threshold)
                mc_report = mc.run(mc_records, symbol=sym)
                
                mc_summary = (
                    f"Probabilidad de Beneficio: **{mc_report.prob_profitable*100:.1f}%**\n"
                    f"Riesgo de Ruina ({ruin_threshold:+.0f} pips): **{mc_report.prob_ruin*100:.1f}%**\n"
                    f"DD Esperado (p50): **{mc_report.p50_drawdown:.1f} pips**\n"
                    f"DD Máximo Probable (p95): **{mc_report.p95_drawdown:.1f} pips**"
                )
            except Exception as mc_err:
                logger.error(f"Error en Monte Carlo: {mc_err}")
                mc_summary = "⚠️ Error ejecutando simulación Monte Carlo"

        # ── Construir embed de resultados ─────────────────────────────────────
        has_edge = closed >= 10 and stats.winrate >= 50 and pf >= 1.2 and stats.total_pips > 0
        color = 0x3fb950 if has_edge else (0xd29922 if closed >= 10 else 0x8b949e)

        embed = discord.Embed(
            title=f"📊 Backtest — {sym} · {strat}",
            color=color,
            description=(
                f"**{n_bars}** velas H1 · {cb_label} · "
                f"{'✅ CON EDGE' if has_edge else '⚠️ SIN EDGE CLARO'}"
            )
        )

        embed.add_field(
            name="Señales",
            value=(
                f"Total: **{stats.signals_final}**\n"
                f"BUY: {stats.buy_signals} · SELL: {stats.sell_signals}\n"
                f"Cerradas: {closed} (TP {stats.tp_hits} / SL {stats.sl_hits})"
            ),
            inline=True,
        )
        embed.add_field(
            name="Rendimiento",
            value=(
                f"Winrate: **{stats.winrate:.1f}%**\n"
                f"Profit Factor: **{pf_str}**\n"
                f"Pips netos: **{stats.total_pips:+.0f}**"
            ),
            inline=True,
        )
        embed.add_field(
            name="Riesgo",
            value=(
                f"R:R medio: {stats.avg_rr:.2f}\n"
                f"Racha max pérd.: {max_streak}\n"
                f"Tiempo: {stats.execution_time:.1f}s"
            ),
            inline=True,
        )

        if n_cb_losses > 0 and stats.cb_activations > 0:
            embed.add_field(
                name="Circuit Breaker",
                value=(
                    f"Activaciones: **{stats.cb_activations}**\n"
                    f"Velas pausadas: {stats.bars_paused}\n"
                    f"Señales bloqueadas: {stats.signals_blocked_by_cb}"
                ),
                inline=True,
            )

        embed.add_field(
            name="Simulación Monte Carlo (5,000 runs)",
            value=mc_summary,
            inline=False,
        )

        if closed < 10:
            embed.set_footer(text="⚠️ Pocas señales cerradas — aumenta las velas para más fiabilidad")
        else:
            embed.set_footer(text="Mismo pipeline que producción · estrategias, scoring y filtros reales")

        await interaction.followup.send(embed=embed)


@bot.tree.command(name="replay")
async def slash_replay(interaction: discord.Interaction):
    """Abre el configurador de backtest y ejecuta el replay con el pipeline real (solo admin)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return
    await interaction.response.send_modal(ReplayConfigModal())




# ======================
# NUEVOS COMANDOS
# ======================

@bot.tree.command(name="bot_status")
async def slash_bot_status(interaction: discord.Interaction):
    """Estado del circuit breaker y cooldowns activos por par (solo admin)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=True)

    try:
        from core.circuit_breaker import get_circuit_breaker
        cb = get_circuit_breaker()
        cb_status = cb.get_status()

        # ── Circuit Breaker ───────────────────────────────────────────────────
        can_trade   = cb_status.get('can_trade', True)
        cons_losses = cb_status.get('consecutive_losses', 0)
        cons_wins   = cb_status.get('consecutive_wins', 0)
        risk_mult   = cb_status.get('risk_multiplier', 1.0)
        paused_until = cb_status.get('paused_until')
        pause_reason = cb_status.get('pause_reason', '')

        if can_trade:
            cb_line = f"🟢 **ACTIVO** · pérdidas seguidas: {cons_losses} · wins seguidos: {cons_wins}"
        else:
            remaining_h = 0.0
            if paused_until:
                from datetime import datetime, timezone
                pu = datetime.fromisoformat(paused_until)
                if pu.tzinfo is None:
                    pu = pu.replace(tzinfo=timezone.utc)
                remaining_h = max(0, (pu - datetime.now(timezone.utc)).total_seconds() / 3600)
            cb_line = (
                f"🔴 **PAUSADO** · {pause_reason}\n"
                f"  Reanuda en **{remaining_h:.1f}h**"
            )

        risk_line = f"Multiplicador de riesgo: **×{risk_mult:.1f}**"

        # ── Cooldowns de autosignals ──────────────────────────────────────────
        cooldown_lines = []
        try:
            import json as _json
            import os as _os
            cooldown_file = _os.path.join(_os.path.dirname(__file__), 'autosignals_state.json')
            if _os.path.exists(cooldown_file):
                with open(cooldown_file, 'r', encoding='utf-8') as f:
                    cd_data = _json.load(f)
                last_times = cd_data.get('last_signal_time', {})
                cooldown_minutes = {'EURUSD': 60, 'XAUUSD': 240, 'BTCEUR': 60}
                now_utc = datetime.now(timezone.utc)
                for sym, cd_min in cooldown_minutes.items():
                    ts_str = last_times.get(sym)
                    if ts_str:
                        ts = datetime.fromisoformat(ts_str)
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        elapsed = (now_utc - ts).total_seconds() / 60
                        remaining = cd_min - elapsed
                        if remaining > 0:
                            cooldown_lines.append(f"  ⏳ **{sym}**: {int(remaining)} min restantes")
                        else:
                            cooldown_lines.append(f"  ✅ **{sym}**: libre")
                    else:
                        cooldown_lines.append(f"  ✅ **{sym}**: libre")
            else:
                cooldown_lines.append("  Sin datos de cooldown (sesión nueva)")
        except Exception as e:
            cooldown_lines.append(f"  Error leyendo cooldowns: {e}")

        lines = [
            "**⚡ Circuit Breaker**",
            cb_line,
            risk_line,
            "",
            "**⏳ Cooldowns por par**",
        ] + cooldown_lines

        await interaction.followup.send("\n".join(lines), ephemeral=True)

    except Exception as e:
        logger.error(f"Error en /bot_status: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


@bot.tree.command(name="news")
async def slash_news(interaction: discord.Interaction):
    """Próximos eventos de alto impacto del calendario económico con ventana de blackout (solo admin)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=True)

    try:
        from services.news_filter import NewsFilter, BLACKOUT_MINUTES
        from datetime import datetime, timezone, timedelta

        nf = NewsFilter()
        now = datetime.now(timezone.utc)

        # Recopilar eventos de los próximos 7 días para todos los símbolos
        all_events = []
        seen = set()
        for currencies in [['USD', 'EUR'], ['USD'], ['EUR']]:
            for offset in range(-1, 8):
                check = (now + timedelta(days=offset)).date()
                events = nf._get_events_near(
                    datetime(check.year, check.month, check.day, 12, tzinfo=timezone.utc),
                    currencies
                )
                for ev in events:
                    key = (ev['name'], ev['time'].isoformat())
                    if key not in seen:
                        seen.add(key)
                        all_events.append(ev)

        # Ordenar por tiempo y filtrar a los próximos 7 días
        cutoff = now + timedelta(days=7)
        upcoming = sorted(
            [e for e in all_events if now - timedelta(hours=1) <= e['time'] <= cutoff],
            key=lambda x: x['time']
        )

        if not upcoming:
            await interaction.followup.send(
                "✅ Sin eventos de alto impacto en los próximos 7 días.", ephemeral=True
            )
            return

        lines = [f"**📅 Próximos eventos de alto impacto** (±{BLACKOUT_MINUTES} min blackout)\n"]
        for ev in upcoming[:15]:
            t = ev['time']
            delta_min = (t - now).total_seconds() / 60
            if delta_min < 0:
                when = f"hace {int(-delta_min)} min"
                icon = "🔴"
            elif delta_min < BLACKOUT_MINUTES:
                when = f"en {int(delta_min)} min ⚠️ BLACKOUT ACTIVO"
                icon = "🚨"
            elif delta_min < 60:
                when = f"en {int(delta_min)} min"
                icon = "🟡"
            else:
                hours = int(delta_min // 60)
                mins  = int(delta_min % 60)
                when = f"en {hours}h {mins}m" if mins else f"en {hours}h"
                icon = "🟢"

            # Símbolos afectados
            affected = []
            for sym, curs in nf.SYMBOL_CURRENCIES.items():
                if ev['currency'] in curs:
                    affected.append(sym)

            lines.append(
                f"{icon} **{ev['name']}** ({ev['currency']})\n"
                f"  {t.strftime('%d/%m %H:%M')} UTC · {when}\n"
                f"  Afecta: {', '.join(affected) if affected else '—'}"
            )

        await interaction.followup.send("\n".join(lines), ephemeral=True)

    except Exception as e:
        logger.error(f"Error en /news: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


@bot.tree.command(name="equity")
async def slash_equity(interaction: discord.Interaction):
    """Snapshot de equity MT5: balance + P&L flotante (solo admin)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=True)

    try:
        from services.dashboard import get_dashboard_service

        snap = get_dashboard_service().get_equity_snapshot()
        mode        = snap.get('mode', 'mt5')
        balance     = snap.get('balance', 0.0)
        floating    = snap.get('floating_pnl', 0.0)
        total       = snap.get('total_equity', 0.0)
        change      = snap.get('change', 0.0)
        change_pct  = snap.get('change_pct', 0.0)
        base        = snap.get('base_balance', balance)

        sign_ch  = "+" if change  >= 0 else ""
        sign_fl  = "+" if floating >= 0 else ""
        mode_lbl = "MT5"

        lines = [
            f"**💰 Equity — {mode_lbl}**",
            "",
            f"Balance base:      **{base:,.2f} €**",
            f"Cerradas (P&L):    **{sign_ch}{change:+.2f} €**",
            f"Flotante (abiertas): **{sign_fl}{floating:+.2f} €**",
            f"─────────────────────",
            f"**Equity total:    {total:,.2f} €**  ({sign_ch}{change_pct:.2f}%)",
        ]

        await interaction.followup.send("\n".join(lines), ephemeral=True)

    except Exception as e:
        logger.error(f"Error en /equity: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# ======================
# COMANDOS: GO-LIVE CHECK y JOURNAL
# ======================

@bot.tree.command(name="go_live_check")
@discord.app_commands.describe(symbol="Par a evaluar: EURUSD, XAUUSD o BTCEUR (por defecto: EURUSD)")
async def slash_go_live_check(
    interaction: discord.Interaction,
    symbol: str = "EURUSD",
):
    """Evalúa automáticamente los 6 criterios de go-live para un par (solo admin)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    sym = symbol.strip().upper()
    if sym not in ('EURUSD', 'XAUUSD', 'BTCEUR'):
        await interaction.response.send_message(
            "❌ Símbolo no válido. Usa EURUSD, XAUUSD o BTCEUR.", ephemeral=True
        )
        return

    await interaction.response.defer(thinking=True, ephemeral=True)

    results: list[str] = []
    passed = 0
    total_criteria = 6

    try:
        # ── Criterio 1: Clasificación progresiva ≥ STABLE ────────────────────
        try:
            import glob
            wf_pattern = os.path.join(
                os.path.dirname(__file__), 'backtest_results',
                f'walkforward_{sym}_*.csv'
            )
            wf_files = sorted(glob.glob(wf_pattern), reverse=True)
            if wf_files:
                import csv
                with open(wf_files[0], newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows_wf = list(reader)
                stability = rows_wf[0].get('stability_rating', 'UNKNOWN') if rows_wf else 'UNKNOWN'
            else:
                stability = 'NO_DATA'

            ok1 = stability in ('STABLE', 'MARGINAL')
            icon1 = '✅' if ok1 else '❌'
            if ok1:
                passed += 1
            results.append(f"{icon1} **Clasificación walk-forward**: `{stability}` (mín: MARGINAL)")
        except Exception as e:
            results.append(f"⚠️ **Clasificación walk-forward**: error al leer CSV — `{e}`")

        # ── Criterio 2: ≥ 50 trades cerrados en MT5 ─────────────────────────
        try:
            from core.journal import get_journal
            journal = get_journal()
            closed_count = journal.count_closed_trades(symbol=sym, mode='live')
            ok2 = closed_count >= 50
            icon2 = '✅' if ok2 else '❌'
            if ok2:
                passed += 1
            results.append(f"{icon2} **Trades cerrados MT5**: `{closed_count}/50`")
        except Exception as e:
            results.append(f"⚠️ **Trades cerrados MT5**: error — `{e}`")

        # ── Criterio 3: PF MT5 ≥ 1.3 ──────────────────────────────────────────
        try:
            from core.journal import get_journal
            rep = get_journal().get_report(days=0, symbol=sym, mode='live')
            pf_live = rep.get('profit_factor', 0.0)
            if pf_live == float('inf'):
                pf_live_str = '∞'
                ok3 = True
            else:
                pf_live_str = f"{pf_live:.2f}"
                ok3 = pf_live >= 1.3
            icon3 = '✅' if ok3 else '❌'
            if ok3:
                passed += 1
            results.append(f"{icon3} **Profit Factor MT5**: `{pf_live_str}` (mín: 1.30)")
        except Exception as e:
            results.append(f"⚠️ **Profit Factor MT5**: error — `{e}`")

        # ── Criterio 4: Drawdown ≤ 15% ───────────────────────────────────────
        try:
            from core.journal import get_journal
            rep = get_journal().get_report(days=0, symbol=sym, mode='live')
            total_pips = rep.get('total_pnl_pips', 0.0)
            # Estimamos el DD máximo como la racha de pérdidas acumuladas
            recent = get_journal().get_recent_trades(limit=200, symbol=sym)
            equity = 0.0
            peak = 0.0
            max_dd_pct = 0.0
            for t in reversed(recent):
                if t.get('result') in ('WIN', 'LOSS', 'BREAKEVEN') and t.get('mode') == 'live':
                    equity += t.get('pnl_pips') or 0.0
                    if equity > peak:
                        peak = equity
                    if peak > 0:
                        dd = (peak - equity) / peak * 100
                        if dd > max_dd_pct:
                            max_dd_pct = dd
            ok4 = max_dd_pct <= 15.0
            icon4 = '✅' if ok4 else '❌'
            if ok4:
                passed += 1
            results.append(f"{icon4} **Drawdown máximo MT5**: `{max_dd_pct:.1f}%` (máx: 15%)")
        except Exception as e:
            results.append(f"⚠️ **Drawdown máximo MT5**: error — `{e}`")

        # ── Criterio 5: WR MT5 ≥ WR backtest × 0.85 ────────────────────────
        try:
            from core.journal import get_journal
            rep_live = get_journal().get_report(days=0, symbol=sym, mode='live')
            wr_live = rep_live.get('winrate', 0.0)

            # WR backtest: buscar en CSV más reciente
            import glob, csv
            bt_pattern = os.path.join(
                os.path.dirname(__file__), 'backtest_results', f'backtest_*_{sym}_*.csv'
            )
            bt_files = sorted(glob.glob(bt_pattern), reverse=True)
            wr_backtest = None
            if bt_files:
                with open(bt_files[0], newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    bt_rows = list(reader)
                if bt_rows:
                    wr_backtest = float(bt_rows[0].get('winrate', 0) or 0)

            if wr_backtest is not None and wr_backtest > 0:
                threshold = wr_backtest * 0.85
                ok5 = wr_live >= threshold
                icon5 = '✅' if ok5 else '❌'
                detail = f"`{wr_live:.1f}%` vs backtest `{wr_backtest:.1f}%` (mín: `{threshold:.1f}%`)"
            else:
                ok5 = wr_live > 0
                icon5 = '⚠️' if ok5 else '❌'
                detail = f"`{wr_live:.1f}%` (sin datos backtest para comparar)"
            if ok5:
                passed += 1
            results.append(f"{icon5} **Winrate MT5 vs backtest**: {detail}")
        except Exception as e:
            results.append(f"⚠️ **Winrate MT5 vs backtest**: error — `{e}`")

        # ── Criterio 6: Walk-forward ventanas útiles ≥ 3 ─────────────────────
        try:
            import glob, csv
            wf_pattern = os.path.join(
                os.path.dirname(__file__), 'backtest_results',
                f'walkforward_{sym}_*.csv'
            )
            wf_files = sorted(glob.glob(wf_pattern), reverse=True)
            profitable_windows = 0
            total_windows = 0
            if wf_files:
                with open(wf_files[0], newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        total_windows += 1
                        try:
                            if float(row.get('test_pf', 0) or 0) >= 1.0:
                                profitable_windows += 1
                        except Exception:
                            pass
            ok6 = profitable_windows >= 3
            icon6 = '✅' if ok6 else '❌'
            if ok6:
                passed += 1
            results.append(
                f"{icon6} **Ventanas WF rentables**: `{profitable_windows}/{total_windows}` (mín: 3)"
            )
        except Exception as e:
            results.append(f"⚠️ **Ventanas WF rentables**: error — `{e}`")

    except Exception as e:
        logger.error(f"Error en /go_live_check: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error inesperado: {e}", ephemeral=True)
        return

    # ── Veredicto final ───────────────────────────────────────────────────────
    if passed == total_criteria:
        verdict = "✅ **LISTO PARA LIVE** — todos los criterios superados"
    elif passed >= 4:
        verdict = f"⚠️ **CASI LISTO** — {passed}/{total_criteria} criterios superados. Revisar los fallidos."
    else:
        verdict = f"❌ **NO LISTO** — solo {passed}/{total_criteria} criterios superados."

    lines = [
        f"**🚦 Go-Live Check — {sym}**",
        "",
    ] + results + [
        "",
        f"─────────────────────────────",
        verdict,
    ]

    await interaction.followup.send("\n".join(lines), ephemeral=True)


@bot.tree.command(name="journal")
@discord.app_commands.describe(
    symbol="Par a consultar (EURUSD, XAUUSD, BTCEUR o ALL)",
    days="Días hacia atrás (0 = todos, por defecto: 30)",
    mode="live (por defecto) u otro valor del journal",
)
async def slash_journal(
    interaction: discord.Interaction,
    symbol: str = "ALL",
    days: int = 30,
    mode: str = "live",
):
    """Resumen del trade journal: winrate, PF, P&L, duración media (solo admin)."""
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=True)

    sym_filter = None if symbol.upper() == 'ALL' else symbol.upper()
    mode_filter = mode.lower() if mode.lower() in ('paper', 'live') else 'live'
    days_val = max(0, days)

    try:
        from core.journal import get_journal
        journal = get_journal()
        rep = journal.get_report(days=days_val, symbol=sym_filter, mode=mode_filter)

        if rep.get('total_trades', 0) == 0:
            await interaction.followup.send(
                f"📭 No hay trades en el journal para **{symbol}** "
                f"({'todos los días' if days_val == 0 else f'últimos {days_val}d'}) — modo `{mode_filter}`.",
                ephemeral=True,
            )
            return

        period_str = "todos los días" if days_val == 0 else f"últimos {days_val}d"
        pf_str = "∞" if rep['profit_factor'] == float('inf') else f"{rep['profit_factor']:.2f}"
        dur = int(rep.get('avg_duration_min', 0))
        dur_str = f"{dur // 60}h {dur % 60}m" if dur >= 60 else f"{dur}min"

        lines = [
            f"**📒 Journal — {symbol.upper()} · {period_str} · `{mode_filter}`**",
            "",
            f"Trades totales:   **{rep['total_trades']}**  (cerrados: {rep['closed_trades']} | pendientes: {rep['pending_trades']})",
            f"Ganadas/perdidas: **{rep['wins']}W / {rep['losses']}L**  →  WR `{rep['winrate']}%`",
            f"Profit Factor:    **{pf_str}**",
            f"P&L total:        **{rep['total_pnl_pips']:+.1f} pips**  ({rep['total_pnl_eur']:+.2f} €)",
            f"Duración media:   **{dur_str}**",
            f"Score confianza:  **{rep['avg_confidence_score']:.2f}** / 1.00",
        ]

        # Por símbolo (si es ALL)
        if sym_filter is None and rep.get('by_symbol'):
            lines += ["", "**Por par:**"]
            for sym, d in sorted(rep['by_symbol'].items()):
                lines.append(
                    f"  {sym}: {d['total']}T · WR `{d['winrate']}%` · `{d['pnl_pips']:+.0f}` pip"
                )

        # Por estrategia
        if rep.get('by_strategy'):
            lines += ["", "**Por estrategia:**"]
            for strat, d in sorted(rep['by_strategy'].items(), key=lambda x: -x[1]['total']):
                lines.append(
                    f"  `{strat}`: {d['total']}T · WR `{d['winrate']}%` · `{d['pnl_pips']:+.0f}` pip"
                )

        # Últimos 5 trades
        recent = journal.get_recent_trades(limit=5, symbol=sym_filter)
        if recent:
            lines += ["", "**Últimas 5 operaciones:**"]
            for t in recent:
                ts = t['entry_time'][:16] if t.get('entry_time') else '?'
                res = t.get('result') or 'PEND'
                pip = t.get('pnl_pips') or 0
                icon = '🟢' if res == 'WIN' else ('🔴' if res == 'LOSS' else '🟡')
                lines.append(
                    f"  {icon} `{ts}` {t.get('symbol','?')} {t.get('signal_type','?')} "
                    f"→ {res} `{pip:+.0f}p` [{t.get('confidence','?')}]"
                )

        msg = "\n".join(lines)
        # Discord limita a 2000 chars
        if len(msg) > 1950:
            msg = msg[:1950] + "\n…*(truncado)*"

        await interaction.followup.send(msg, ephemeral=True)

    except Exception as e:
        logger.error(f"Error en /journal: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# ======================
# START
# ======================

if __name__ == '__main__':
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN no encontrado en el entorno. Añade .env con DISCORD_TOKEN=")
        raise SystemExit("DISCORD_TOKEN missing")

    try:
        bot.run(DISCORD_TOKEN)
    except discord.errors.PrivilegedIntentsRequired as exc:
        logger.error("Privileged intents required: %s", exc)
        logger.error("Enable the required privileged intents (Message Content) in the Discord Developer Portal for your application: https://discord.com/developers/applications")
        logger.error("Or remove/avoid using `message_content` intent by migrating commands to application (slash) commands.")
        print("ERROR: Privileged intents required. See logs for details.")
        raise
    except Exception:
        logger.exception("Unhandled exception while running bot")
        raise
    finally:
        # ensure MT5 is shutdown when process exits
        log_event("Bot cerrándose - Limpiando recursos...")
        try:
            stop_enhanced_dashboard()
            log_event("Dashboard inteligente detenido")
        except Exception:
            pass
        try:
            mt5_shutdown()
            log_event("MT5 desconectado")
        except Exception:
            pass
        
        # Información final del archivo de log
        intelligent_logger = get_intelligent_logger()
        current_log_file = intelligent_logger.current_log_file
        if current_log_file and os.path.exists(current_log_file):
            file_size = os.path.getsize(current_log_file)
            file_size_mb = file_size / (1024 * 1024)
            log_event(f"📝 Log final guardado: {os.path.basename(current_log_file)} ({file_size_mb:.2f} MB)")
        
        log_event("Bot cerrado completamente")
        print("=" * 60)
        print(f"📝 Sesión completa guardada en: {os.path.basename(current_log_file) if current_log_file else 'archivo desconocido'}")
        print("=" * 60)
