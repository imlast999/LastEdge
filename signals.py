"""
signals.py — Módulo de compatibilidad (P3.3 Repository Cleanup)
Re-exporta la implementación principal desde services.signals.
"""
import services.signals as _svc_signals

for _attr in dir(_svc_signals):
    if not _attr.startswith("__"):
        globals()[_attr] = getattr(_svc_signals, _attr)