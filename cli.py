#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LastEdge — Ecosystem Interactive Mini CLI (cli.py)
Controlador para desarrollo y testing local del ecosistema de 3 repositorios.
No trackeado en Git (ignorado por .gitignore).
"""

from __future__ import annotations

import os
import sys
import time
import subprocess
import urllib.request
import json
from pathlib import Path

# Force UTF-8 on Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).parent.resolve()
ENGINE_DIR = ROOT_DIR / "LastEdge Trading Engine"
LAB_DIR = ROOT_DIR / "LastEdge Strategy Lab"
APP_DIR = ROOT_DIR / "LastEdge App"

# Windows color support
os.system("")

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def get_lan_ip() -> str:
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def print_banner():
    clear_screen()
    print(f"{CYAN}{BOLD}{'=' * 75}{RESET}")
    print(f"{CYAN}{BOLD}       🚀 LASTEDGE QUANTITATIVE TRADING PLATFORM — MINI CLI{RESET}")
    print(f"{CYAN}{BOLD}{'=' * 75}{RESET}\n")
    print(f" {BOLD}--- [ EJECUCIÓN DE SERVICIOS ] ---{RESET}")
    print(f"  [{GREEN}1{RESET}] Iniciar Trading Engine (Puerto 8081 — REST API & AutoSignals)")
    print(f"  [{GREEN}2{RESET}] Iniciar Web Dashboard (Puerto 8080 — LastEdge App)")
    print(f"  [{GREEN}3{RESET}] Iniciar Strategy Lab (Puerto 8082 — API Investigación)")
    print(f"  [{GREEN}4{RESET}] Iniciar Ecosistema Completo ({BOLD}Engine + Dashboard + Strategy Lab{RESET})\n")
    print(f" {BOLD}--- [ AUDITORÍAS Y CONTROL PRE-PRODUCCIÓN ] ---{RESET}")
    print(f"  [{YELLOW}5{RESET}] Go-Live Checklist Audit (17 Controles P5.1)")
    print(f"  [{YELLOW}6{RESET}] Certificación de Bróker & Latencia MT5 (P5.4)")
    print(f"  [{YELLOW}7{RESET}] Verificación Automatizada de 11 Subsistemas (P5.2)")
    print(f"  [{YELLOW}8{RESET}] Verificación de Estabilidad a Largo Plazo (P5.3)\n")
    print(f" {BOLD}--- [ TESTEOS RÁPIDOS & DIAGNÓSTICO ] ---{RESET}")
    print(f"  [{CYAN}9{RESET}] Test de Conectividad Rápida (Health Checks 8081, 8080, 8082)")
    print(f" [{CYAN}10{RESET}] Ejecutar Suite de Tests Unitarios (Engine, Lab, App)")
    print(f" [{RED}11{RESET}] Detener Todos los Servicios (Liberar puertos 8080, 8081, 8082)")
    print(f" [{CYAN}12{RESET}] Sincronizar / Clonar Repositorios (git clone / git pull ecosistema)\n")
    print(f"  [{GRAY}0{RESET}] Salir")
    print(f"{CYAN}{'=' * 75}{RESET}")


def launch_in_window(title: str, cwd: Path, command: str):
    safe_title = title.replace("(", "").replace(")", "").replace(":", "-").strip()
    # Inyectar python -u para unbuffered streaming
    cmd_formatted = command
    if command.startswith("python "):
        cmd_formatted = "python -u -X utf8 " + command[7:]
    
    cmd_str = f"title {safe_title} & {cmd_formatted}"
    flags = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    subprocess.Popen(["cmd.exe", "/k", cmd_str], cwd=str(cwd), creationflags=flags, env=env)


def run_command_in_console(cwd: Path, command: list[str]):
    print(f"\n{GRAY}Ejecutando en: {cwd}{RESET}")
    print(f"{GRAY}Comando: {' '.join(command)}{RESET}\n")
    subprocess.run(command, cwd=cwd)


def check_health_endpoints():
    print(f"\n{BOLD}Sondeando servicios del ecosistema...{RESET}\n")
    endpoints = [
        ("Trading Engine (:8081)", "http://127.0.0.1:8081/api/health", "http://localhost:8081/api/health"),
        ("Web Dashboard (:8080)", "http://127.0.0.1:8080/api/health", "http://localhost:8080/api/health"),
        ("Strategy Lab (:8082)", "http://127.0.0.1:8082/api/health", "http://localhost:8082/api/health"),
    ]

    for name, url_ip, url_host in endpoints:
        success = False
        last_error = None

        for target_url in (url_ip, url_host):
            try:
                req = urllib.request.Request(target_url, headers={"User-Agent": "LastEdgeCLI/1.0"})
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    status = f"{GREEN}[ONLINE — HTTP {resp.status}]{RESET}"
                    details = f"service: {data.get('service', 'ok')}"
                    print(f"  {name:26} : {status} ({details})")
                    success = True
                    break
            except Exception as e:
                last_error = e

        if not success:
            err_msg = str(last_error) if last_error else "sin respuesta"
            print(f"  {name:26} : {RED}[OFFLINE]{RESET} ({err_msg})")


def stop_services():
    print(f"\n{BOLD}{YELLOW}Deteniendo servicios en puertos 8080, 8081 y 8082...{RESET}")
    ports = [8080, 8081, 8082]
    stopped = 0

    if os.name == "nt":
        for p in ports:
            try:
                out = subprocess.check_output(
                    f"netstat -ano | findstr :{p}", shell=True, stderr=subprocess.DEVNULL
                ).decode("utf-8")
                pids = set()
                for line in out.strip().split("\n"):
                    parts = line.strip().split()
                    if len(parts) >= 5 and f":{p}" in parts[1]:
                        pids.add(parts[-1])

                for pid in pids:
                    subprocess.run(f"taskkill /PID {pid} /F", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"  {GREEN}✓{RESET} Proceso {pid} en puerto {p} detenido.")
                    stopped += 1
            except Exception:
                print(f"  {GRAY}• Puerto {p} ya estaba libre.{RESET}")
    else:
        print("Operación solo soportada en Windows.")

    print(f"\n{GREEN}Listo. {stopped} proceso(s) detenidos.{RESET}")


def main():
    while True:
        try:
            print_banner()
            choice = input(f" {BOLD}Selecciona una opción [0-11]: {RESET}").strip()

            if choice == "1":
                print(f"\n{GREEN}[+] Iniciando Trading Engine en ventana separada...{RESET}")
                launch_in_window("LastEdge Trading Engine (:8081)", ENGINE_DIR, "python main.py")
                time.sleep(1)

            elif choice == "2":
                print(f"\n{GREEN}[+] Iniciando Web Dashboard & Mobile Gateway en ventana separada...{RESET}")
                launch_in_window("LastEdge Web Dashboard (:8080)", APP_DIR, "python main.py")
                lan_ip = get_lan_ip()
                print(f"  {GREEN}✓ Dashboard Local:{RESET}   http://localhost:8080")
                print(f"  {GREEN}✓ Gateway App Móvil:{RESET} http://{lan_ip}:8080\n")
                time.sleep(1)

            elif choice == "3":
                print(f"\n{GREEN}[+] Iniciando Strategy Lab en ventana separada...{RESET}")
                launch_in_window("LastEdge Strategy Lab (:8082)", LAB_DIR, "python -m services.api_server 8082")
                time.sleep(1)

            elif choice == "4":
                print(f"\n{GREEN}[+] Lanzando los 3 repositorios en consolas dedicadas...{RESET}")
                launch_in_window("LastEdge Trading Engine (:8081)", ENGINE_DIR, "python main.py")
                launch_in_window("LastEdge Strategy Lab (:8082)", LAB_DIR, "python -m services.api_server 8082")
                launch_in_window("LastEdge Web Dashboard (:8080)", APP_DIR, "python main.py")
                lan_ip = get_lan_ip()
                print(f"\n  {GREEN}✓ Trading Engine:{RESET}              http://localhost:8081")
                print(f"  {GREEN}✓ Web Dashboard & Mobile Gateway:{RESET} http://localhost:8080 (LAN: http://{lan_ip}:8080)")
                print(f"  {GREEN}✓ Strategy Lab:{RESET}                http://localhost:8082\n")
                input(f"{GRAY}Presiona Enter para volver al menú...{RESET}")

            elif choice == "5":
                clear_screen()
                print(f"{CYAN}{BOLD}[+] Ejecutando Go-Live Checklist Audit (P5.1)...{RESET}\n")
                run_command_in_console(ENGINE_DIR, ["python", "-X", "utf8", "run_go_live_checklist.py"])
                input(f"\n{GRAY}Presiona Enter para volver al menú...{RESET}")

            elif choice == "6":
                clear_screen()
                print(f"{CYAN}{BOLD}[+] Ejecutando Certificación de Bróker & Latencia (P5.4)...{RESET}\n")
                run_command_in_console(ENGINE_DIR, ["python", "-X", "utf8", "run_broker_certification.py"])
                input(f"\n{GRAY}Presiona Enter para volver al menú...{RESET}")

            elif choice == "7":
                clear_screen()
                print(f"{CYAN}{BOLD}[+] Ejecutando Verificación de Subsistemas (P5.2)...{RESET}\n")
                run_command_in_console(ENGINE_DIR, ["python", "-X", "utf8", "run_production_verifier.py"])
                input(f"\n{GRAY}Presiona Enter para volver al menú...{RESET}")

            elif choice == "8":
                clear_screen()
                print(f"{CYAN}{BOLD}[+] Ejecutando Verificación de Estabilidad (P5.3)...{RESET}\n")
                run_command_in_console(ENGINE_DIR, ["python", "-X", "utf8", "run_stability_verification.py"])
                input(f"\n{GRAY}Presiona Enter para volver al menú...{RESET}")

            elif choice == "9":
                clear_screen()
                print_banner()
                check_health_endpoints()
                input(f"\n{GRAY}Presiona Enter para volver al menú...{RESET}")

            elif choice == "10":
                clear_screen()
                print(f"{CYAN}{BOLD}[+] Ejecutando suite de tests unitarios del ecosistema...{RESET}\n")
                print(f"{BOLD}--- [1/3] Tests en LastEdge Trading Engine ---{RESET}")
                subprocess.run(["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], cwd=ENGINE_DIR)
                print(f"\n{BOLD}--- [2/3] Tests en LastEdge Strategy Lab ---{RESET}")
                subprocess.run(["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], cwd=LAB_DIR)
                print(f"\n{BOLD}--- [3/3] Tests en LastEdge App ---{RESET}")
                subprocess.run(["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], cwd=APP_DIR)
                input(f"\n{GRAY}Presiona Enter para volver al menú...{RESET}")

            elif choice == "11":
                clear_screen()
                print_banner()
                stop_services()
                input(f"\n{GRAY}Presiona Enter para volver al menú...{RESET}")

            elif choice == "12":
                clear_screen()
                bat_path = ROOT_DIR / "clone_repos.bat"
                if bat_path.exists():
                    subprocess.run(["cmd.exe", "/c", str(bat_path)], cwd=ROOT_DIR)
                else:
                    print(f"{RED}[!] No se encontró clone_repos.bat en {ROOT_DIR}{RESET}")
                input(f"\n{GRAY}Presiona Enter para volver al menú...{RESET}")

            elif choice == "0":
                print(f"\n{GREEN}👋 ¡Hasta pronto! Buen trading.{RESET}\n")
                sys.exit(0)

            else:
                print(f"\n{RED}[!] Opción '{choice}' no válida.{RESET}")
                time.sleep(1)

        except KeyboardInterrupt:
            print(f"\n\n{YELLOW}Interrupción detectada. Saliendo del CLI...{RESET}")
            sys.exit(0)


if __name__ == "__main__":
    main()
