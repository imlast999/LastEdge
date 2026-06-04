#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_hypothesis.py — Actualiza el estado o añade evidencia a una hipótesis

Uso:
    # Cambiar estado de una hipótesis:
    python research/tools/update_hypothesis.py --id eurusd_simple --status PAPER_TRADING --reason "Pasó walk-forward con 3/4 ventanas estables"

    # Añadir evidencia desde una Run Card:
    python research/tools/update_hypothesis.py --id eurusd_simple --add-evidence RC_20260610_walkforward.json

    # Mover test de pending a passed:
    python research/tools/update_hypothesis.py --id eurusd_simple --pass-test walk_forward

    # Mover test de pending a failed:
    python research/tools/update_hypothesis.py --id eurusd_simple --fail-test walk_forward
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime


def load_hypothesis(hypotheses_dir: Path, hyp_id: str) -> tuple:
    """Carga un archivo de hipótesis. Retorna (path, dict)."""
    path = hypotheses_dir / f"{hyp_id}.json"
    if not path.exists():
        return None, None
    with open(path, encoding="utf-8") as f:
        return path, json.load(f)


def save_hypothesis(path: Path, hyp: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(hyp, f, indent=2, ensure_ascii=False)


def update_status(hyp: dict, new_status: str, reason: str, date: str) -> dict:
    old_status = hyp.get("status")
    hyp["status"] = new_status

    history_entry = {
        "date": date,
        "from_status": old_status,
        "to_status": new_status,
        "reason": reason,
    }
    if "history" not in hyp:
        hyp["history"] = []
    hyp["history"].append(history_entry)

    return hyp


def add_evidence_from_run_card(hyp: dict, run_card_path: Path, hyp_id: str) -> dict:
    """Añade evidencia desde una Run Card al hypothesis.
    Soporta dos formatos:
      - retest_multi_horizon: tiene results_summary[hyp_id]
      - walk_forward / monte_carlo / paper_trading_review: tiene results directamente
    """
    with open(run_card_path, encoding="utf-8") as f:
        card = json.load(f)

    run_type = card.get("type", "")

    # ── Formato retest (results_summary por estrategia) ──────────────────────
    if "results_summary" in card:
        strategy_result = card.get("results_summary", {}).get(hyp_id)
        if not strategy_result:
            print(f"  ⚠️  La Run Card no tiene resultados para '{hyp_id}'. Disponibles: {list(card.get('results_summary', {}).keys())}")
            return hyp

        pf_vals = list(strategy_result.get("pf_by_horizon", {}).values())
        pf_str  = f"PF {min(pf_vals):.3f}–{max(pf_vals):.3f}" if pf_vals else "PF ?"

        evidence_entry = {
            "run_id":  card.get("run_id", "?"),
            "type":    run_type,
            "date":    card.get("date", "?"),
            "verdict": strategy_result.get("verdict", "?"),
            "summary": f"{strategy_result.get('reason','')} | {pf_str} | degradation={strategy_result.get('degradation_score')}",
            "metrics": {
                "pf_by_horizon":    strategy_result.get("pf_by_horizon"),
                "wr_by_horizon":    strategy_result.get("wr_by_horizon"),
                "degradation_score":strategy_result.get("degradation_score"),
                "robustness_score": strategy_result.get("robustness_score"),
            },
        }

    # ── Formato walk-forward / monte_carlo / paper_trading_review ────────────
    else:
        results = card.get("results", {})
        verdict = results.get("stability_rating") or results.get("verdict") or "?"

        # Construir summary según tipo
        if run_type == "walk_forward":
            summary = (
                f"stability={verdict} | "
                f"windows={results.get('windows_stable')}/{results.get('windows_total')} | "
                f"avg_test_pf={results.get('avg_test_pf')} | "
                f"consistency={results.get('consistency_score')}"
            )
            metrics = {
                "stability_rating":  verdict,
                "windows_stable":    results.get("windows_stable"),
                "windows_total":     results.get("windows_total"),
                "avg_train_pf":      results.get("avg_train_pf"),
                "avg_test_pf":       results.get("avg_test_pf"),
                "avg_pf_degradation":results.get("avg_pf_degradation"),
                "consistency_score": results.get("consistency_score"),
                "worst_window_pf":   results.get("worst_window_pf_test"),
            }
        elif run_type == "monte_carlo":
            summary = (
                f"verdict={verdict} | "
                f"ruin_prob={results.get('ruin_probability')} | "
                f"dd_p95={results.get('expected_drawdown_p95')}"
            )
            metrics = results
        elif run_type == "paper_trading_review":
            summary = (
                f"signals={results.get('signals_closed')} | "
                f"wr={results.get('winrate')} | "
                f"net_pips={results.get('net_pips')} | "
                f"matches_backtest={results.get('matches_backtest_expectation')}"
            )
            metrics = results
        else:
            summary = card.get("what", "")
            metrics = results

        evidence_entry = {
            "run_id":  card.get("run_id", "?"),
            "type":    run_type,
            "date":    card.get("date", "?"),
            "verdict": verdict,
            "summary": summary,
            "metrics": metrics,
        }

    if "evidence" not in hyp:
        hyp["evidence"] = []
    hyp["evidence"].append(evidence_entry)

    print(f"  ✅  Evidencia añadida: {evidence_entry['run_id']} → {evidence_entry['verdict']}")
    return hyp


def move_test(hyp: dict, test_name: str, from_list: str, to_list: str) -> dict:
    """Mueve un test entre listas (pending→passed, pending→failed)."""
    src = hyp.get(from_list, [])
    dst = hyp.get(to_list, [])

    if test_name not in src:
        # Añadir igualmente si no estaba en pending
        print(f"  ⚠️  '{test_name}' no estaba en {from_list}. Añadiéndolo a {to_list} de todas formas.")
    else:
        src.remove(test_name)

    if test_name not in dst:
        dst.append(test_name)

    hyp[from_list] = src
    hyp[to_list]   = dst
    return hyp


def main():
    parser = argparse.ArgumentParser(description="Actualiza una hipótesis del registry")
    parser.add_argument("--id",           required=True, type=str, help="ID de la hipótesis (ej: eurusd_simple)")
    parser.add_argument("--status",       type=str, help="Nuevo estado")
    parser.add_argument("--reason",       type=str, default="", help="Motivo del cambio de estado")
    parser.add_argument("--date",         type=str, default=datetime.now().strftime("%Y-%m-%d"), help="Fecha (YYYY-MM-DD)")
    parser.add_argument("--add-evidence", type=str, help="Ruta a Run Card desde la que añadir evidencia")
    parser.add_argument("--pass-test",    type=str, help="Mover test de pending a tests_passed")
    parser.add_argument("--fail-test",    type=str, help="Mover test de pending a tests_failed")
    parser.add_argument("--dry-run",      action="store_true", help="Mostrar cambios sin guardar")
    args = parser.parse_args()

    # Localizar directorio
    script_dir      = Path(__file__).parent
    project_root    = script_dir.parent.parent
    hypotheses_dir  = project_root / "research" / "hypotheses"

    path, hyp = load_hypothesis(hypotheses_dir, args.id)
    if hyp is None:
        print(f"\n  ❌  Hipótesis '{args.id}' no encontrada en {hypotheses_dir}")
        available = [f.stem for f in hypotheses_dir.glob("*.json")] if hypotheses_dir.exists() else []
        if available:
            print(f"  Disponibles: {', '.join(available)}")
        sys.exit(1)

    print(f"\n  Hipótesis: {args.id}  |  Estado actual: {hyp.get('status','?')}")

    changed = False

    # Cambio de estado
    if args.status:
        valid_statuses = ["IDEA", "TESTING", "VALIDATING", "RETESTING", "PAPER_TRADING", "LIVE", "FAILED", "ARCHIVED"]
        if args.status.upper() not in valid_statuses:
            print(f"  ❌  Estado inválido '{args.status}'. Válidos: {', '.join(valid_statuses)}")
            sys.exit(1)
        hyp     = update_status(hyp, args.status.upper(), args.reason, args.date)
        changed = True
        print(f"  Estado → {args.status.upper()}  (razón: {args.reason or 'no especificada'})")

    # Añadir evidencia
    if args.add_evidence:
        rc_path = Path(args.add_evidence)
        if not rc_path.exists():
            # Intentar relativo a run_cards dir
            rc_path = project_root / "research" / "run_cards" / args.add_evidence
        if not rc_path.exists():
            print(f"  ❌  Run Card no encontrada: {args.add_evidence}")
            sys.exit(1)
        hyp     = add_evidence_from_run_card(hyp, rc_path, args.id)
        changed = True

    # Mover test a passed
    if args.pass_test:
        hyp     = move_test(hyp, args.pass_test, "tests_pending", "tests_passed")
        changed = True
        print(f"  Test '{args.pass_test}': pending → passed")

    # Mover test a failed
    if args.fail_test:
        hyp     = move_test(hyp, args.fail_test, "tests_pending", "tests_failed")
        changed = True
        print(f"  Test '{args.fail_test}': pending → failed")

    if not changed:
        print("  ⚠️  No se especificó ningún cambio. Usa --status, --add-evidence, --pass-test o --fail-test.")
        sys.exit(0)

    if args.dry_run:
        print(f"\n  DRY RUN — resultado:\n")
        print(json.dumps(hyp, indent=2, ensure_ascii=False)[:2000])
    else:
        save_hypothesis(path, hyp)
        print(f"\n  ✅  Guardado: {path}")


if __name__ == "__main__":
    main()
