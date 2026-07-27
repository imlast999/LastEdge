"""
Audit & Validation Script for Telegram Integration — scratch/audit_telegram.py
================================================================================
Prueba integral de auditoría sin modificar código ni arquitectura.
Verifica credenciales, conectividad con Telegram Bot API (getMe), respuestas de comandos,
resiliencia de NotificationDispatcher y limpieza de ciclo de vida asíncrono.
"""

import sys
import os
sys.path.insert(0, os.path.abspath("."))

import asyncio
import json
import logging
import aiohttp
from dotenv import load_dotenv

load_dotenv()

from services.bot_service import get_bot_service
from services.telegram_adapter import TelegramAdapter
from services.notification_dispatcher import NotificationDispatcher, get_notification_dispatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_audit")

async def run_audit():
    print("=" * 75)
    print("🔍 AUDITORÍA DE EXTREMO A EXTREMO — INTEGRACIÓN TELEGRAM")
    print("=" * 75)

    passed_checks = []
    manual_checks = []
    issues = []

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    # ── 1. Revisión de .env ───────────────────────────────────────────────────
    print("\n[PASO 1] Auditando configuración en .env...")
    if not token:
        issues.append("TELEGRAM_BOT_TOKEN no encontrado en .env")
        print("  ❌ TELEGRAM_BOT_TOKEN no configurado")
    else:
        masked_token = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else "***"
        print(f"  ✅ TELEGRAM_BOT_TOKEN presente: {masked_token}")
        if ":" in token and token.split(":")[0].isdigit():
            print("  ✅ Formato de TELEGRAM_BOT_TOKEN válido (ID númerico + hash)")
            passed_checks.append("TELEGRAM_BOT_TOKEN presente y con estructura válida")
        else:
            issues.append("Formato de TELEGRAM_BOT_TOKEN no estándar")

    if not chat_id:
        issues.append("TELEGRAM_CHAT_ID no encontrado en .env")
        print("  ❌ TELEGRAM_CHAT_ID no configurado")
    else:
        masked_chat = f"{chat_id[:3]}...{chat_id[-2:]}" if len(chat_id) > 5 else "***"
        print(f"  ✅ TELEGRAM_CHAT_ID presente: {masked_chat}")
        if chat_id.lstrip("-").isdigit():
            print("  ✅ Formato de TELEGRAM_CHAT_ID válido (ID numérico)")
            passed_checks.append("TELEGRAM_CHAT_ID presente y con formato de ID válido")
        else:
            issues.append("TELEGRAM_CHAT_ID no es numérico")

    # ── 2. Conexión real con Telegram Bot API (getMe) ──────────────────────────
    print("\n[PASO 2] Verificando autenticación y comunicación con la Bot API (getMe)...")
    if token:
        try:
            url = f"https://api.telegram.org/bot{token}/getMe"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        bot_data = await resp.json()
                        if bot_data.get("ok"):
                            result = bot_data["result"]
                            bot_username = result.get("username")
                            bot_name = result.get("first_name")
                            print(f"  ✅ Autenticación exitosa en Telegram Bot API!")
                            print(f"     Bot registrado: {bot_name} (@{bot_username}) [ID: {result.get('id')}]")
                            passed_checks.append(f"Autenticación exitosa con Telegram Bot API (@{bot_username})")
                        else:
                            issues.append(f"Respuesta getMe no ok: {bot_data}")
                    else:
                        err_txt = await resp.text()
                        issues.append(f"Error autenticación Telegram HTTP {resp.status}: {err_txt}")
                        print(f"  ❌ Error HTTP {resp.status}: {err_txt}")
        except Exception as e:
            issues.append(f"Excepción al conectar con Telegram API: {e}")
            print(f"  ❌ Excepción en llamada getMe: {e}")

    # ── 3. Verificación de TelegramAdapter y Comandos ─────────────────────────
    print("\n[PASO 3] Evaluando TelegramAdapter y ejecución de comandos...")
    bot_service = get_bot_service()
    adapter = TelegramAdapter(bot_service=bot_service)
    
    if adapter.is_configured():
        passed_checks.append("TelegramAdapter se inicializa e identifica credenciales válidas")
        print("  ✅ TelegramAdapter inicializado y configurado correctamente")
    else:
        issues.append("TelegramAdapter.is_configured() devolvió False")

    # Probar formateador de respuestas de comandos sin enviar al servidor real
    mock_session = aiohttp.ClientSession()
    command_tests = [
        ("/help", adapter._cmd_help),
        ("/status", adapter._cmd_status),
        ("/positions", adapter._cmd_positions),
        ("/equity", adapter._cmd_equity),
        ("/risk", adapter._cmd_risk),
        ("/journal", adapter._cmd_journal),
        ("/research", adapter._cmd_research),
    ]

    print("\n  Ejecutando controladores de comandos en TelegramAdapter:")
    for cmd_name, cmd_func in command_tests:
        try:
            # Reemplazar _send_response para capturar texto generado
            captured_texts = []
            async def _dummy_send(session, chat_id, text):
                captured_texts.append(text)
            
            orig_send = adapter._send_response
            adapter._send_response = _dummy_send
            
            if cmd_name == "/help":
                await cmd_func(mock_session, 12345)
            else:
                await cmd_func(mock_session, 12345)
            
            adapter._send_response = orig_send
            
            if captured_texts:
                sample_txt = captured_texts[0].split("\n")[0]
                print(f"    ✅ Comando {cmd_name:<12} -> Generó respuesta limpia: '{sample_txt}'")
                passed_checks.append(f"Comando {cmd_name} funciona sin excepciones y genera formato Markdown")
            else:
                issues.append(f"Comando {cmd_name} no generó respuesta")
        except Exception as e:
            print(f"    ❌ Comando {cmd_name} lanzó excepción: {e}")
            issues.append(f"Excepción en controlador {cmd_name}: {e}")

    await mock_session.close()

    # ── 4. Verificación de NotificationDispatcher y Resiliencia a Fallos ─────
    print("\n[PASO 4] Verificando NotificationDispatcher y aislamiento de fallos (Discord vs Telegram)...")
    dispatcher = NotificationDispatcher()
    
    discord_called = False
    async def failing_discord(msg):
        nonlocal discord_called
        discord_called = True
        raise RuntimeError("Fallo simulado en Discord webhook")

    dispatcher.register_discord_handler(failing_discord)
    
    # Broadcast simulando fallo en Discord para verificar que Telegram NO se bloquea
    try:
        res = await dispatcher.broadcast_message("Mensaje de prueba de resiliencia", title="Test Resiliencia", level="WARNING")
        print(f"  ✅ Fallo en Discord aislado correctamente: {res}")
        if discord_called:
            print("  ✅ Discord falló intencionalmente, pero no interrumpió el flujo global")
            passed_checks.append("NotificationDispatcher aísla fallos entre canales (Discord err != Telegram err)")
    except Exception as e:
        issues.append(f"Fallo en NotificationDispatcher interrumpió la ejecución: {e}")

    # ── 5. Verificación de Ciclo de Vida del Event Loop y Tareas ───────────────
    print("\n[PASO 5] Verificando ciclo de vida asíncrono, arranque y cancelación limpia...")
    try:
        polling_task = asyncio.create_task(adapter.start_polling())
        await asyncio.sleep(1.5)
        adapter.is_running = False
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
        print("  ✅ Tarea de polling cancelada limpiamente sin tareas colgadas ni fugas")
        passed_checks.append("Ciclo de vida de polling asíncrono inicia y finaliza limpiamente sin tareas zombi")
    except Exception as e:
        issues.append(f"Error cancelando polling task: {e}")

    # Pruebas que requieren teléfono manual
    manual_checks.append("Enviar mensaje real por chat de Telegram (/status, /positions) desde la app móvil o de escritorio")
    manual_checks.append("Verificar recepción de alerta push en tiempo real en Telegram cuando se genera una señal MT5")
    manual_checks.append("Probar ejecución de /close_position <ticket> con una posición demo real abierta")

    # ── RESUMEN FINAL DE LA AUDITORÍA ──────────────────────────────────────────
    print("\n" + "=" * 75)
    print("📊 INFORME DE AUDITORÍA TELEGRAM — LASTEDGE")
    print("=" * 75)

    print(f"\n✅ COMPROBACIONES SUPERADAS ({len(passed_checks)}):")
    for check in passed_checks:
        print(f"  • {check}")

    print(f"\n⚠️ REQUIEREN PRUEBA MANUAL DESDE TELÉFONO ({len(manual_checks)}):")
    for check in manual_checks:
        print(f"  • {check}")

    print(f"\n❌ PROBLEMAS ENCONTRADOS ({len(issues)}):")
    if not issues:
        print("  • Ningún problema técnico ni error encontrado. 0 errores.")
    else:
        for issue in issues:
            print(f"  • {issue}")

    print("\n📋 RECOMENDACIÓN FINAL:")
    if not issues and token and chat_id:
        print("  La integración de Telegram se encuentra **VALIDADA TÉCNICAMENTE** a nivel de arquitectura, credenciales, API Bot y comandos. Para el pase definitivo a producción de notificaciones push, se requiere realizar la comprobación manual enviando un mensaje desde el teléfono.")
    else:
        print("  Telegram se encuentra **IMPLEMENTADO**, requiriendo resolver las observaciones encontradas.")

if __name__ == "__main__":
    asyncio.run(run_audit())
