# Phase 09 — Adaptive QA Learning Graph (Graphiti + FalkorDB)

## Objective
Convertir experiencia verificada de runs anteriores en memoria temporal/reutilizable que reduzca exploración y model calls sin degradar correctness, seguridad ni durabilidad.

## Required reading
- `docs/10-knowledge-graph.md`
- `docs/26-adaptive-learning-graph.md`
- `docs/adr/0008-adaptive-learning-graph.md`
- `contracts/knowledge-experience.schema.json`
- `contracts/memory-context.schema.json`

## Required skills
- `adaptive-memory-graph`
- `backend-slice`
- `postgresql`
- `prompt-engineering-patterns`
- `error-handling-patterns`
- `durability-review`

## Tasks
1. Crear bounded context `Knowledge` con ports; no importar Graphiti/FalkorDB fuera de Infrastructure.
2. Añadir tablas durables incrementales: `knowledge_candidates`, `memory_feedback`, `graph_sync_state` y los índices/constraints necesarios.
3. Implementar `KnowledgeExperienceCandidate` y `MemoryContext` con runtime/schema validation y provenance obligatoria.
4. Implementar `GraphMemoryAdapter` con Graphiti + FalkorDB y graph schema/version metadata.
5. Inyectar `llm_client`/`embedder` en Graphiti; prohibir dependencia accidental del default OpenAI. Añadir `EmbeddingGateway` y adapter local a vLLM `/v1/embeddings` con un pooling model validado.
6. Crear `ExperienceConsolidator`: episodio cerrado -> redaction -> candidates -> quality/promotion gates -> idempotent Graphiti ingestion.
7. Hacer que fallo del graph write deje `pending_sync`; el run no falla. Implementar retry/replay posterior desde durable candidates.
8. Implementar `MemoryRetriever` antes de planning: hard scope filters -> hybrid retrieval -> deterministic ranking -> bounded `MemoryContext`.
9. Implementar version/fingerprint compatibility y `revalidate` behavior; side-effect playbooks siguen verify-before-retry.
10. Implementar `MemoryFeedbackRecorder` para success/failure/contradiction/stale/unsafe después de outcomes verificados; actualizar reliability e invalidation.
11. Añadir negative learning para failure signatures, dead transitions y playbooks invalidados sin guardar raw noise.
12. Añadir GraphRebuilder/validator y API/CLI admin: `memory status`, `memory rebuild`, `memory validate` (la CLI sigue siendo thin-client).
13. Exponer metrics/traces: retrieval hit/use, accepted/revalidated/stale, graph sync lag, playbook success y savings cold-vs-warm.
14. Crear benchmark reproducible usando `templates/MEMORY_EVAL_TEMPLATE.md` para al menos login+navegación+un flujo CRUD seguro.
15. Preparar query/read model para el knowledge browser que se implementará en Phase 10, sin construir UI anticipadamente.

## Gates
- Un cold run verificado produce durable candidates con provenance correcta y Graphiti materializa sólo knowledge reusable.
- Un segundo run sobre fingerprint compatible reutiliza memoria y reduce de forma medible planner model calls o browser exploration actions frente al cold baseline, sin cambiar un verdict correcto por uno incorrecto/inconclusive.
- El benchmark objetivo inicial demuestra >=20% de reducción en al menos una métrica primaria (planner model calls o exploratory browser actions) en un flujo estable; si no, la fase documenta el bottleneck y no marca la optimización como validada.
- Fingerprint/version mismatch marca memoria como `revalidate`/incompatible y evita replay ciego.
- Un playbook usado y contradicho por evidencia verificada pierde reliability/se invalida; el run siguiente no lo trata como trusted.
- Graphiti/FalkorDB caído durante un run deja candidates pendientes y el run conserva correctness/lifecycle.
- Borrar FalkorDB y ejecutar rebuild reconstruye una memoria funcional desde PostgreSQL sin reejecutar tests.
- Cross-project/role leakage test devuelve cero memoria ajena.
- Secret/prompt-injection fixture no termina promovida como policy/fact operable.
- LLM/model-derived hypothesis permanece etiquetada y no reemplaza deterministic observation.
- MemoryContext respeta límites y cada item incluye provenance/reliability/compatibility/selection_reason.
