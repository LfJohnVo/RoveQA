# Session Handoff

Última sesión: 2026-08-18 (Opus 5). **Phases 02, 03 y 04 completadas**; **Phase 05 iniciada (slice 1 de 4)**.

# Current Phase

05 — LangGraph Agent Core (`plans/phase-05-langgraph-agent-core.md`). **IN_PROGRESS**: el camino de resume está construido y probado; faltan los nodos y el cableado a la activity.

# Phase Status

- Phases 00, 01, 02, 03, 04: **DONE**.
- Phase 05: **IN_PROGRESS**.
  - Slice 1 **DONE**: `AgentState`, `RecoveryPoint` + tabla, checkpointer PostgreSQL verificado.
  - Slices 2-4 **PENDIENTES**: nodos del graph + fake model, compaction en el runtime real, `RunEpisodeActivity` con heartbeat y los tests de kill/restart y crash window.

# Last Stable State

- Git branch `main`, working tree limpio (queda por commitear sólo esta actualización de docs).
- `bash scripts/ci-local.sh` → **all green**: 260 tests backend, 1 frontend, migraciones sin drift, build frontend, compose config.
- Stack corriendo: postgres, redis, temporal, temporal-ui, falkordb, api, worker. Schema en `f9911e78285a`.

# Architecture Decisions Made

Phase 05 slice 1:

