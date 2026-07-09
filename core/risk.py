"""
core/risk.py — DEPRECADO

Este archivo se mantiene únicamente por compatibilidad con imports directos
del tipo `from core.risk import RiskManager`.

El sistema ha sido migrado al paquete `core/risk/` (Risk Engine v2).

Toda la lógica real vive en:
    core/risk/engine.py          — RiskEngine (motor principal)
    core/risk/position_sizer.py  — PositionSizer (cálculo de lote)
    core/risk/margin_checker.py  — MarginChecker (validación de margen)
    core/risk/portfolio_risk.py  — PortfolioRisk (riesgo del portfolio)
    core/risk/config.py          — RiskConfig (configuración)

NO añadir lógica nueva aquí. Usar get_risk_engine() en su lugar.
"""

# Re-export completo desde el paquete core/risk/
from core.risk import (  # noqa: F401
    RiskEngine,
    RiskDecision,
    get_risk_engine,
    create_risk_engine,
    RiskConfig,
    load_risk_config,
    PositionSizer,
    SizingResult,
    MarginChecker,
    MarginCheckResult,
    PortfolioRisk,
    PortfolioRiskResult,
    PositionRisk,
    # Legacy backward compat
    RiskManager,
    RiskParameters,
    RiskAssessment,
    get_risk_manager,
    create_risk_manager,
)