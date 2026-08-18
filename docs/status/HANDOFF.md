# Session Handoff

Última sesión: 2026-08-18 (Claude Fable 5 → Opus 5). Auditoría de blueprint, Phase 00 y Phase 01 completas.

# Current Phase
02 — Run API + Temporal Lifecycle (`plans/phase-02-temporal-run-lifecycle.md`). Phase 01 está DONE con sus 4 gates PASS.

# Phase Status
- Phase 00: **DONE** (gates PASS; ver histórico más abajo).
- Phase 01: **DONE** (4/4 gates PASS, ver Acceptance Gates).
- Phase 02: **NOT_STARTED**. No existe FastAPI, ni Temporal SDK, ni idempotency records.

# Last Stable State
- Git branch `main`, working tree limpio, 14 commits. Último: `test(architecture): enforce the dependency rule and wire migrations into the gate`.
- `bash scripts/ci-local.sh` → **all green** (68 tests backend, 1 frontend, migraciones sin drift, build frontend, compose config).
- PostgreSQL levantado durante la sesión con el schema de Phase 01 migrado a head (`a2fc1518b988`).

# Architecture Decisions Made
Esta sesión (Phase 01), además de las de Phase 00 (ADR 0009 y el endurecimiento de contratos):

- **Use cases como funciones, no clases**: sin estado ni polimorfismo que justifiquen una clase; FastAPI podrá depender de ellas directamente en Phase 02. Convertir a clases es mecánico si Phase 02 lo necesita.
- **Los use cases no hacen commit**: el caller es dueño del transaction boundary (session-per-request). No se introdujo un `UnitOfWork` port porque ninguna operación actual es multi-repo atómica; **Phase 02 sí lo necesitará** (run + idempotency record deben ser atómicos) y ese es el momento de añadirlo.
- **Enums como VARCHAR + CHECK nombrado en `__table_args__`**, no native PG enum ni `Enum(create_constraint=True)`: el CHECK implícito que emite SQLAlchemy es invisible para autogenerate, que entonces propone borrarlo (detectado con `alembic check`). Añadir un valor al enum queda como una migración normal y revisable.
- **Duplicados: chequeo aplicativo + constraint de DB**. Los adapters comprueban existencia primero (error limpio, sin INSERT fallido ni conflicto de identity map) y además mapean SQLSTATE 23505 → `AlreadyExistsError` para carreras concurrentes. Otros IntegrityError (FK, check) se propagan: nunca se disfrazan de "ya existe".
- **Inserts dentro de SAVEPOINT** (`begin_nested`): un insert rechazado no envenena la transacción del caller.
- **Criteria relacional, precondiciones JSONB**: `criterion_id` lo referencian plan steps y findings (contratos), así que es una tabla con orden explícito (`position`); las listas de texto sin necesidad de query van en JSONB.
- **`filterwarnings = ["error"]`** en pytest: un warning es señal de defecto (fue lo que expuso el conflicto de identity map), nunca ruido.
- **Dependency rule como test** (`tests/architecture/`), no como hábito de review. El guard se testea con violaciones plantadas.

# Files Created
Backend (Phase 01):
- `domain/errors.py`, `domain/validation.py`
- `domain/projects/project.py`, `domain/qa/user_story.py`
- `application/errors.py`, `application/ports/repositories.py`
- `application/commands/create_project.py`, `create_story.py`, `create_run_draft.py`
- `application/queries/get_project.py`
- `infrastructure/persistence/postgres/`: `models.py`, `mappers.py`, `engine.py`, `repositories.py`
- `alembic.ini`, `alembic/env.py`, `alembic/versions/a2fc1518b988_phase_01_baseline_projects_stories_.py`
- Tests: `tests/conftest.py`, `tests/fakes/repositories.py`, `tests/contracts/test_repository_contracts.py`, `tests/domain/test_entities.py`, `tests/application/test_use_cases.py`, `tests/integration/test_schema_constraints.py`, `tests/integration/test_use_cases_postgres.py`, `tests/architecture/test_layer_boundaries.py` (+ `__init__.py` de cada paquete de tests)