- **`recovery_points` en vez de `checkpoints`**: el checkpointer de LangGraph crea una tabla llamada exactamente `checkpoints`, y colisionaba con la del dominio (fallo real: `column "thread_id" does not exist`). El nombre nuevo además es el correcto según ADR 0009: un `RecoveryPoint` es un momento *semánticamente* seguro con datos para reconstruir el browser, no un checkpoint por superstep. `docs/11` registra el motivo.
- **Frontera de propiedad de tablas en Alembic**: `env.py` excluye las tablas que LangGraph crea y migra por su cuenta (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`). Sin eso, autogenerate proponía borrarlas y `alembic check` nunca quedaba limpio.
- **Dos drivers contra una base**: SQLAlchemy usa asyncpg; el checkpointer de LangGraph exige psycopg. Se aceptó en vez de reimplementar el checkpointer; la traducción del DSN vive en un único sitio (`to_psycopg_dsn`).
- **Contexto plano por diseño**: `AgentState` mantiene una ventana de 12 steps y pliega los episodios cerrados en summaries. 500 steps ejecutados dejan 10 entradas para el planner.

# Files Created

- `domain/agent/state.py` (`AgentState`, `StepRecord`, `EpisodeSummary`)
- `domain/runs/recovery.py` (`RecoveryPoint`, `BrowserRecoveryData`, `RecoveryTrigger`)
- `application/ports/checkpoints.py`
- `infrastructure/agent/langgraph/checkpointer.py`
- `alembic/versions/f9911e78285a_phase_05_recovery_points.py`
- Tests: `tests/agent/test_state_and_recovery.py`, `tests/agent/test_checkpointer.py`

# Files Modified

- `infrastructure/persistence/postgres/{models,repositories,unit_of_work}.py`: `RecoveryPointModel` + repositorio + propiedad `recovery_points` en el UoW.
- `application/ports/unit_of_work.py`, `tests/fakes/{repositories,unit_of_work}.py`: mismo port en el fake.
- `alembic/env.py`: exclusión de tablas ajenas.
- `docs/11-data-and-artifacts.md`: renombrado documentado.
- `tests/conftest.py`: helper `postgres_test_dsn` (renombrado desde `test_dsn`, que pytest coleccionaba como test) y tablas nuevas en el TRUNCATE.
- `backend/pyproject.toml`: `langgraph`, `langgraph-checkpoint-postgres`, `psycopg[binary,pool]`.

# Database/Migrations State

- Migraciones: … → `6c4d6570f65c` → **`f9911e78285a`** (`recovery_points`).
- `alembic check` limpio con la exclusión de tablas de LangGraph.
- Tablas propias: projects, environments, run_policies, user_stories, acceptance_criteria, runs, run_events, recovery_points, idempotency_records. LangGraph añade las suyas al hacer `setup()`.

# Tests Executed

```
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
cd backend && uv run alembic upgrade head && uv run alembic check
bash scripts/ci-local.sh
graphify . --code-only
```

# Exact Test Results

- **260 tests backend passed** (0 failed, warnings-as-errors activo):
  - `tests/domain` 59 · `tests/contracts` 80 · `tests/application` 21 · `tests/http` 29 · `tests/browser` 31 · `tests/agent` 13 · `tests/integration` 16 · `tests/architecture` 10 · `tests/test_health.py` 2
- ruff "All checks passed!"; mypy strict "no issues found in 147 source files" **sin `type: ignore` en código de producción**; `alembic check` sin drift.
- Frontend: eslint OK, tsc OK, vitest 1 passed, build OK. `ci-local.sh`: "ci-local: all green".

# Acceptance Gates (Phase 05) — estado parcial

| Gate | Estado |
| --- | --- |
| Active context no crece linealmente con steps | **PASS** (500 steps → 10 summaries; ventana de 12 acotada y testeada) |
| Run retoma desde último safe checkpoint | **PARCIAL**: el estado del graph sobrevive a una conexión nueva y el `RecoveryPoint` más reciente es recuperable, pero **no existe todavía un run real que reanude** (falta el graph y la activity). |
| No duplicate side effect en crash window test | **PENDIENTE** (la mecánica existe: `perform_once` de Phase 04; falta ejercitarla dentro del graph) |

# Known Issues

- **Windows: psycopg async no funciona con `ProactorEventLoop`** (el default) y Playwright necesita ese loop para su subproceso. Los tests del checkpointer conducen su propio `SelectorEventLoop`; si el graph acaba usando checkpointer y browser en el *mismo* proceso en Windows, habrá que resolverlo (en Linux, donde corre el worker, no hay conflicto). **Es el primer riesgo a validar en el slice 2.**
- Un `uvicorn` huérfano de una sesión anterior bloqueó el venv e hizo fallar `uv add`. Si `uv` falla con "Acceso denegado", buscar procesos python/uvicorn del venv y cerrarlos.
- Los tests de integración (postgres, Temporal, Redis) hacen skip si el servicio no responde.
- El browser sigue sin estar cableado a ningún run (eso es el slice 4).

# Technical Debt

- `open_checkpointer` abre y cierra su propia conexión; cuando el worker ejecute muchos episodios convendrá reutilizar un pool.
- `AgentState` aún no se persiste como parte del graph: el slice 2 debe decidir si el state del graph *es* `AgentState` o lo envuelve.
- Sigue sin haber endpoints de `Environment`, ni GET de policies, ni presence/heartbeat en Redis.
- `test-target-app` vive en `backend/tests/target_app/`.

# Risks

- El conflicto de event loop en Windows puede obligar a ejecutar el graph y el browser en procesos distintos, o a mover los tests del graph a Linux/CI. Decidirlo pronto evita rehacer el slice 4.
- El graph no debe cambiar la forma del workflow fijada por ADR 0009 (una activity por episodio).
- Toda activity de Temporal invocada por nombre necesita `result_type` explícito.

# Decisions Still Open

- Si el state de LangGraph es `AgentState` directamente (dataclass) o un `TypedDict` que lo contiene.
- Dónde se genera el `evidence_set_id`: por episodio, por step o por run.
- Cómo convive el checkpointer con el pool de SQLAlchemy (dos drivers, una base).

# Graphify Status

- `graphify-out/graph.json` refrescado (code-only, incremental).

# Services That Are Working

- postgres (`f9911e78285a` + tablas de LangGraph), redis, temporal + temporal-ui, falkordb, api (`http://localhost:8000/docs`), worker. Chromium vía Playwright.

# Services Still Stubbed/Deferred

- `frontend` como servicio compose (Phase 10), `vllm` (06), `vllm-embed` (09), `airllm` (11).

# Exact Next Task

Implement Phase 05 slice 2: build the LangGraph agent graph with its Observe/Plan/Act/Verify/Recover/Checkpoint/CloseEpisode nodes over a deterministic FakeModelGateway, driving the guarded browser against the test target app — and settle first whether the graph and the browser can share one process on Windows, since psycopg's checkpointer needs a SelectorEventLoop and Playwright needs the Proactor one.

# Exact Next Command

En Claude Code: `/implement-phase 05`

# Recommended Skills For Next Session

- `implement-phase` (proceso), `ponytail` (always-on).
- `durability-review` (resume, uncertainty window) + `browser-runtime` (el graph conduciendo el browser).
- `prompt-engineering-patterns` cuando aparezca el ModelGateway real (Phase 06; en 05 el fake es determinista).
- `systematic-debugging` para el conflicto de event loop.
- `architecture-guard` + `test-and-verify` al cierre.
