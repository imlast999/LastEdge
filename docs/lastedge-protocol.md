# LastEdge Protocol

Este documento describe el LastEdge Protocol: el proceso estandarizado de investigación que el proyecto aplica a cada estrategia antes de su promoción a producción.

## Qué es

El LastEdge Protocol es un pipeline reproducible y auditable que transforma una idea de estrategia en una investigación formal (Research Run). El objetivo es producir evidencia cuantificable sobre la robustez y la estabilidad de la estrategia.

## Por qué existe

- Evitar decisiones basadas en backtests aislados y no reproducibles.
- Unificar pasos de validación para facilitar auditoría y comparaciones.

## Qué problema resuelve

Reduce riesgo de sobreajuste y decisiones ad-hoc al exigir un pipeline mínimo y artefactos reproducibles antes de promover una estrategia.

## Fases del protocolo

1. Backtest — reproducción histórica con costes reales.
2. Walk Forward — validación por ventanas para medir generalización.
3. Monte Carlo — simulaciones de outcomes para estimar ruina y drawdown percentiles.
4. Exit Research — comparación de variantes de salida (MAE/MFE/Profit Captured).

Estas fases pueden ejecutarse de forma encadenada (pipeline completo) o de forma parcial según necesidad.

## Ejecución parcial

- Quick Validation: ejecutar sólo Backtest en dataset reducido.
- Custom Investigation: seleccionar fases concretas (p. ej. sólo Monte Carlo y Exit Research).

## Research Run

Un Research Run es la unidad del protocolo. Contiene:
- Configuración (parámetros exactos y seed si aplica)
- Artefactos (curvas, tablas, MC dumps)
- Métricas (PF, WR, DD percentiles, Stability Score)
- Metadatos (fechas, commit del código, environment)

Los Runs son reproducibles: se debe poder re-ejecutar un Run con la misma configuración y obtener resultados comparables.

## Qué información produce

- Métricas agregadas (winrate, profit factor, expectancy)
- Curva de equity
- Resultados de Monte Carlo (p5, p50, p95) y probabilidad de ruina
- Heatmaps, trade timeline y comparativas entre variantes
- Conclusiones y anotaciones del investigador

## Interpretación y decisiones

- Aprobar un protocolo: cuando las métricas cumplen criterios de estabilidad y robustez (por ejemplo, Stability Score mínimo, MC Ruin bajo, WF clasificación positiva).
- Rechazar una estrategia: si presenta evidencia de overfitting, PF inestable o riesgo inaceptable.

Las reglas exactas de aprobación pueden variar por proyecto; LastEdge define criterios en su sistema de validación (ver `README` principal y Exit Research docs).
