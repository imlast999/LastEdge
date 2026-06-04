#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_card_generator.py — Genera Run Cards desde session_summary.json

Uso:
    # Generar desde el último session_summary.json encontrado:
    python research/tools/run_card_generator.py

    # Generar desde un session específico:
    python research/tools/run_card_generator.py --session backtest_results/session_20260601_022844/session_20260601_022844/session_summary.json

    # Modo dry-run (muestra sin guardar):
    python research/tools/run_card_generator.py --dry-run

Qué guarda y qué no:
    GUARDA: run_id, tipo, fecha, estrategias, veredictos, métricas clave, parámetros usados, hipótesis relacionadas
    NO GUARDA: equity_curves completas, señales individuales (están en session_summary.json)
               timestamps internos de cada señal, configuración de logging
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime


def find_latest_session(backtest_results_dir: Path) -> Path | None:
    """Busca el session_summary.json más reciente."""
    summaries = list(backtest_results_dir.rglob("session_summary.json"))
    if not summaries:
        return None
    return max(summaries, key=lambda p: p.stat().st_mtime)


def load_hypothesis_ids(hypotheses_dir: Path) -> set:
    """Carga los IDs de hipótesis conocidas para mapear automáticamente."""
    ids = set()
    if hypotheses_dir.exists():
        for f in hypotheses_dir.glob("*.json"):
            ids.add(f.stem)
    return ids


def classify_run_type(session: dict) -> str:
    """Infiere el tipo de run desde el contenido del session."""
    bars = session.get("bars_tested", [])
    if len(bars) >= 3:
        return "retest_multi_horizon"
    elif len(bars) == 1:
        return "retest_single"
    return "backtest"


def extract_strategy_result(strategy_id: str, strategy_data: dict, hypothesis_ids: set) -> dict:
    """Extrae las métricas clave de una estrategia — descarta equity_curve y datos voluminosos."""
    comparison = strategy_data.get("comparison", {})
    results    = strategy_data.get("results", [])

    # Métricas clave por horizonte
    pf_by_horizon = comparison.get("pf_by_horizon", {})
    wr_by_horizon = comparison.get("wr_by_horizon", {})
    dd_by_horizon = comparison.get("dd_by_horizon", {})

    # Parámetros usados (del primer resultado disponible)
    params = {}
    if results:
        params = results[0].get("params", {})

    # Circuit breaker info (del primer resultado disponible)
    cb_info = {}
    if results:
        cb_info = {
            "cb_losses": results[0].get("cb_losses", 0),
            "cb_pause":  results[0].get("cb_pause", 0),
        }

    # Total señales (horizonte más largo)
    signals_by_horizon = {}
    for r in results:
        signals_by_horizon[str(r.get("bars", "?"))] = {
            "signals_total": r.get("signals_total", 0),
            "wins": r.get("wins", 0),
            "losses": r.get("losses", 0),
        }

    return {
        "hypothesis_id": strategy_id if strategy_id in hypothesis_ids else None,
        "symbol": strategy_data.get("symbol", "?"),
        "verdict": comparison.get("classification", "?"),
        "reason": comparison.get("reason", ""),
        "pf_by_horizon": pf_by_horizon,
        "wr_by_horizon": wr_by_horizon,
        "dd_by_horizon": dd_by_horizon,
        "degradation_score": comparison.get("degradation_score"),
        "robustness_score": comparison.get("robustness_score"),
        "consistency": comparison.get("consistency"),
        "params": params,
        "circuit_breaker": cb_info,
        "signals_by_horizon": signals_by_horizon,
    }


