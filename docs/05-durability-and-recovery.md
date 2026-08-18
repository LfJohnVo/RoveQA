# Durability and Recovery

## Three durable layers
1. Temporal: progreso y lifecycle del workflow.
2. LangGraph + PostgreSQL: estado cognitivo/reanudable del agente.
3. PostgreSQL + filesystem: metadata durable y evidencia.

Redis queda fuera de esta lista intencionalmente. Graphiti/FalkorDB también: el grafo acelera/aprende, pero sus inputs de reconstrucción (`knowledge_candidates`, feedback y provenance) son PostgreSQL-durables.

## Safe checkpoint
Crear recovery point después de eventos semánticamente significativos: login verificado, navegación estable, submit verificado, goal completado, error descubierto, episode cerrado.

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
