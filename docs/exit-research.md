# Exit Research

Documento focalizado en Exit Research: propósito, métricas clave, artefactos y cómo interpretar resultados.

## Objetivo

Evaluar variantes de salida (exit) de una estrategia para identificar la configuración que maximiza captura de profits y estabilidad bajo diferentes condiciones de mercado.

## Qué compara

- Variantes de exit (p. ej. fixed TP/SL, partial close, trailing stop, time-based exits)
- Comportamiento en ventanas walk-forward
- Robustez mediante Monte Carlo

## Por qué existen variantes

Porque la lógica de salida afecta de forma determinante la relación riesgo/recompensa, drawdown y la capacidad de una estrategia de sobrevivir en producción.

## Métricas analizadas (lista)

- Profit Factor (PF)
- Win Rate (WR)
- Max Drawdown (DD)
- Expectancy
- MAE (Maximum Adverse Excursion)
- MFE (Maximum Favorable Excursion)
- Profit Captured (%)
- Monte Carlo outcomes (p5/p50/p95, ruin probability)
- Stability Score (agregado de robustez)
- Trade Timeline y Heatmap (visibilidad de concentración temporal)

## Artefactos visuales

- Equity Curve
- Trade Timeline (operación por operación)
- Heatmap de densidad de señales
- Monte Carlo distribution plots
- Variant Comparison table

## Interpretación

- PF alto + DD controlado + baja probabilidad de ruina → candidato a promoción.
- MAE/MFE analizan calidad de entradas y eficiencia de salida; MAE alto sugiere entradas poco óptimas.
- Profit Captured indica porcentaje de beneficio efectivo capturado por la variante de salida.

## Promoción de una variante

Promocionar significa seleccionar una variante como default para demo/live tests. Antes de promocionar, la variante debe pasar las reglas del protocolo (WF, MC, Stability Score) y someterse a validación en Demo MT5.

## Integración con LastEdge Protocol

Exit Research es la fase final del protocolo. Sus resultados son artefactos del Research Run y condicionan la recomendación de promoción a producción.
