#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
new_run_card.py — Crea una Run Card vacía para experimentos manuales
(walk-forward individual, monte carlo, paper trading review)

Uso:
    python research/tools/new_run_card.py --type walk_forward --strategy eurusd_simple
    python research/tools/new_run_card.py --type monte_carlo --strategy xauusd_momentum
    python research/tools/new_run_card.py --type paper_trading_review --strategy eurusd_simple --date 2026-06-07

    # Ver tipos disponibles:
    python research/tools/new_run_card.py --list-types
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

RUN_TYPES = {
    "walk_forward": {
        "what_template": "Walk-forward testing de {strategy} en {total_bars} velas.",
        "extra_fields": {
            "config": {
                "train_bars": None,
                "test_bars": None,
                "step_bars": None,
                "total_bars": None,
                "windows_count": None,
            },
            "results": {
                "stability_rating": None,
                "windows_stable": None,
                "windows_total": None,
                "avg_test_pf": None,
                "avg_pf_degradation": None,
                "worst_window_pf": None,
            }
        }
    },
    "monte_carlo": {
        "what_template": "Monte Carlo simulation de {strategy} con {simulations} simulaciones.",
        "extra_fields": {
            "config": {
                "simulations": 1000,
                "confidence_levels": [0.95, 0.99],
            },
            "results": {
                "ruin_probability": None,
                "expected_drawdown_p95": None,
                "expected_drawdown_p99": None,
                "pf_distribution_median": None,
                "verdict": None,
            }
        }
    },
    "paper_trading_review": {
        "what_template": "Revisión de paper trading de {strategy} — semana del {date}.",
        "extra_fields": {
            "period": {
                "from": None,
                "to": None,
                "days": None,
            },
            "results": {
                "signals_generated": None,
                "signals_closed": None,
                "wins": None,
                "losses": None,
                "winrate": None,
                "net_pips": None,
                "matches_backtest_expectation": None,
                "notes": ""
            }
        }
    },
    "grid_search": {
        "what_template": "Grid search de {strategy} para optimización de parámetros.",
        "extra_fields": {
            "params_searched": {},
            "results": {
                "best_params": None,
                "best_pf": None,
                "combinations_tested": None,
                "overfitting_risk": None,
                "notes": ""
            }
        }
    },
}


def main():
    parser = argparse.ArgumentParser(description="Crea una Run Card vacía para completar manualmente")
    parser.add_argument("--type",       type=str, help="Tipo de run")
    parser.add_argument("--strategy",   type=str, required=False, help="ID de la estrategia/hipótesis")
    parser.add_argument("--date",       type=str, default=datetime.now().strftime("%Y-%m-%d"), help="Fecha")
    parser.add_argument("--list-types", action="store_true", help="Listar tipos disponibles")
    parser.add_argument("--dry-run",    action="store_true", help="Mostrar sin guardar")
    args = parser.parse_args()

    if args.list_types:
        print("\n  Tipos de Run Card disponibles:")
        for t in RUN_TYPES:
            print(f"    {t}")
        print()
        sys.exit(0)

    if not args.type:
        print("  ❌  Especifica --type. Usa --list-types para ver opciones.")
        sys.exit(1)

    run_type = args.type.lower()
    if run_type not in RUN_TYPES:
        print(f"  ❌  Tipo '{run_type}' no reconocido. Usa --list-types.")
        sys.exit(1)

    strategy  = args.strategy or "PENDIENTE"
    date_str  = args.date.replace("-", "")
    run_id    = f"{run_type}_{date_str}_{strategy}"
    template  = RUN_TYPES[run_type]

    card = {
        "run_id":    run_id,
        "type":      run_type,
        "date":      args.date,
        "what":      template["what_template"].format(
            strategy=strategy,
            date=args.date,
            total_bars="TODO",
            simulations=1000,
        ),
        "reproducibility": {
            "script":    "TODO",
            "strategy":  strategy,
            "bars":      None,
            "timeframe": "H1",
            "params":    {},
        },
        "hypothesis_id": strategy,
        **template["extra_fields"],
        "decisions_triggered": [],
        "notes": "",
        "generated_at": datetime.now().isoformat(),
        "status": "DRAFT",
    }

    # Localizar directorio de salida
    script_dir    = Path(__file__).parent
    project_root  = script_dir.parent.parent
    run_cards_dir = project_root / "research" / "run_cards"
    filename      = f"RC_{run_id[:40]}.json"
    output_path   = run_cards_dir / filename

    if args.dry_run:
        print(f"\n  DRY RUN — se crearía: {filename}")
        print(json.dumps(card, indent=2, ensure_ascii=False))
    else:
        run_cards_dir.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(card, f, indent=2, ensure_ascii=False)
        print(f"\n  ✅  Run Card creada: {output_path}")
        print(f"  Completa los campos 'TODO' y 'null' después de ejecutar el experimento.")

    print(f"\n  Run ID: {run_id}")


if __name__ == "__main__":
    main()
