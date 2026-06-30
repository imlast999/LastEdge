"""
Core Trading System

Sistema consolidado de trading que integra:
- Engine de orquestación principal
- Sistema de scoring flexible
- Filtros consolidados
- Gestión de riesgo

Reemplaza la fragmentación anterior y proporciona una API unificada.
"""

from .engine import (
    TradingEngine, 
    SignalContext, 
    SignalResult,
    BotState,
    get_trading_engine,
    get_current_period_start,
    active_symbols,
    is_symbol_active,
    symbol_health,
    set_btceur_health,
    record_signal,
)

from .scoring import (
    FlexibleScoring,
    ConfirmationRule,
    ScoringResult,
    get_scoring_system
)

from .filters import (
    ConsolidatedFilters,
    FilterResult,
    get_filters_system
)

from .risk import (
    RiskManager,
    RiskParameters,
    RiskAssessment,
    get_risk_manager,
    create_risk_manager
)

from .replay_engine import (
    ReplayEngine,
    ReplaySignal,
    ReplayStatistics,
    get_replay_engine
)

from .montecarlo import (
    MonteCarlo,
    MonteCarloReport,
    TradeRecord,
    run_montecarlo,
)

from .journal import (
    TradeJournal,
    get_journal,
)

from .i18n import (
    _,
    set_language,
    get_language,
    get_language_name,
    get_supported_languages,
    get_supported_languages_display,
)

# Aliases for compatibility
get_engine = get_trading_engine

# Instancias globales para compatibilidad
trading_engine = get_trading_engine()
scoring_system = get_scoring_system()
filters_system = get_filters_system()
risk_manager = get_risk_manager()

__all__ = [
    # Engine
    'TradingEngine',
    'SignalContext', 
    'SignalResult',
    'BotState',
    'get_trading_engine',
    'get_engine',  # Alias
    'trading_engine',
    
    # Scoring
    'FlexibleScoring',
    'ConfirmationRule',
    'ScoringResult',
    'get_scoring_system',
    'scoring_system',
    
    # Filters
    'ConsolidatedFilters',
    'FilterResult',
    'get_filters_system',
    'filters_system',
    
    # Risk
    'RiskManager',
    'RiskParameters',
    'RiskAssessment',
    'get_risk_manager',
    'create_risk_manager',
    'risk_manager',
    
    # Replay Engine
    'ReplayEngine',
    'ReplaySignal',
    'ReplayStatistics',
    'get_replay_engine',

    # Monte Carlo
    'MonteCarlo',
    'MonteCarloReport',
    'TradeRecord',
    'run_montecarlo',

    # Trade Journal
    'TradeJournal',
    'get_journal',
    
    # Utilities
    'get_current_period_start',

    # Símbolos activos
    'active_symbols',
    'is_symbol_active',

    # Estado BTCEUR (visibilidad)
    'symbol_health',
    'set_btceur_health',
    'record_signal',
]