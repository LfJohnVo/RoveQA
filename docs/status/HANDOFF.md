# Session Handoff

Última sesión: 2026-08-18 (Opus 5). Phase 02 completada. Phases 00 y 01 ya estaban DONE.

# Current Phase
03 — Redis coordination/realtime (`plans/phase-03-redis-realtime.md`). Phase 02 está DONE con sus 7 gates PASS.
Phase 04 (browser gateway) también está desbloqueada por 02; el usuario elige cuál sigue.

# Phase Status
- Phase 00: **DONE**. Phase 01: **DONE**. Phase 02: **DONE** (7/7 gates, ver Acceptance Gates).
- Phase 03: **NOT_STARTED**. No existe cliente Redis, ni locks, ni streams, ni WebSocket.

# Last Stable State
- Git branch `main`, working tree limpio, 19 commits. Último: cierre de Phase 02.
- `bash scripts/ci-local.sh` → **all green**: 112 tests backend, 1 frontend, migraciones sin drift, build frontend, compose config.
- Stack compose levantado durante la sesión: postgres, redis, temporal, temporal-ui, falkordb, **api**, **worker**. Schema migrado a `f3aede0b5c07`.
- E2E verificado por el stack containerizado: `POST /api/v1/projects` → `POST /api/v1/runs` → el worker lleva el run a `completed/inconclusive`.

# Architecture Decisions Made
Esta sesión (Phase 02), sobre ADR 0009 (retry ownership/workflow shape) ya existente:

- **ADR 0010 — Transaction ownership (nuevo)**: los *commands* reciben `UnitOfWork` y son dueños de su commit; las *queries* reciben el repository. Los repositories se obtienen **a través** del UoW, nunca inyectados en paralelo, lo que hace imposible mezclar repositories de transacciones distintas. Salir del bloque sin commit hace rollback.
- **Orden obligatorio para side effects externos** (en ADR 0010): persistir y commitear primero, disparar el efecto después. `POST /runs` commitea run + idempotency record y sólo entonces arranca el workflow; si el arranque falla queda un run `QUEUED` recuperable, nunca un workflow huérfano. Hay test.
- **Sólo el workflow escribe status.** La API señala intención y devuelve `202`; las transiciones ocurren en activities y pasan por el state machine del dominio. Eso es lo que impide que DB y workflow diverjan.
- **Un run se acepta como `QUEUED`**, no `CREATED`: `POST /runs` significa aceptado y encolado. `CREATED` queda para drafts futuros (UI).
- **Payload único en el workflow**: `RunParams` lleva `start_episode`. Un segundo argumento hacía que el converter devolviera JSON crudo.
- **`result_type` explícito** al invocar activities por nombre; sin él la anotación de retorno es mentira (el converter devuelve dict).
- **Verdict honesto**: sin agent runtime, un run completa `inconclusive`, no `passed`.
- **`bootstrap/` es el composition root**: Interfaces no importa infraestructura (test de arquitectura lo prohíbe).

# Files Created
Backend (Phase 02):
- `application/ports/unit_of_work.py`, `application/ports/idempotency.py`, `application/ports/workflows.py`
- `application/commands/start_run.py` (sustituye a `create_run_draft.py`), `application/commands/transition_run.py`
- `bootstrap/settings.py`, `bootstrap/container.py`
- `interfaces/http/`: `app.py`, `dependencies.py`, `errors.py`, `schemas.py`, `request_context.py`, `routers/{projects,runs}.py`
- `infrastructure/persistence/postgres/unit_of_work.py`
- `infrastructure/workflows/temporal/`: `contracts.py`, `activities.py`, `workflows.py`, `gateway.py`, `worker.py`
- `alembic/versions/f3aede0b5c07_phase_02_idempotency_records.py`
- Tests: `tests/contracts/test_unit_of_work_contracts.py`, `tests/http/test_api_contract.py`, `tests/integration/test_api_postgres.py`, `tests/integration/test_temporal_workflow.py`, `tests/fakes/{unit_of_work,workflows}.py`
- `docs/adr/0010-transaction-ownership.md`