# Files Modified
- `domain/runs/run.py`: `RunTransitionError` hereda `DomainError`; validación de identificadores en `__post_init__`.
- `backend/pyproject.toml`: deps sqlalchemy[asyncio]/alembic/asyncpg + pytest-asyncio; mypy cubre `src` y `tests`; `asyncio_mode=auto`; `filterwarnings=["error"]`; ruff excluye `alembic/versions`.
- `scripts/ci-local.sh` (paso de migraciones), `Makefile` (targets `migrate`/`migrate-down`).
- `docs/11-data-and-artifacts.md` (marca ✅ las tablas ya migradas), `docs/status/PROGRESS.md`.
- `graphify-out/graph.json` (refrescado, incremental).

# Database/Migrations State
- Una sola migración: **`a2fc1518b988`** (baseline Phase 01) creando `projects`, `user_stories`, `acceptance_criteria`, `runs`.
- Verificado en esta sesión: `DROP SCHEMA public CASCADE` → `alembic upgrade head` reconstruye el schema completo; `downgrade base` → `upgrade head` limpio; `alembic check` reporta "No new upgrade operations detected".
- Constraints en la DB (probadas con SQL crudo): `ck_runs_status`, `ck_runs_verdict`, `ck_runs_verdict_only_when_terminal`, FK `runs.project_id` (RESTRICT), FK `user_stories.project_id` (CASCADE), `uq_acceptance_criteria_story_criterion`, `uq_acceptance_criteria_story_position`.
- DSN por defecto `postgresql+asyncpg://agentic:agentic@localhost:5432/agentic_qa`; override con `POSTGRES_DSN` (migraciones) o `POSTGRES_TEST_DSN` (tests).

# Docker State
- Durante la sesión sólo se levantó `postgres` (`docker compose up -d postgres`). Los demás servicios quedaron abajo; volúmenes `roveqa_postgres_data` y `roveqa_falkordb_data` persisten.
- `make up` levanta el set completo (postgres, redis, temporal, temporal-ui, falkordb). Nunca `down -v`: destruiría las DBs de Temporal.
- Imágenes `roveqa-backend:dev` / `roveqa-frontend:dev` construidas en Phase 00; aún no incorporan las nuevas deps (reconstruir cuando Phase 02 añada el servicio `api`).

# Tests Executed
```
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
cd backend && uv run alembic upgrade head && uv run alembic check
cd backend && uv run alembic downgrade base && uv run alembic upgrade head
docker exec roveqa-postgres-1 psql -U agentic -d agentic_qa -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"   # luego upgrade head
bash scripts/ci-local.sh
graphify . --code-only ; graphify explain "create_run_draft"
```

# Exact Test Results
- **68 tests backend passed** (0 failed, 0 skipped, warnings-as-errors activo), desglose:
  - `tests/test_health.py`: 2
  - `tests/domain`: 23 (12 state machine + 11 invariantes de entidades)
  - `tests/contracts`: 20 (10 casos × memory y postgres)
  - `tests/application`: 10
  - `tests/integration`: 6 (5 constraints de schema + 1 end-to-end use case→DB)
  - `tests/architecture`: 7
- ruff: "All checks passed!"; ruff format: sin cambios; mypy strict: "Success: no issues found in 66 source files".
- Alembic: upgrade desde schema vacío OK; `alembic check` → "No new upgrade operations detected".
- Frontend: eslint OK, tsc OK, vitest 1 passed, build OK.
- `ci-local.sh`: "ci-local: all green".
- Graphify: extracción incremental (59 cacheados, 35 re-extraídos); `graphify explain "create_run_draft"` devuelve sus 9 conexiones.

# Acceptance Gates (Phase 01)
| Gate | Resultado |
|---|---|
| Domain unit tests cubren run state invariants | **PASS** (23 tests: transiciones legales/ilegales, verdict sólo en terminales, FAILED→inconclusive/blocked, identificadores) |
| DB limpia puede migrar a head | **PASS** (probado tras `DROP SCHEMA public CASCADE`; también downgrade base → upgrade head) |
| No ORM imports en Domain/Application | **PASS** (test automático AST; Domain sólo importa stdlib + domain, Application stdlib + domain/application) |
| Repository contract tests verdes | **PASS** (20 casos idénticos contra fakes y PostgreSQL) |

