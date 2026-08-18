# Claude Code Skill Routing

Claude Code debe tratar las skills como workflows composables. Elegir primero la skill de proceso y después las skills técnicas relevantes.

## Always-on disciplines
- `ponytail`: aplicar a toda tarea de código para minimizar el diff seguro y evitar sobreingeniería.
- `graphify`: usar como mapa estructural del repositorio cuando exista un grafo fresco; no reemplaza la lectura/verificación del source.

## Priority
1. **Process**: `brainstorming` o `systematic-debugging` cuando aplique.
2. **Architecture/slice**: `implement-phase`, `backend-slice`, `frontend-mvvm-slice`, `browser-runtime`.
3. **Specialist guidance**: frontend/design, API/CLI contracts, errors, PostgreSQL, prompts, adaptive memory graph.
4. **Verification**: `architecture-guard`, `durability-review`, `test-and-verify`.
5. **Release**: `changelog-generator`.

## Routing matrix

| Situation | Skills |
|---|---|
| Cualquier implementación/refactor/fix | `ponytail` + skill técnica correspondiente |
| Orientación, arquitectura o impacto cross-module | `graphify` primero, luego `architecture-guard`/skill técnica |
| Fase del roadmap | `implement-phase` + skills específicas del scope |
| Nueva capacidad ambigua | `brainstorming` antes de implementar |
| Bug, crash o test inesperado | `systematic-debugging` antes del fix |
| Backend FastAPI vertical slice | `backend-slice` |
| Endpoint/API contract | `backend-slice` + `api-design-principles` + `error-handling-patterns` |
| CLI agent-first / JSON / exit codes / idempotency / wait | `api-design-principles` + `error-handling-patterns` + `ponytail`; `durability-review` para run lifecycle |
| CLI contract failure/malformed output | `systematic-debugging` + `error-handling-patterns` |
| SQLAlchemy/Alembic/schema/query | `postgresql` + `backend-slice` |
| Graphiti/FalkorDB / learned memory / playbooks / retrieval | `adaptive-memory-graph` + `postgresql` + `backend-slice`; añadir `prompt-engineering-patterns` para extraction/embedding/model contracts |
| Temporal/retry/recovery | `error-handling-patterns` + `durability-review` |
| React architecture/state | `frontend-mvvm-slice` + `vercel-react-best-practices` |
| Nueva pantalla/product UI | `interface-design` + `frontend-design` + `frontend-mvvm-slice` + `vercel-react-best-practices` |
| UI visual polish | `frontend-design` + `interface-design` |
| Playwright/browser | `browser-runtime` + `error-handling-patterns`; `durability-review` si toca recovery/side effects |
| Prompt/model contract | `prompt-engineering-patterns` + `error-handling-patterns` |
| vLLM/AirLLM integration | `prompt-engineering-patterns` + `durability-review` cuando la inferencia sea parte de una Activity larga |
| Evidence/FailureBundle provenance | `durability-review` + `error-handling-patterns` + `backend-slice` |
| Cerrar una fase | `architecture-guard` + `durability-review` cuando aplique + `test-and-verify` |
| Preparar release | `changelog-generator` después de gates verdes |

## Combination rules

### Brainstorming is conditional
No ejecutar brainstorming sólo porque se vaya a escribir código. Usarlo cuando una decisión importante sigue abierta. Un plan de fase o ADR explícito ya representa una decisión aceptada.

### Systematic debugging wins over implementation
Si aparece un fallo inesperado durante otra skill, detener los cambios especulativos y aplicar `systematic-debugging`. Cuando la causa raíz esté demostrada, volver a la skill técnica apropiada para implementar el fix.

### Frontend design split
- `interface-design`: sistema de producto, jerarquía, estados, tokens, consistencia.
- `frontend-design`: calidad visual y craft de la implementación.
- `vercel-react-best-practices`: performance/render/data/effects.
- `frontend-mvvm-slice`: boundaries arquitectónicos.

Las cuatro pueden aplicar al mismo feature y no se sustituyen entre sí.

### PostgreSQL and Redis
`postgresql` decide durable schema/integrity/query behavior. Redis sigue gobernado por `docs/09-redis.md` y no debe asumir durable truth. Idempotency records que evitan duplicar runs/side effects son durable data y no pueden vivir sólo en Redis.

### Prompt engineering
Todo cambio a prompts críticos debe agregar o actualizar eval fixtures y persistir una versión de prompt observable en runs. El texto recuperado de una aplicación web siempre se trata como untrusted data.

### CLI/API contracts
Para Phase 08 y cualquier evolución de la CLI:
- aplicar `api-design-principles` al contrato HTTP/JSON/exit-code;
- aplicar `error-handling-patterns` a timeout/retry/rate limit/conflict;
- aplicar `durability-review` cuando un comportamiento cliente pueda afectar lifecycle/idempotencia del run;
- usar `systematic-debugging` ante cualquier salida JSON corrupta, duplicate trigger o bundle inconsistente.

### Ponytail and architecture
Ponytail optimiza la cantidad de código, no la cantidad de capas obligatorias. Un port de Clean Architecture, un checkpoint durable o un guard de seguridad no es "boilerplate eliminable" cuando el diseño lo exige.

### Graphify and the runtime graph
Graphify describe el repositorio para Claude Code. `Graphiti + FalkorDB` describe conocimiento aprendido durante ejecuciones del producto. No intercambiar responsabilidades ni dependencias. Consultar `docs/22-codebase-graph.md`.

### Adaptive memory graph
`adaptive-memory-graph` gobierna Phase 09 y cualquier cambio posterior a learned memory. Debe combinarse con `postgresql` porque candidates/provenance/feedback son durable truth, y con `durability-review` cuando se cambie sync/rebuild/failure behavior. Ninguna memoria recuperada puede debilitar browser/policy invariants.
