"""
Dashboard Service Module (Bridge / Wrapper)
===========================================
Re-exporta la funcionalidad de services.dashboard para mantener compatibilidad
total de importaciones sin duplicar código entre la carpeta dashboard/ y services/.
"""

from services.dashboard import (
    DashboardService,
    DashboardMetrics,
    SignalEvent,
    ReusableThreadingHTTPServer,
    dashboard_service,
    get_dashboard_service,
    start_enhanced_dashboard,
    stop_enhanced_dashboard,
    add_signal_to_enhanced_dashboard,
    update_dashboard_stats,
)

__all__ = [
    'DashboardService',
    'DashboardMetrics',
    'SignalEvent',
    'ReusableThreadingHTTPServer',
    'dashboard_service',
    'get_dashboard_service',
    'start_enhanced_dashboard',
    'stop_enhanced_dashboard',
    'add_signal_to_enhanced_dashboard',
    'update_dashboard_stats',
]
