# ADR 0009 — Run workflow shape, retry ownership and checkpoint reconciliation

Status: Accepted

## Context
El blueprint promete runs durables de horas (Temporal) con un state machine cognitivo (LangGraph), pero tres decisiones quedaban abiertas y habrían producido implementaciones incompatibles entre Phase 02 y Phase 05:
1. Qué capa posee cada retry (Temporal activity retry vs LangGraph Recover vs cliente).
2. La forma del workflow multi-hora: granularidad de activities, límites de event history, y cómo pause/cancel interrumpen una activity larga.
3. La relación entre la tabla `checkpoints` del dominio (`CheckpointReference`/`RecoveryPoint`) y el checkpointer PostgreSQL de LangGraph.

## Decision

### Retry ownership (single owner per loop)
- **Temporal** reintenta únicamente fallos de infraestructura (worker death, transient I/O). Un retry de activity siempre reanuda a través del último checkpoint de LangGraph y pasa por verify-before-retry; nunca re-ejecuta acciones semánticas a ciegas.
- **LangGraph Recover node** es el único dueño de los retries semánticos de acciones (elemento no encontrado, verificación fallida), bajo los budgets de la RunPolicy.
- **CLI/HTTP clients** poseen sólo transport retries sobre triggers idempotentes (`Idempotency-Key`).
- Rate-limit/backoff hacia model providers vive en el ModelGateway adapter, no en el graph ni en Temporal.

### Workflow shape
- `AgentRunWorkflow` (Temporal) orquesta el run y ejecuta **una activity por episodio** (`RunEpisodeActivity`) que corre/reanuda el graph de LangGraph con heartbeat.
- Pause/cancel llegan como signals al workflow; el workflow cancela la activity en curso; la activity detecta la cancelación vía heartbeat y el graph se detiene en el siguiente safe checkpoint. `PAUSING`/`CANCELLING` son los estados visibles durante esa ventana.
- Los events/status de pasos se persisten **desde dentro de las activities** (PostgreSQL), no como commands del workflow por paso, para acotar el event history de Temporal.
- Si el número de episodios puede crecer sin límite (exploración), el workflow aplica `continue-as-new` a un umbral configurable de episodios.

### Checkpoint reconciliation
- El checkpointer PostgreSQL de LangGraph es detalle de infraestructura: persiste cada superstep en su propio schema.
- La tabla `checkpoints` del dominio almacena `RecoveryPoint`s: referencia al checkpoint id de LangGraph (`CheckpointReference`) + browser recovery data (storage state ref, URL, page fingerprint, last verified action).
- Resume = cargar el último checkpoint LangGraph → verificar preconditions contra el `RecoveryPoint` más reciente → verify-before-retry para cualquier action dentro de la uncertainty window.
- El gate de Phase 05 "Run retoma desde último safe checkpoint" se interpreta así: se reanuda desde el último checkpoint LangGraph, validado contra el último `RecoveryPoint`; si la validación falla, se retrocede al `RecoveryPoint` y se re-deriva el estado.

## Consequences
- Phase 02 implementa `AgentRunWorkflow` + signals + activities de persistencia con esta forma; Phase 05 implementa `RunEpisodeActivity` + checkpointer + Recover node sin renegociar la costura.
- Los durability tests deben matar el worker dentro y fuera de la uncertainty window y demostrar que ninguna capa duplica el retry de otra.
- Cualquier cambio a esta forma (p.ej. activity por acción) requiere ADR superseding.