Gates transversales: `architecture-guard` ejecutado (ahora automatizado como test), `test-and-verify` vía `ci-local.sh` all green.

# Known Issues
- Los tests de integración **hacen skip** si PostgreSQL no está accesible. `ci-local.sh` lo compensa migrando antes (falla ruidosamente si la DB está caída), pero un `pytest` suelto sin DB pasa en verde con menos cobertura de la real.
- Graphify sigue siendo code-only (los 106 docs necesitan un LLM API key). `graphify update` no acepta `--code-only`; usar `graphify . --code-only` (es incremental igual).
- Imágenes Docker de Phase 00 desactualizadas respecto a las nuevas dependencias del backend.

# Technical Debt
- **`UnitOfWork` port pendiente**: los use cases no commitean y nadie agrupa escrituras atómicamente. Phase 02 lo necesita de verdad (run + idempotency record).
- No hay `Environment` ni `RunPolicy` como entidades/tablas todavía; la regla normativa de resolución de RunPolicy (docs/12) no tiene dónde apoyarse hasta que existan. Phase 02/04.
- `Run` no persiste `created_at` en el dominio (la columna existe con `server_default`); si Phase 02 necesita ordenar runs por fecha, hay que subirlo al dominio.
- `frontend/index.css` conserva estilos del template Vite (Phase 10).
- IMPORTANT de la auditoría aún abiertos por fase: schemas de `result.json`/`steps.json` del bundle (07/08), endpoints de memory admin (09), `allowed_action_classes` explícitos (04).

# Risks
- Phase 02 introduce Temporal: la forma de workflow está fijada por ADR 0009 (una activity por episodio, continue-as-new, pause/cancel por signal). Desviarse rompe Phase 05.
- El pre-chequeo de duplicados en los adapters es una defensa amable, no una garantía; la garantía real es la constraint. No convertirlo en la única defensa al añadir idempotencia en Phase 02.
- Compatibilidad GPU/modelos vLLM/AirLLM sin validar (Phases 06/09/11).
- Los checks locales corren en Windows; el runtime es Linux. CI en Linux pendiente (Phase 13).

# Decisions Still Open
- Estrategia de identidad de runs en Phase 02: `uuid4` actual vs id derivado de la idempotency key.
- Dónde vive el commit: `UnitOfWork` port explícito vs dependencia FastAPI que commitea al cerrar el request.
- Modelos concretos vLLM/AirLLM (Phases 06/09/11) y auth de plataforma post-v1 (requiere ADR).

# Graphify Status
- `graphify-out/graph.json` refrescado tras Phase 01 (code-only, incremental). Query verificada: `graphify explain "create_run_draft"`. Refrescar con `graphify . --code-only` tras cambios estructurales.

# Services That Are Working
- postgres:16-alpine con el schema de Phase 01 migrado (único servicio levantado al cierre; el resto arranca con `make up`).
- redis, temporal, temporal-ui, falkordb: verificados healthy en Phase 00, sin cambios en esta sesión.

# Services Still Stubbed/Deferred
- `api` y `worker` (Phase 02), `frontend` como servicio compose (Phase 10), `vllm` (06), `vllm-embed` (09), `airllm` (11), `test-target-app` (04).

# Exact Next Task
Implement Phase 02 slice 1: add a `UnitOfWork` port in `backend/src/agentic_qa/application/ports/` with a PostgreSQL adapter (session + commit/rollback), and make `create_run_draft` run inside it — this is the seam the durable `Idempotency-Key` record needs before any FastAPI endpoint or Temporal workflow is written.

# Exact Next Command
En Claude Code: `/implement-phase 02`

# Recommended Skills For Next Session
- `implement-phase` (proceso), `ponytail` (always-on).
- `backend-slice` + `api-design-principles` (endpoints de run, DTOs, error contract) + `error-handling-patterns`.
- `postgresql` (idempotency records durables, transacciones).
- `durability-review` (Temporal lifecycle, wait≠cancel, retry ownership de ADR 0009).
- `architecture-guard` + `test-and-verify` al cierre.
