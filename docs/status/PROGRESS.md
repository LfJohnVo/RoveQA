# Progress

Última actualización: 2026-08-19 — Phase 07 completada; Phases 00-06 completadas, vLLM validado sobre GPU real, pipeline containerizado y blueprint auditado (ver HANDOFF).

| Phase | Status | Evidence |
|---|---|---|
| 00 | DONE | `scripts/ci-local.sh` all green (blueprint + ruff/format/mypy/pytest + eslint/tsc/vitest/build + compose config); 5 servicios compose healthy; FalkorDB persistence probada write→restart→read; imágenes backend/frontend construidas; graphify-out/graph.json generado (code-only) |
| 01 | DONE | 4/4 gates PASS: 23 domain tests (Run state machine + Verdict + entity invariants), migración verificada desde schema vacío + `alembic check` sin drift, test automático de dependency rule (Domain/Application sin ORM/framework), 20 contract tests corriendo contra memory y PostgreSQL. 68 tests backend; `ci-local.sh` all green |
| 02 | DONE | 7/7 gates PASS: run sobrevive al reemplazo del worker (test contra Temporal real), API sin loops largos, workflow puro (test AST), status sólo escrito por activities vía state machine, request id end-to-end en logs, duplicate POST /runs no duplica run ni workflow, reuse incompatible de key falla tipado. 112 tests backend; e2e por el stack containerizado (api+worker) → completed/inconclusive |
| 03 | DONE | 3/3 gates PASS: cliente reconecta y recupera baseline durable desde `run_events` (REST + WebSocket con catch-up antes del live), `FLUSHALL` + restart de Redis no cambian status ni historial confirmados, locks expiran/renuevan con ownership token verificado por Lua. 173 tests backend; e2e containerizado con 3 eventos en el log durable y en el stream |
| 04 | DONE | 5/5 gates PASS: sin JS arbitrario (action set cerrado), origin policy aplicada en dominio y sobre Chromium real, recovery tras crash real con storage state, manifests con provenance verificable (hash/size/streaming), y cross-run imposible por construcción. 247 tests incl. 31 de browser contra Chromium; `ci-local.sh` all green |
| 05 | DONE | 3/3 gates PASS: run reanuda desde el último safe checkpoint (worker muere en la página 3, el reemplazo continúa desde ahí contra el checkpointer PostgreSQL real), contexto del planner acotado (500 steps → ventana de 12), y sin side effect duplicado en la crash window. 274 tests; `RunEpisodeActivity` ejecuta el graph y persiste el RecoveryPoint |
| 06 | DONE | 3/3 gates PASS: output inválido del modelo nunca llega a Playwright (graph real + browser recorder: prosa, acción inexistente, click sin target y completion vacía → 0 acciones ejecutadas), límite de concurrencia demostrado por endpoint contra Redis real e in-memory (peak in-flight ≤ capacity con 6 llamadas y con dos clientes compartiendo presupuesto), y agent system test con fake model obligatorio + modelo real opcional (skip sin `VLLM_BASE_URL`). 324 tests; e2e en la imagen worker: HTTP real al endpoint → schema → policy → Chromium → checkpoint |
| 07 | DONE | 5/5 gates PASS: una story conocida pasa dos veces seguidas y falla nombrando el criterio incumplido (e2e real contra Chromium + PostgreSQL + target app); el TestPlan valida contra `contracts/test-plan.schema.json` y sobrevive export→import incluido el tipo de los valores de metadata; cada criterio apunta a su plan step y a su run; el reporte se construye desde filas durables y separa `deterministic_observation` de `root_cause_hypothesis`; un criterio sin ancla determinista termina inconclusive sin culpar al producto. 370 tests |
| 08 | NOT_STARTED | desbloqueada por 07 |
| 09 | NOT_STARTED | desbloqueada por 07 |
| 10 | BLOCKED | requiere APIs de 02/07; CLI 08 recomendado para agent workflow |
| 11 | NOT_STARTED | desbloqueada por 07 |
| 12 | BLOCKED | requiere 07-09 |
| 13 | BLOCKED | requiere core completo |
| 14 | BLOCKED | requiere 13 |

Statuses permitidos: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `DONE`.

Notas:
- 2026-08-19 (Phase 07): el verdict deja de ser `inconclusive` fijo y se deriva de resultados durables por criterio. La decisión que gobierna el diseño: **sólo un check determinista puede acusar al producto**; la opinión de un modelo deja el run inconclusive. `EpisodeOutcome` transporta el verdict derivado, no los resultados: éstos viven en PostgreSQL y copiarlos al history de Temporal lo haría crecer por episodio.
- 2026-08-19 (GPU): vLLM `v0.27.1-cu129` sirviendo `Qwen/Qwen3-4B-Instruct-2507` en una RTX 5060 Ti (16GB, sm_120). Dos hallazgos de configuración: `--guided-decoding-backend` ya no existe en 0.27 (es `--structured-outputs-config`, y su default resuelve a xgrammar), y bajo WSL2 vLLM desactiva pinned memory por defecto, lo que mata el engine con "UVA is not available" — se habilita con `VLLM_WSL2_ENABLE_PIN_MEMORY=1`. El test opcional de modelo real pasa contra el endpoint vivo.
- 2026-08-18 (Phase 06): dos defectos encontrados al ejecutar, no al revisar. (1) Una acción denegada por RunPolicy escapaba como excepción desde el graph, lo que hacía que Temporal reintentara el episodio como fallo de infraestructura hasta agotar el timeout de 2h — contra ADR 0009. Ahora se registra como `StepOutcome.DENIED` y cierra el episodio sin replanificar. (2) El checkpointer de LangGraph reconstruía cualquier tipo nombrado en la fila y sólo avisaba; un tipo fuera de la lista vuelve como `dict` y rompe el resume en silencio. Añadido `CHECKPOINTED_TYPES` explícito + `LANGGRAPH_STRICT_MSGPACK=true` en worker y suite, con test de round-trip verificado por mutación.
- 2026-08-18: auditoría de blueprint (6 dimensiones) previa a Phase 00. 2 BLOCKERs corregidos (label observed/model_derived en MemoryContext; regla de resolución de RunPolicy) y ~15 IMPORTANT (contratos versionados, Verdict domain value, ADR 0009 retry ownership/workflow shape/checkpoints, semántica de origins, credential handling, identity model v1). Ver commit `docs(blueprint): fix audit blockers...`.
- Blueprint update previo: adaptive memory graph design para Phase 09 (Graphiti + FalkorDB como proyección reconstruible; implementación no iniciada).
