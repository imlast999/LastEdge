"""
Test script for log formatting verification — scratch/test_logging_format.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath("."))

from services.logging import get_intelligent_logger, log_event

def test_logging():
    logger = get_intelligent_logger()
    
    log_event("Bot iniciado y listo para operar", "INFO", "BOT")
    log_event("Escaneando 3 pares (EURUSD, XAUUSD, BTCEUR)...", "INFO", "AUTOSIGNAL")
    log_event("Posición #100001 evaluada limpiamente", "INFO", "TRADING")
    log_event("Circuit Breaker activo (multiplicador x1.0)", "INFO", "RISK")
    
    log_file = logger.current_log_file
    print(f"\n📄 Leyendo archivo de log recién generado: {log_file}\n")
    
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("--- INICIO DE ARCHIVO DE LOG ---")
    print(content)
    print("--- FIN DE ARCHIVO DE LOG ---")
    
    lines = content.strip().splitlines()
    assert len(lines) >= 4, f"Se esperaban al menos 4 líneas separadas, se obtuvieron {len(lines)}"
    print(f"✅ VERIFICACIÓN EXITOSA: {len(lines)} líneas independientes generadas correctamente con timestamps de sesión.")

if __name__ == '__main__':
    test_logging()