# Files Modified
- `application/commands/{create_project,create_story}.py`: reciben UoW y commitean (ADR 0010).
- `application/ports/repositories.py`: `RunRepository.save`.
- `application/errors.py`: `IdempotencyConflictError`.
- `infrastructure/persistence/postgres/{models,repositories}.py`: tabla + adapter de idempotency, `save` de runs.
- `tests/conftest.py`: fixtures `unit_of_work_factory` (memory/postgres) y `postgres_unit_of_work_factory` (con TRUNCATE en teardown).
- `tests/fakes/repositories.py`: `InMemoryStore` compartido con snapshot/restore.
- `compose.yaml`: servicios `api` y `worker`; `docs/12-api-and-events.md`: semántica 202 de los comandos de lifecycle.
- `backend/pyproject.toml`: fastapi, uvicorn, temporalio, httpx(dev).

# Database/Migrations State
- Migraciones: `a2fc1518b988` (baseline Phase 01) → **`f3aede0b5c07`** (Phase 02, `idempotency_records` con PK compuesta `scope+idempotency_key`).
- Verificado: `upgrade head`, `downgrade -1`, re-`upgrade`, `alembic check` limpio.
- Tablas: projects, user_stories, acceptance_criteria, runs, idempotency_records, alembic_version.

# Docker State
- Servicios corriendo al cierre: postgres, redis, temporal, temporal-ui, falkordb, api (`:8000`, healthcheck), worker.
- `make up` levanta sólo las dependencias; `docker compose up -d api worker` añade la aplicación. Nunca `down -v`.
- Imagen `roveqa-api`/`roveqa-worker` construida desde `./backend` en esta sesión.

# Tests Executed
```
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
cd backend && uv run alembic upgrade head && uv run alembic check && uv run alembic downgrade -1 && uv run alembic upgrade head
bash scripts/ci-local.sh
docker compose build api && docker compose up -d api worker
curl POST /api/v1/projects ; curl POST /api/v1/runs (x2, misma Idempotency-Key) ; poll GET /api/v1/runs/{id}
```

# Exact Test Results
- **112 tests backend passed** (0 failed, warnings-as-errors activo):
  - `tests/test_health.py` 2 · `tests/domain` 23 · `tests/contracts` 32 (repos 20 + unit of work 12) · `tests/application` 14 · `tests/http` 19 · `tests/integration` 13 (5 constraints + 3 postgres use-case/api + 5 Temporal) · `tests/architecture` 9
- ruff "All checks passed!"; mypy strict "no issues found in 95 source files"; `alembic check` "No new upgrade operations detected".
- Frontend: eslint OK, tsc OK, vitest 1 passed, build OK. `ci-local.sh`: "all green".
- E2E containerizado: `first=201`, `replay=200`, status final `completed inconclusive`.

# Acceptance Gates (Phase 02)
| Gate | Resultado |
|---|---|
| Run sigue existiendo y su workflow continúa tras restart del worker | **PASS** (`test_run_continues_after_the_worker_is_replaced`: run pausado, worker destruido, worker nuevo, resume → completed) |
| API request no aloja loop largo | **PASS** (`test_creating_a_run_returns_before_it_finishes`: devuelve `queued`, no espera estado terminal) |
| Workflows no realizan I/O directo | **PASS** (`test_workflow_code_performs_no_io`: AST del módulo del workflow sin DB/HTTP/os/random) |
| Status DB y workflow no divergen silenciosamente | **PASS** (toda transición pasa por activities + state machine; `test_status_does_not_change_just_because_a_command_was_accepted`; los tests de Temporal comparan verdict del workflow con el de la DB) |
| Request ID visible de extremo a extremo | **PASS** (`test_internal_errors_are_generic_and_correlatable`: el id del cliente aparece en el log record del servidor) |
| Duplicate `POST /runs` con misma key no crea segundo run | **PASS** (unit, postgres y HTTP; además `test_starting_the_same_run_twice_does_not_duplicate_the_workflow`) |
| Reuse incompatible de una idempotency key falla tipado | **PASS** (`IdempotencyConflictError` → 409 CONFLICT) |

