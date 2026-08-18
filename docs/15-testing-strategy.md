# Testing Strategy

## Layers
1. Domain unit tests: invariants/state transitions.
2. Application unit tests with fake ports.
3. Adapter integration tests: PostgreSQL, Redis, filesystem, vLLM HTTP contract stubs, Playwright test target.
4. Temporal workflow tests/time skipping where applicable.
5. API/CLI contract tests against versioned schemas.
6. CLI subprocess tests: stdout/stderr/exit codes/signals/timeouts.
7. System tests against a deterministic local demo web app.
8. Chaos/recovery tests.

## Mandatory recovery scenarios
- Worker dies during read-only action.
- Worker dies after target side effect but before acknowledgement.
- Chromium crashes.
- vLLM unavailable and recovers.
- Redis restart/flush.
- PostgreSQL temporary outage.
- Temporal worker restart.
- WebSocket client disconnect/reconnect.
- CLI process dies or receives Ctrl-C while waiting: server run continues.
- Client loses the response to `POST /runs` and retries with the same idempotency key: no duplicate logical run/target side effect.

## CLI/API contract scenarios
- `--output json` produce exactamente un valor JSON tanto en success como error.
- stderr puede contener progress/debug sin contaminar stdout.
- Runtime response validation rechaza una respuesta 2xx malformed en vez de producir fake success.
- Exit code coincide con error/verdict documentado.
- Wait timeout devuelve run identity/last status y no cancela.
- `plan scaffold` y `plan lint` funcionan offline.
- Config precedence está testeada.
- File-input flags tienen existence/type/size/secret guards.
- Histories/steps/responses grandes están bounded/paginated/streamed.

## FailureBundle integrity scenarios
Intentar construir bundles artificialmente mezclados y exigir rechazo:
- screenshot de run A + DOM de run B;
- misma run pero distinto `evidence_set_id` cuando el bundle exige uno;
- plan version diferente del result;
- artifact hash/tamaño incorrecto;
- fallo durante descarga/escritura produce `.partial` y nunca un `manifest.json` completo.

## Agent-plan quality scenarios
Mantener fixtures donde el producto funciona pero el plan es malo:
- assertion demasiado ambigua;
- OR/branching excesivo que agota budget;
- muchas acciones sin progreso;
- assertion sólo comprueba presence aunque el recurso esté roto;
- layout-sensitive criterion verificado sólo por texto.

El sistema debe poder clasificar estos casos como `plan`, `agent_budget` o `inconclusive` sin reportarlos automáticamente como product defect.

## Browser fixture application
Crear una pequeña `test-target-app` local con auth, CRUD, forms, validation errors, delayed responses, dynamic DOM, controlled 500s y optional canvas widget. Agregar páginas/fixtures de prompt injection, broken image, modal inesperado y side effect verificable. Es la base reproducible para validar el agent runtime.

## Definition of a regression
Todo bug reproducible del runtime/product/CLI contract debe crear test que falle antes del fix y pase después.


## Adaptive memory tests
- candidate creation/promotion con provenance;
- cold-vs-warm benchmark reproducible;
- exact fingerprint reuse y mismatch -> revalidation;
- negative feedback/contradiction -> reliability drop/invalidation;
- Graphiti/FalkorDB outage durante run -> pending sync + run unaffected;
- empty graph rebuild from PostgreSQL;
- cross-project/environment/role isolation;
- secret redaction;
- page prompt-injection/memory-poisoning fixtures;
- model-derived hypothesis never treated as observed fact;
- bounded MemoryContext and deterministic ranking controls;
- local Graphiti LLM/embedder integration contract tests with fake/OpenAI-compatible endpoints.
