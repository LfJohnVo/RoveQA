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

## Implementation notes (Phase 09)
Refinamientos descubiertos al implementar, dentro del marco de la decisión:

- **Graphiti aporta el modelo de grafo y el driver; no la ingestión ni el search.** `add_episode`/`add_triplet` usan un LLM para descubrir entidades y decidir cuándo dos son la misma. Ese trabajo no existe aquí: los candidates llegan estructurados desde PostgreSQL y su identidad es un `dedup_key` determinista. Delegar identidad a un modelo pondría una conjetura a cargo de qué cuenta como el mismo hecho. Los nodos se escriben directo con UUID derivado del `candidate_id`, lo que además hace cada write idempotente y un rebuild reproducible.
- **El search es una query full-text propia, no el pipeline de Graphiti.** Ese pipeline existe para fusionar métodos de retrieval y reordenar con cross-encoder; nosotros queremos lo contrario — una lista de candidate ids con scope, ordenada después de forma determinista por reliability/freshness/compatibility en el Domain. Un rerank con modelo pondría una inferencia delante del retrieval de cada run y haría el camino warm más lento que el cold que debe superar.
- **No se construye el objeto `Graphiti`.** Su constructor crea un cliente LLM y un embedder OpenAI para cualquier slot vacío. No teniendo el objeto no hay slot que dejar vacío, así que un deployment local-first no puede adquirir una dependencia hosted por omisión. Verificado por test.
- **`group_id` es un digest opaco.** Graphiti restringe el charset y sanitizar no sería inyectivo; además FalkorDB indexa `group_id` como full text, así que un valor con `-`/`_` nunca coincide con la frase exacta. Los valores legibles viajan en cada nodo (`project_id`, `environment_id`).
- **Los índices los crea el adapter, no la librería.** `build_indices_and_constraints()` emite índices compuestos de relación que FalkorDB 4.20.3 rechaza *cerrando la conexión*, lo que aborta el resto del loop; la víctima era justo el índice full-text de `Entity` que usa el search.
- **El payload no se copia al grafo.** Ya está redactado, pero duplicar contenido derivado de página en un segundo store agrega una segunda fuente de fuga sin beneficio de retrieval: el search matchea sobre el summary.

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
