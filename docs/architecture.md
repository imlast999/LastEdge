# Architecture — LastEdge

Resumen de alto nivel del ecosistema LastEdge. Este documento explica la composición del sistema, cómo se comunican los componentes y el flujo de datos entre ellos.

## Visión general

LastEdge es una plataforma modular compuesta por tres capas principales:

- Ingesta y ejecución (MT5 + LastEdge Engine)
- Investigación y validación (Backtest, Walk-Forward, Exit Research)
- Observabilidad y control (API, Dashboard web, Mobile App, Discord)

## Diagrama de alto nivel

```
[MT5] <---> [LastEdge Engine (Python)] <-> [bot_state.db SQLite]
                                   ^
                                   |
                               [API Server (Express)]
                                   |
                ---------------------------------------------
                |                     |                     |
            [Web Dashboard]       [Mobile App]           [Discord Bot]
                |                     |                     |
                ---------------------------------------------
                                   |
                            [Research Storage / Logs]
```

## Componentes principales

- LastEdge Engine (Python): motor de estrategia, backtesting, walk-forward y exit research. Es la fuente de verdad para señales y resultados.
- MT5 (MetaTrader 5): capa de ejecución y datos de mercado (candles, órdenes). Puede ser Demo o Live según configuración.
- API Server (Express): puente entre la base de datos `bot_state.db` y clientes externos (mobile, web). Lee/escribe de forma controlada.
- Web Dashboard: interfaz para análisis en escritorio y visualización avanzada.
- Mobile App: control y Research Lab portátil; consume la API para mostrar status, señales y ejecutar Research Runs.
- Discord Bot: canal de alertas y control rápido (slash commands).
- Research Storage: artefactos de investigación (resultados, curvas, MC, metadata) almacenados junto a la DB o en carpetas de salida.

## Comunicación entre módulos

- El Engine escribe en `bot_state.db` (SQLite). El API Server lee/actualiza esa DB.
- Clientes (Mobile/Web/Discord) consumen la API (REST). Sólo el Engine puede ejecutar órdenes en MT5.
- Research Runs se encolan (tabla `backtest_tasks`) y el Engine procesa la cola, escribiendo resultados de vuelta.

## Flujo de datos (resumen)

1. MT5 provee ticks/candles al Engine.
2. Engine genera señales y las persiste en `bot_state.db`.
3. API Server expone endpoints para status, señales, trades y Research Runs.
4. Mobile/Web consultan la API y muestran información.
5. Research Runs son encoladas por la UI (Web o Mobile) y procesadas por el Engine.

## Configuración y despliegue

- El sistema está pensado para correr en una máquina que tenga MT5 y el Engine para mínima latencia (demo/local). El API Server puede correr en la misma máquina o en otra que tenga acceso a la DB.
- Para despliegues remotos, se recomienda exponer el API Server detrás de un proxy seguro y usar autenticación con tokens.

## Futuras ampliaciones (breve)

- Migración a un almacenamiento de artefactos centralizado (S3/Postgres) para facilitar comparativas y multi-user.
- Soporte de colas de tareas distribuidas para Research Runs pesadas.
- Telemetría y tracing central para auditoría completa.

---

Este documento sirve como referencia rápida para colaboradores que necesiten comprender la organización general de LastEdge sin revisar el código.
