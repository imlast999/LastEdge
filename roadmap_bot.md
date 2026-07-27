# Roadmap — Plataforma de Comunicación (Discord → Multiplataforma)

## Objetivo

Convertir la interfaz del bot en una capa limpia, mantenible y reutilizable, permitiendo que LastEdge pueda utilizar Discord, Telegram (y futuras plataformas) sin duplicar lógica.

---

# P2.1 — Auditoría y Limpieza del Bot de Discord (Crítico)

## Objetivo

Eliminar deuda técnica y asegurar que el bot de Discord refleja el estado real del proyecto.

### Tareas

- [ ] Inventariar todos los comandos existentes.
- [ ] Identificar comandos obsoletos.
- [ ] Detectar comandos rotos.
- [ ] Eliminar referencias a funcionalidades eliminadas.
- [ ] Actualizar mensajes y embeds.
- [ ] Revisar permisos.
- [ ] Revisar botones e interacciones.
- [ ] Revisar menús.
- [ ] Revisar autocompletado.
- [ ] Eliminar código muerto.

### Resultado esperado

Bot de Discord completamente funcional y alineado con LastEdge actual.

---

# P2.2 — Separación de la Lógica (Muy Alta)

## Objetivo

Hacer que Discord deje de contener lógica de negocio.

### Tareas

- [ ] Identificar lógica mezclada con Discord.
- [ ] Extraer esa lógica a Services/Core.
- [ ] Dejar los comandos como simples adaptadores.
- [ ] Eliminar duplicaciones.

Ejemplo

Discord

↓

StatusService

↓

RiskEngine

↓

Journal

---

# P2.3 — Revisión de UX del Bot (Alta)

## Objetivo

Que utilizar el bot sea cómodo.

### Revisar

- nombres de comandos
- categorías
- respuestas
- embeds
- botones
- tiempos de respuesta
- consistencia

Preguntas clave

- ¿Encuentro rápido lo que busco?
- ¿Hay comandos duplicados?
- ¿Algún comando hace demasiadas cosas?

---

# P2.4 — Preparación Multiplataforma (Alta)

## Objetivo

Dejar preparada la arquitectura para múltiples interfaces.

Arquitectura objetivo

Core

├── Discord Adapter

├── Telegram Adapter

└── (Futuro Web / CLI)

### Tareas

- [ ] Definir interfaz común.
- [ ] Identificar servicios reutilizables.
- [ ] Evitar dependencias de Discord.

---

# P2.5 — Desarrollo del Bot de Telegram (Media)

## Objetivo

Crear una interfaz ligera para uso diario.

### Primera versión

- [ ] /status
- [ ] /positions
- [ ] /balance
- [ ] /risk
- [ ] /signals
- [ ] /journal
- [ ] /research
- [ ] Alertas automáticas

No añadir todavía:

- comparadores complejos
- dashboards
- menús enormes

---

# P2.6 — Sincronización de Plataformas (Media)

## Objetivo

Garantizar que Discord y Telegram muestran exactamente la misma información.

### Verificar

- mismas métricas
- mismos cálculos
- mismos permisos
- mismo comportamiento

---

# P2.7 — Decisión Estratégica (Baja)

Tras varias semanas usando ambos bots responder:

- ¿Uso más Discord?
- ¿Uso más Telegram?
- ¿Mantengo ambos?
- ¿Discord queda como administración?
- ¿Telegram pasa a ser la interfaz principal?

Solo entonces decidir el futuro de cada plataforma.

---

## Filosofía de esta fase

- No duplicar lógica.
- Las plataformas solo muestran información.
- Toda la inteligencia permanece en el Core.
- Resolver necesidades reales antes de añadir funcionalidades nuevas.
- Telegram se incorpora como una interfaz adicional, no como un reemplazo inmediato de Discord.