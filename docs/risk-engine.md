# Risk Engine

Descripción del Risk Engine: componentes, responsabilidades y cómo protege el portfolio.

## Arquitectura (componentes)

- `PositionSizer`: calcula el lote en base a riesgo por trade, sl, balance y reglas de símbolo.
- `MarginChecker`: valida que la operación propuesta cumpla límites de margin y free margin.
- `PortfolioRisk`: calcula exposición agregada y riesgo por símbolo y por cuenta.
- `RiskEngine`: orquesta la lógica global: aplica reglas, circuit breakers y políticas de reducción de exposición.

## Flujo completo

1. Una señal llega desde el Strategy Engine.
2. `PositionSizer` estima el lote basado en SL y riesgo configurado.
3. `MarginChecker` valida si la cuenta puede soportar la posición.
4. `PortfolioRisk` evalúa impacto en exposición total y posibles colisiones con otras posiciones.
5. `RiskEngine` aprueba/rechaza o sugiere adaptación (partial close, menor lote, reject).

## Cálculo de lote

El lote se calcula usando: balance, riesgo máximo por trade (p. ej. 0.5% del balance), SL (en pips) y tamaño de pip por símbolo. Fórmula general:

```
risk_amount = balance * risk_percent
lot = risk_amount / (SL_in_pips * pip_value_per_lot)
```

El `PositionSizer` incluye protecciones: lot mínimo/máximo, rounding por micro/mini/standard lots, y límites por símbolo.

## Soporte por mercados (Forex, Oro, Crypto)

- Pip/value calculations adaptadas por símbolo.
- Crypto y Commodities manejan tamaños y observaciones específicas (p. ej. comisiones por contrato), pero la lógica de riesgo es la misma: riesgo monetario objetivo por trade.

## Protecciones de portfolio

- Límite de exposición por símbolo
- Límite de pérdida diaria (circuit breaker)
- Reducción de posición automática ante drawdown
- Reglas de correlación para evitar overexposure en activos altamente correlacionados

## Integración con App y TradingEngine

- La app muestra decisiones del `RiskEngine` (por ejemplo: rechazado por margin, lote reducido) en la UI.
- El `TradingEngine` consulta el `RiskEngine` antes de enviar órdenes a MT5; sólo el `TradingEngine` ejecuta (actor único de ejecución).

## Configuraciones y extensibilidad

- Reglas configurables: `max_risk_per_trade`, `daily_loss_limit`, `exposure_limit_per_symbol`, `min_free_margin`.
- Añadir nuevas reglas: crear un nuevo módulo que implemente la interfaz de validación y registrarlo en `RiskEngine`.

---

Este documento se centra en el motor de riesgo; no describe estrategias ni policy tuning específico.
