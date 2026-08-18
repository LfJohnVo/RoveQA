# ADR 0008 — Adaptive QA Learning Graph with Graphiti + FalkorDB

## Status
Accepted.

## Context
RoveQA repite recorridos sobre aplicaciones que cambian con el tiempo. Guardar sólo summaries planos obliga al planner a redescubrir navegación, estados, fallos y relaciones en cada run. Al mismo tiempo, una memoria aprendida puede quedar obsoleta, contaminarse con contenido no confiable o convertirse accidentalmente en una segunda fuente de verdad.

## Decision
Usar **Graphiti + FalkorDB** como proyección temporal de conocimiento reusable del runtime.

- PostgreSQL + filesystem siguen siendo la verdad durable de runs, evidencia, knowledge candidates, provenance y feedback.
- FalkorDB contiene una proyección reconstruible optimizada para traversal/hybrid retrieval.
- Graphiti aporta ingestión/consolidación temporal y acceso al graph backend.
- El adapter de Graphiti debe recibir `llm_client`/`embedder` explícitos; el runtime local-first no dependerá del provider OpenAI por defecto.
- Para embeddings se preferirá un `EmbeddingGateway` local, inicialmente una instancia vLLM pooling/OpenAI-compatible separada cuando el modelo seleccionado esté validado.
- Memory retrieval ocurre antes del planning y después de hard scope filters.
- Memory feedback se registra únicamente a partir de outcomes verificados.
- Fingerprint/version mismatch, contradiction o policy mismatch obliga a revalidar o descartar memoria.
- Fallo/pérdida del graph store degrada rendimiento/aprendizaje, no la durabilidad ni correctness del run.

## Consequences
### Positive
- Reutilización de rutas y playbooks entre runs.
- Menos model calls/acciones de exploración en flujos conocidos.
- Relaciones temporales explícitas entre versiones, páginas, acciones, criterios, fallos y fixes.
- Knowledge browser útil para humanos y agentes.
- Rebuild posible desde datos durables.

### Costs / risks
- Ingestión y retrieval agregan complejidad y consumo de inferencia/embeddings.
- Memory poisoning/staleness requieren controles explícitos.
- Graphiti funciona mejor con structured outputs; el modelo local elegido debe evaluarse para ingestión.
- Se necesita benchmark cold-vs-warm para demostrar que la memoria aporta valor real.

## Rejected alternatives
- **Sólo PostgreSQL JSON/vector:** suficiente para facts planos, peor para paths/relationships/versioned transitions que son centrales al producto.
- **Neo4j además de FalkorDB:** duplica infraestructura sin una necesidad v1.
- **Kuzu:** no se adopta para un proyecto nuevo; mantener un único graph backend.
- **Mem0/Cognee además de Graphiti:** posible evaluación futura, pero añadir dos frameworks de memoria ahora aumenta complejidad sin un gate que lo justifique.
- **Fine-tuning automático:** fuera de v1; “aprendizaje” significa memoria/estrategias con evidence, no modificar pesos del modelo.
