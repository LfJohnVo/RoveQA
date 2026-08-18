# Progress

Última actualización: 2026-08-18 — Phase 05 completada; Phases 00-04 completadas y blueprint auditado (ver HANDOFF).

| Phase | Status | Evidence |
|---|---|---|
| 00 | DONE | `scripts/ci-local.sh` all green (blueprint + ruff/format/mypy/pytest + eslint/tsc/vitest/build + compose config); 5 servicios compose healthy; FalkorDB persistence probada write→restart→read; imágenes backend/frontend construidas; graphify-out/graph.json generado (code-only) |
| 01 | DONE | 4/4 gates PASS: 23 domain tests (Run state machine + Verdict + entity invariants), migración verificada desde schema vacío + `alembic check` sin drift, test automático de dependency rule (Domain/Application sin ORM/framework), 20 contract tests corriendo contra memory y PostgreSQL. 68 tests backend; `ci-local.sh` all green |
| 02 | DONE | 7/7 gates PASS: run sobrevive al reemplazo del worker (test contra Temporal real), API sin loops largos, workflow puro (test AST), status sólo escrito por activities vía state machine, request id end-to-end en logs, duplicate POST /runs no duplica run ni workflow, reuse incompatible de key falla tipado. 112 tests backend; e2e por el stack containerizado (api+worker) → completed/inconclusive |
| 03 | DONE | 3/3 gates PASS: cliente reconecta y recupera baseline durable desde `run_events` (REST + WebSocket con catch-up antes del live), `FLUSHALL` + restart de Redis no cambian status ni historial confirmados, locks expiran/renuevan con ownership token verificado por Lua. 173 tests backend; e2e containerizado con 3 eventos en el log durable y en el stream |
| 04 | DONE | 5/5 gates PASS: sin JS arbitrario (action set cerrado), origin policy aplicada en dominio y sobre Chromium real, recovery tras crash real con storage state, manifests con provenance verificable (hash/size/streaming), y cross-run imposible por construcción. 247 tests incl. 31 de browser contra Chromium; `ci-local.sh` all green |
| 05 | DONE | 3/3 gates PASS: run reanuda desde el último safe checkpoint (worker muere en la página 3, el reemplazo continúa desde ahí contra el checkpointer PostgreSQL real), contexto del planner acotado (500 steps → ventana de 12), y sin side effect duplicado en la crash window. 274 tests; `RunEpisodeActivity` ejecuta el graph y persiste el RecoveryPoint |
| 06 | NOT_STARTED | desbloqueada por 05 |
| 07 | BLOCKED | requiere 05-06 |
| 08 | BLOCKED | requiere 02 + 07 contracts |
| 09 | BLOCKED | requiere 07 |
| 10 | BLOCKED | requiere APIs de 02/07; CLI 08 recomendado para agent workflow |
| 11 | BLOCKED | requiere 07 |
| 12 | BLOCKED | requiere 07-09 |
| 13 | BLOCKED | requiere core completo |
| 14 | BLOCKED | requiere 13 |

Statuses permitidos: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `DONE`.

Notas:
- 2026-08-18: auditoría de blueprint (6 dimensiones) previa a Phase 00. 2 BLOCKERs corregidos (label observed/model_derived en MemoryContext; regla de resolución de RunPolicy) y ~15 IMPORTANT (contratos versionados, Verdict domain value, ADR 0009 retry ownership/workflow shape/checkpoints, semántica de origins, credential handling, identity model v1). Ver commit `docs(blueprint): fix audit blockers...`.
- Blueprint update previo: adaptive memory graph design para Phase 09 (Graphiti + FalkorDB como proyección reconstruible; implementación no iniciada).
