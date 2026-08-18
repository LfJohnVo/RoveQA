---
name: adaptive-memory-graph
description: Diseña, implementa y revisa el grafo de aprendizaje runtime de RoveQA con Graphiti + FalkorDB. Usar cuando el cambio toque memoria aprendida, knowledge candidates, graph schema, retrieval/ranking, playbooks, feedback de ejecuciones, invalidación por fingerprint/versión, rebuild del grafo, embeddings o protección contra memory poisoning.
---
# Adaptive Memory Graph

1. Leer `docs/10-knowledge-graph.md`, `docs/26-adaptive-learning-graph.md`, ADR `0008` y la fase actual antes de editar.
2. Mantener PostgreSQL como durable truth de candidatos/provenance/feedback. FalkorDB es una proyección reconstruible; un fallo del grafo nunca puede corromper ni bloquear el lifecycle principal de un run.
3. Escribir al grafo sólo conocimiento reusable. No persistir cada token, DOM completo o acción trivial: raw history/evidence vive en PostgreSQL/filesystem.
4. Promover memoria sólo desde outcomes verificados. Separar siempre `observed=true` de hipótesis `model_derived=true`; una hipótesis no se convierte en hecho por repetición del modelo.
5. Antes de retrieval aplicar hard scope filters: project, environment, role/policy, target origin, app/version/fingerprint compatibility. Después rankear por reliability, freshness, fingerprint similarity y relevance.
6. Todo `MemoryContext` devuelto al planner debe incluir provenance (`source_run_id`, `evidence_set_id` o candidate id), confidence/reliability y razón de selección.
7. Un fingerprint/version mismatch obliga a revalidation. Ningún playbook, incluso trusted, puede saltarse RunPolicy, side-effect verification o allowlists.
8. Registrar feedback cuando memoria usada produce un outcome verificado: success, failure, contradiction, stale o unsafe. Actualizar reliability determinísticamente y permitir invalidación.
9. Hacer ingestion/consolidation idempotente por `candidate_id`/`episode_id`. Si Graphiti/FalkorDB no está disponible, dejar el candidate durable pendiente y continuar el run.
10. No acoplar Domain a Graphiti/FalkorDB. Definir ports (`KnowledgeRepository`, `MemoryRetriever`, `ExperienceConsolidator` o equivalentes) y adapters en Infrastructure.
11. Mantener local-first: inyectar LLM/embedder en Graphiti. No depender del default OpenAI. Preferir ModelRouter + un `EmbeddingGateway` servido por vLLM pooling/OpenAI-compatible embeddings cuando esté validado.
12. Añadir tests de cold-vs-warm, stale knowledge, contradiction, graph outage/rebuild, tenant leakage, secret redaction y memory poisoning.
13. Medir valor: hit rate, accepted-memory rate, revalidation rate, model calls/actions ahorradas y warm-run success quality. Si una optimización no mejora el benchmark o baja la calidad, no promoverla.
