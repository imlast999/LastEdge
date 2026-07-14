# Strategies — creación y registro

Guía práctica para crear, registrar y desplegar estrategias en LastEdge. Este documento trata únicamente la estructura y buenas prácticas para estrategias.

## Estructura mínima

Una estrategia debe exponer al menos:

- `metadata`: { `id`, `name`, `symbol`, `required_history`, `required_timeframe` }
- `generate_signals(candles, state)`: función que devuelve un array de señales con `{symbol, side, entry, tp, sl, confidence}`

Ejemplo mínimo de metadata:

```json
{
  "id": "eurusd_partial",
  "name": "EURUSD Partial Close",
  "symbol": "EURUSD",
  "required_history": 10000,
  "required_timeframe": "H1"
}
```

## Metadata y required_history

- `required_history`: número mínimo de velas históricas para backtest reproducible.
- `required_timeframe`: TF en el que la estrategia opera.

## Detección de setups y gestión de entradas

- Las reglas de entrada deben ser deterministas y parametrizables.
- Registrar timestamp y condiciones que originaron la señal para auditoría.

## Registro y visibilidad

- Registrar la estrategia en el `Strategy Registry` (simple archivo o endpoint) incluyendo metadata y versión.
- Para ser visible en la app/web, actualizar el `constants/backtest.ts` o el endpoint `routes/bot.ts#/strategies`.

## Añadir nuevo símbolo

- Crear metadata con `symbol` y ajustar pip/value en la tabla de símbolos.
- Verificar `PositionSizer` y `MarginChecker` soporten el nuevo símbolo.

## Buenas prácticas

- Mantener funciones puras y añadir tests unitarios para `generate_signals`.
- Versionar metadata y conservar compatibilidad.
- Documentar assumptions (liquidity, spread, hours) en la metadata.

## Errores comunes

- No definir `required_history` suficientemente grande → backtest no reproducible.
- Usar operaciones no deterministas (dependencia de sistema o hora local sin seed).
- No registrar la estrategia en el Registry → no visible para la UI.
