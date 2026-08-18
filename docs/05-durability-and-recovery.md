# Durability and Recovery

## Three durable layers
1. Temporal: progreso y lifecycle del workflow.
2. LangGraph + PostgreSQL: estado cognitivo/reanudable del agente.
3. PostgreSQL + filesystem: metadata durable y evidencia.

Redis queda fuera de esta lista intencionalmente. Graphiti/FalkorDB también: el grafo acelera/aprende, pero sus inputs de reconstrucción (`knowledge_candidates`, feedback y provenance) son PostgreSQL-durables.

## Safe checkpoint
Crear recovery point después de eventos semánticamente significativos: login verificado, navegación estable, submit verificado, goal completado, error descubierto, episode cerrado.

### Checkpoint model reconciliation
El checkpointer de LangGraph (PostgreSQL) persiste el estado del graph en cada superstep y es un detalle de infraestructura. La tabla `checkpoints` del dominio almacena filas `RecoveryPoint` que referencian un checkpoint id de LangGraph (`CheckpointReference`) más datos de recovery del browser (storage state ref, URL, page fingerprint, last verified action). Resume = cargar el último checkpoint LangGraph, verificar preconditions contra el `RecoveryPoint` más reciente y aplicar verify-before-retry a cualquier action dentro de la uncertainty window. Ver ADR 0009.

## Retry ownership
Exactamente una capa posee cada retry loop (ver ADR 0009):
- **Temporal** reintenta sólo fallos de infraestructura (worker muerto, I/O transitorio) y siempre reanuda a través del checkpoint LangGraph + verify-before-retry; nunca re-ejecuta acciones semánticas a ciegas.
- **LangGraph Recover node** posee los retries semánticos de acciones (bajo budgets de RunPolicy).
- **CLI/HTTP clients** poseen sólo transport retries (timeouts, connection reset) sobre triggers idempotentes.
Un fallo manejado por una capa no debe generar un segundo retry en otra.

## Browser recovery
No serializar Chromium. Persistir:
- storage state/autenticación permitida
- current/last stable URL
- relevant tab metadata
- page fingerprint
- last verified action
- viewport/permissions necesarios
- recovery instructions

Recovery: iniciar Chromium nuevo -> restaurar storage state -> navegar a recovery URL -> verificar fingerprint/preconditions -> reanudar LangGraph.

## Side-effect uncertainty window
Caso obligatorio a diseñar: el target procesó `Create User`, pero el worker murió antes del ack.

Nunca repetir ciegamente. `verify-before-retry` busca el recurso por una idempotency marker (por ejemplo email generado con run id). Si existe y cumple postconditions, marcar action como verificada; si no, reintentar según policy.

## Context compaction
No enviar miles de pasos al LLM. Mantener active context pequeño y convertir bloques anteriores en EpisodeSummary durable, knowledge candidates y artifact references.

## Knowledge graph outage/rebuild
Un fallo de Graphiti/FalkorDB no puede fallar el primary run. Persistir candidate + `pending_sync`, continuar y reintentar consolidación después. Soportar rebuild idempotente desde PostgreSQL hacia un graph store vacío.