# Known Issues
- El worker de compose **no espera** a que las migraciones estén aplicadas; en una DB nueva hay que correr `make migrate` antes de `docker compose up -d api worker`.
- Los tests de integración (postgres y Temporal) **hacen skip** si el servicio no está accesible; `ci-local.sh` migra antes y falla ruidosamente si la DB está caída, pero Temporal caído sólo produce skips.
- `run_episode` no ejecuta trabajo real (no hay agent runtime hasta Phase 05); por eso todo run completa `inconclusive`.
- Graphify sigue code-only y **no se refrescó** en esta sesión: correr `graphify . --code-only`.
- structlog (tech stack documentada) aún no está: los logs usan stdlib + contextvar. Migrar cuando se implemente `docs/14-observability.md`.

# Technical Debt
- No hay `run_events` ni tabla de eventos: el plan de Phase 02 mencionaba "persist status/events" y sólo se implementó status. Los eventos llegan con Redis Streams/WebSocket (Phase 03).
- No hay `Environment` ni `RunPolicy` como entidades/tablas; la regla normativa de resolución de RunPolicy (docs/12) sigue sin implementarse. Phase 04 la necesita.
- `GET /runs/{id}` no tiene `wait_seconds` (bounded long-poll) — es un seam documentado para Phase 08.
- Sin purga de `idempotency_records` (retención indefinida en v1, Phase 13).
- No hay endpoint de listado de runs ni pagination; llega cuando la UI (Phase 10) o la CLI (Phase 08) lo necesiten.
- `frontend/index.css` conserva estilos del template Vite (Phase 10).

# Risks
- Phase 05 debe rellenar `run_episode` **sin** cambiar la forma del workflow (ADR 0009). Cambiarla invalidaría los tests de durabilidad de Phase 02.
- Los dos bugs de conversión de Temporal (payload dict, `result_type`) reaparecerán al añadir nuevas activities: cualquier activity llamada por nombre necesita `result_type` explícito.
- Compatibilidad GPU/modelos vLLM/AirLLM sin validar (Phases 06/09/11).
- CI en Linux pendiente (Phase 13); todo se verifica en Windows contra contenedores Linux.

# Decisions Still Open
- Si `run_events` va a PostgreSQL además de Redis Streams (Phase 03 debe decidirlo; CLAUDE.md exige que Redis no sea fuente de verdad).
- Cómo se resuelve la RunPolicy efectiva cuando existan Environment/Project defaults (Phase 04).
- Modelos concretos vLLM/AirLLM y auth de plataforma post-v1 (requiere ADR).

# Graphify Status
- `graphify-out/graph.json` está **desactualizado** respecto a Phase 02. Refrescar con `graphify . --code-only` (incremental) antes de usarlo para orientación.

# Services That Are Working
- postgres (schema `f3aede0b5c07`), redis, temporal + temporal-ui, falkordb, **api** (`http://localhost:8000`, `/health`, OpenAPI en `/docs`), **worker** (task queue `agentic-qa`).

# Services Still Stubbed/Deferred
- `frontend` como servicio compose (Phase 10), `vllm` (06), `vllm-embed` (09), `airllm` (11), `test-target-app` (04).

# Exact Next Task
Implement Phase 03 slice 1: add a `RunEventPublisher` port plus its durable PostgreSQL `run_events` table and migration, and have the workflow's activities append an event on every status transition — the durable event log must exist before Redis Streams fan-out is added on top of it, because Redis can never be the source of truth.

# Exact Next Command
En Claude Code: `/implement-phase 03`

# Recommended Skills For Next Session
- `implement-phase` (proceso), `ponytail` (always-on).
- `backend-slice` + `postgresql` (tabla de eventos, secuencia, índices).
- `error-handling-patterns` y `durability-review` (Redis puede desaparecer sin perder el run).
- `api-design-principles` para `GET /runs/{id}/events?after=&limit=` y el WebSocket.
- `architecture-guard` + `test-and-verify` al cierre.
