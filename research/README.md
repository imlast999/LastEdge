# Research System — BOT-MT5

Sistema de validación y acumulación de evidencia para el proyecto.
Tres capas simples: hipótesis, experimentos, decisiones.

---

## Estructura

```
research/
├── hypotheses/          # Una hipótesis por estrategia
│   ├── eurusd_simple.json
│   ├── xauusd_momentum.json
│   ├── xauusd_simple.json
│   ├── eurusd_asian_breakout.json   ← FAILED
│   └── btc_trend_pullback_v1.json  ← TESTING (pendiente)
│
├── run_cards/           # Una tarjeta por experimento importante
│   └── RC_20260601_retest_multi_horizon.json
│
├── journal.md           # Decisiones y descubrimientos (no ejecuciones)
│
└── tools/               # Scripts de automatización
    ├── hypothesis_status.py    # Vista rápida del estado
    ├── run_card_generator.py   # Genera Run Cards desde session_summary.json
    ├── update_hypothesis.py    # Actualiza estado/evidencia de una hipótesis
    └── new_run_card.py         # Crea Run Card vacía para experimentos manuales
```

---

## Uso rápido

### Ver estado de todas las hipótesis
```bash
python research/tools/hypothesis_status.py
python research/tools/hypothesis_status.py --verbose
python research/tools/hypothesis_status.py --status RETESTING
```

### Generar Run Card después de un retest
```bash
# Automático — busca el último session_summary.json
python research/tools/run_card_generator.py

# Desde un session específico
python research/tools/run_card_generator.py --session backtest_results/session_XXXX/session_XXXX/session_summary.json
```

### Crear Run Card para walk-forward / monte carlo / paper trading
```bash
python research/tools/new_run_card.py --type walk_forward --strategy eurusd_simple
python research/tools/new_run_card.py --type monte_carlo --strategy xauusd_momentum
python research/tools/new_run_card.py --type paper_trading_review --strategy eurusd_simple
```

### Actualizar una hipótesis
```bash
# Cambiar estado tras walk-forward exitoso
python research/tools/update_hypothesis.py --id eurusd_simple --status PAPER_TRADING --reason "Walk-forward: 3/4 ventanas STABLE, PF mínimo 1.08"

# Añadir evidencia desde una Run Card
python research/tools/update_hypothesis.py --id eurusd_simple --add-evidence RC_walkforward_20260610_eurusd_simple.json

# Marcar test como completado
python research/tools/update_hypothesis.py --id eurusd_simple --pass-test walk_forward
python research/tools/update_hypothesis.py --id eurusd_simple --pass-test monte_carlo
```

---

## Ciclo de vida de una hipótesis

```
IDEA → TESTING → VALIDATING → RETESTING → PAPER_TRADING → LIVE
                                    ↓
                                  FAILED → ARCHIVED
```

| Estado         | Significado                                    |
|----------------|------------------------------------------------|
| IDEA           | Concepto sin datos                             |
| TESTING        | Grid search / primeros backtests               |
| VALIDATING     | Primeros retests multi-horizonte               |
| RETESTING      | Retests largos completados (10k/15k/20k)       |
| PAPER_TRADING  | En paper trading activo                        |
| LIVE           | En trading real                                |
| FAILED         | Descartada — PF < 1.0 o degradación excesiva  |
| ARCHIVED       | Pausada — podría revisarse en el futuro        |

---

## Qué registrar en el journal

**Sí:**
- Descartes (y por qué)
- Promociones a siguiente fase
- Cambios de criterio
- Descubrimientos inesperados
- Decisiones sobre el pipeline

**No:**
- "Hoy corrí un backtest y salió X"
- Métricas sin contexto
- Resultados rutinarios sin decisión asociada

---

## Estado actual del pipeline (2026-06-04)

| Estrategia            | Estado       | Próximo paso         |
|-----------------------|--------------|----------------------|
| eurusd_simple         | RETESTING    | walk-forward         |
| xauusd_simple         | RETESTING    | walk-forward         |
| xauusd_momentum       | RETESTING    | walk-forward (vigilar degradación 12%) |
| eurusd_asian_breakout | FAILED       | —                    |
| btc_trend_pullback_v1 | TESTING      | grid search          |
