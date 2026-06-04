#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hypothesis_status.py — Vista rápida del estado de todas las hipótesis

Uso:
    python research/tools/hypothesis_status.py
    python research/tools/hypothesis_status.py --verbose
    python research/tools/hypothesis_status.py --status RETESTING
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# ─── Colores ANSI ───────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
CYAN   = "\033[36m"
GRAY   = "\033[90m"
BLUE   = "\033[34m"

STATUS_COLOR = {
    "IDEA":          GRAY,
    "TESTING":       YELLOW,
    "VALIDATING":    CYAN,
    "RETESTING":     BLUE,
    "PAPER_TRADING": GREEN,
    "LIVE":          BOLD + GREEN,
    "FAILED":        RED,
    "ARCHIVED":      GRAY,
}

STATUS_ICON = {
    "IDEA":          "💡",
    "TESTING":       "🔬",
    "VALIDATING":    "📊",
    "RETESTING":     "🔁",
    "PAPER_TRADING": "📋",
    "LIVE":          "🟢",
    "FAILED":        "❌",
    "ARCHIVED":      "📦",
}


def load_hypotheses(hypotheses_dir: Path) -> list:
    hypotheses = []
    for f in sorted(hypotheses_dir.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fp:
                h = json.load(fp)
            h["_file"] = f.name
            hypotheses.append(h)
        except Exception as e:
            print(f"  ⚠️  Error leyendo {f.name}: {e}")
    return hypotheses


def print_summary(hypotheses: list, filter_status: str = None):
    filtered = hypotheses
    if filter_status:
        filtered = [h for h in hypotheses if h.get("status", "").upper() == filter_status.upper()]

    if not filtered:
        print(f"  No hay hipótesis con estado '{filter_status}'.")
        return

    print()
    print(f"  {'ID':<30} {'SYMBOL':<8} {'STATUS':<16} {'EVIDENCIA':<10} {'PENDIENTE'}")
    print("  " + "─" * 90)

    for h in filtered:
        hid      = h.get("id", "?")
        symbol   = h.get("symbol", "?")
        status   = h.get("status", "?")
        evidence = len(h.get("evidence", []))
        pending  = ", ".join(h.get("tests_pending", [])[:2])
        if len(h.get("tests_pending", [])) > 2:
            pending += f" (+{len(h['tests_pending'])-2})"

        color = STATUS_COLOR.get(status, "")
        icon  = STATUS_ICON.get(status, "·")

        print(f"  {hid:<30} {symbol:<8} {color}{icon} {status:<14}{RESET} {evidence:<10} {GRAY}{pending}{RESET}")

    print()
    # Resumen por estado
    by_status = {}
    for h in hypotheses:
        s = h.get("status", "UNKNOWN")
        by_status[s] = by_status.get(s, 0) + 1

    print("  Resumen: " + "  ".join(
        f"{STATUS_COLOR.get(s,'')}{STATUS_ICON.get(s,'·')} {s}: {n}{RESET}"
        for s, n in sorted(by_status.items())
    ))
    print()


def print_verbose(hypotheses: list, filter_status: str = None):
    filtered = hypotheses
    if filter_status:
        filtered = [h for h in hypotheses if h.get("status", "").upper() == filter_status.upper()]

    for h in filtered:
        status = h.get("status", "?")
        color  = STATUS_COLOR.get(status, "")
        icon   = STATUS_ICON.get(status, "·")

        print()
        print(f"  {BOLD}{'─'*60}{RESET}")
        print(f"  {BOLD}{h.get('id', '?')}{RESET}  [{color}{icon} {status}{RESET}]  {h.get('symbol','')}")
        print()
        print(f"  {CYAN}Hipótesis:{RESET}")
        print(f"    {h.get('hypothesis', 'N/A')}")
        print()

        evidence = h.get("evidence", [])
        if evidence:
            print(f"  {CYAN}Evidencia ({len(evidence)} run(s)):{RESET}")
            for e in evidence:
                verdict_color = GREEN if e.get("verdict") == "ROBUST" else RED if e.get("verdict") == "FAILED" else YELLOW
                print(f"    [{e.get('date','')}] {verdict_color}{e.get('verdict','?')}{RESET} — {e.get('summary','')[:80]}")

        passed  = h.get("tests_passed", [])
        pending = h.get("tests_pending", [])
        failed  = h.get("tests_failed", [])

        if passed or pending or failed:
            print()
            if passed:  print(f"  {GREEN}✓ Pasados:{RESET}  {', '.join(passed)}")
            if pending: print(f"  {YELLOW}⏳ Pendientes:{RESET} {', '.join(pending)}")
            if failed:  print(f"  {RED}✗ Fallidos:{RESET}  {', '.join(failed)}")

        if h.get("notes"):
            print()
            print(f"  {GRAY}Notas: {h['notes'][:120]}{RESET}")


def main():
    parser = argparse.ArgumentParser(description="Vista de estado de hipótesis")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar detalle completo")
    parser.add_argument("--status", "-s", type=str, help="Filtrar por estado (ej: RETESTING, FAILED)")
    args = parser.parse_args()

    # Localizar directorio de hipótesis (relativo al script o a la raíz del proyecto)
    script_dir = Path(__file__).parent
    candidates = [
        script_dir.parent / "hypotheses",
        Path.cwd() / "research" / "hypotheses",
    ]
    hypotheses_dir = None
    for c in candidates:
        if c.exists():
            hypotheses_dir = c
            break

    if hypotheses_dir is None:
        print("  ❌  No se encontró research/hypotheses/")
        sys.exit(1)

    hypotheses = load_hypotheses(hypotheses_dir)

    if not hypotheses:
        print("  No hay hipótesis registradas todavía.")
        sys.exit(0)

    print(f"\n  {BOLD}HYPOTHESIS REGISTRY{RESET}  —  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  {len(hypotheses)} hipótesis  |  {hypotheses_dir}")

    if args.verbose:
        print_verbose(hypotheses, filter_status=args.status)
    else:
        print_summary(hypotheses, filter_status=args.status)


if __name__ == "__main__":
    main()