def generate_run_card(session_path: Path, hypothesis_ids: set) -> dict:
    """Genera una Run Card desde un session_summary.json."""
    with open(session_path, encoding="utf-8") as f:
        session = json.load(f)

    timestamp = session.get("timestamp", "unknown")
    run_type  = classify_run_type(session)
    bars      = session.get("bars_tested", [])
    date_str  = timestamp[:8]  # YYYYMMDD
    date_fmt  = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    run_id = f"{run_type}_{timestamp}"

    # Estrategias
    strategies_raw = session.get("strategies", {})
    results_summary = {}
    for strat_id, strat_data in strategies_raw.items():
        results_summary[strat_id] = extract_strategy_result(strat_id, strat_data, hypothesis_ids)

    # Decisiones automáticas inferidas
    decisions = []
    for strat_id, res in results_summary.items():
        verdict = res.get("verdict", "")
        if verdict == "FAILED":
            decisions.append(f"{strat_id} → FAILED — revisar hipótesis")
        elif verdict == "ROBUST":
            decisions.append(f"{strat_id} → ROBUST — avanza a walk-forward/monte_carlo")
        elif verdict == "UNSTABLE":
            decisions.append(f"{strat_id} → UNSTABLE — excluir de pipeline")
        else:
            decisions.append(f"{strat_id} → {verdict} — revisar manualmente")

    card = {
        "run_id": run_id,
        "type": run_type,
        "date": date_fmt,
        "timestamp": timestamp,
        "what": f"Retest automático {'multi-horizonte' if len(bars) > 1 else 'single'} — {len(strategies_raw)} estrategias en {bars} velas H1.",
        "reproducibility": {
            "session_dir": str(session_path.parent),
            "bars": bars,
            "timeframe": "H1",
            "no_cb_mode": session.get("no_cb", False),
            "total_elapsed_seconds": session.get("total_elapsed_s"),
        },
        "strategies_tested": list(strategies_raw.keys()),
        "results_summary": results_summary,
        "decisions_triggered": decisions,
        "generated_at": datetime.now().isoformat(),
        "generated_from": str(session_path),
    }

    return card


def main():
    parser = argparse.ArgumentParser(description="Genera Run Cards desde session_summary.json")
    parser.add_argument("--session", type=str, help="Ruta al session_summary.json")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar sin guardar")
    parser.add_argument("--output-dir", type=str, help="Directorio de salida (default: research/run_cards/)")
    args = parser.parse_args()

    # Localizar raíz del proyecto
    script_dir   = Path(__file__).parent
    project_root = script_dir.parent.parent

    # Directorios
    backtest_dir    = project_root / "backtest_results"
    hypotheses_dir  = project_root / "research" / "hypotheses"
    run_cards_dir   = Path(args.output_dir) if args.output_dir else project_root / "research" / "run_cards"

    # Cargar IDs de hipótesis conocidas
    hypothesis_ids = load_hypothesis_ids(hypotheses_dir)
    print(f"\n  Hipótesis conocidas: {', '.join(sorted(hypothesis_ids)) or 'ninguna'}")

    # Localizar session_summary.json
    if args.session:
        session_path = Path(args.session)
    else:
        session_path = find_latest_session(backtest_dir)
        if session_path is None:
            print(f"\n  ❌  No se encontró session_summary.json en {backtest_dir}")
            print("  Usa --session para especificar la ruta.")
            sys.exit(1)
        print(f"  Session encontrado: {session_path}")

    if not session_path.exists():
        print(f"\n  ❌  No existe: {session_path}")
        sys.exit(1)

    # Generar Run Card
    print(f"\n  Generando Run Card desde: {session_path.name}")
    card = generate_run_card(session_path, hypothesis_ids)

    run_id   = card["run_id"]
    filename = f"RC_{run_id[:30].replace('/', '_')}.json"

    if args.dry_run:
        print(f"\n  {'─'*60}")
        print(f"  DRY RUN — se generaría: {filename}")
        print(f"  {'─'*60}")
        print(json.dumps(card, indent=2, ensure_ascii=False)[:3000])
        if len(json.dumps(card)) > 3000:
            print("  ... (truncado para dry-run)")
    else:
        run_cards_dir.mkdir(parents=True, exist_ok=True)
        output_path = run_cards_dir / filename

        # Evitar sobreescribir
        if output_path.exists():
            print(f"\n  ⚠️   Ya existe: {output_path}")
            print("  Sobreescribiendo...")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(card, f, indent=2, ensure_ascii=False)

        print(f"\n  ✅  Run Card guardada: {output_path}")

    # Mostrar resumen
    print(f"\n  {'─'*60}")
    print(f"  Run ID   : {card['run_id']}")
    print(f"  Tipo     : {card['type']}")
    print(f"  Fecha    : {card['date']}")
    print(f"  Strategies: {', '.join(card['strategies_tested'])}")
    print()
    for strat, res in card["results_summary"].items():
        verdict = res.get("verdict", "?")
        icon = "✅" if verdict == "ROBUST" else "❌" if verdict in ("FAILED", "UNSTABLE") else "⚠️"
        pf_vals = list(res.get("pf_by_horizon", {}).values())
        pf_str = f"PF {min(pf_vals):.3f}–{max(pf_vals):.3f}" if pf_vals else "PF ?"
        print(f"    {icon} {strat:<35} {verdict:<12} {pf_str}")
    print()


if __name__ == "__main__":
    main()
