# Session Handoff

Última sesión: 2026-08-18 (Opus 5). **Phases 02, 03, 04 y 05 completadas** en esta sesión.

# Current Phase

06 — vLLM model adapter/router (`plans/phase-06-vllm-router.md`). Phase 05 está DONE con sus 3 gates PASS.

# Phase Status

- Phases 00, 01, 02, 03, 04, 05: **DONE**.
- Phase 06: **NOT_STARTED**. No existe adapter de vLLM ni router de modelos; el único `ModelGateway` es el doble determinista de tests.

# Last Stable State

- Git branch `main`, working tree limpio salvo esta actualización de docs.
- `bash scripts/ci-local.sh` → **all green**: 274 tests backend, 1 frontend, migraciones sin drift, build frontend, compose config.
- Stack corriendo: postgres, redis, temporal, temporal-ui, falkordb, api, worker. Schema en `f9911e78285a`.

# Architecture Decisions Made

Phase 05:

- **Los nodos deciden, la activity persiste.** El graph marca `safe_point`; el `RecoveryPoint` durable lo escribe la activity, donde existe el checkpoint id real. Así el código replayable no hace escrituras a base de datos.
- **`recovery_points`, no `checkpoints`**: el saver de LangGraph posee una tabla con ese nombre exacto y colisionaban (`column "thread_id" does not exist`). `alembic/env.py` declara además las tablas que la librería gestiona, para que autogenerate no proponga borrarlas.
- **Recover es el único dueño del retry semántico** (ADR 0009), con tope de intentos: un step que nunca funciona cierra el episodio en vez de girar.
- **El silencio del planner no es verificación.** Si una acción falló y el planner luego no propone nada, el episodio se cierra como fallido con el motivo, no como éxito. (Era un bug real, encontrado por un test.)
- **Puerto `EpisodeRunner`**: la activity resuelve la policy, pide el episodio y anota el resultado; qué motor lo ejecuta queda detrás del port.
- **El runner recibe el browser ya envuelto en la policy**, así que no puede pasar un gateway sin guardia al graph.
- **El worker no configura agent runtime todavía**: ejecutar un episodio necesita un `ModelGateway` real y el único que existe es el doble de tests. La activity dice "no runtime configurado" en vez de simular. Phase 06 lo suministra.
- **Windows: psycopg async exige `SelectorEventLoop`, Playwright exige `Proactor`** (verificado, no supuesto). Como el graph depende del *port* del browser, la durabilidad se prueba con un doble y el browser real se prueba aparte; en Linux comparten loop.

# Files Created

Backend (Phase 05):

- `domain/agent/state.py`, `domain/runs/recovery.py`
- `application/ports/checkpoints.py`, `models.py`, `episodes.py`
- `infrastructure/agent/langgraph/`: `checkpointer.py`, `graph.py`, `episode_runner.py`
- `alembic/versions/f9911e78285a_phase_05_recovery_points.py`
- Tests: `tests/agent/{test_state_and_recovery,test_checkpointer,test_graph,test_graph_resume,test_episode_activity}.py`, `tests/fakes/agent.py`

# Files Modified

- `infrastructure/workflows/temporal/{activities,contracts,worker}.py`: `run_episode` real, `EpisodeParams.goal`, nota de wiring pendiente.
- `bootstrap/container.py`: campo `episodes`.
- `infrastructure/persistence/postgres/*` y `tests/fakes/*`: repositorio de recovery points.
- `alembic/env.py`: tablas propiedad de LangGraph excluidas.
- `docs/11-data-and-artifacts.md`: renombrado documentado.
- `backend/pyproject.toml`: `langgraph`, `langgraph-checkpoint-postgres`, `psycopg[binary,pool]`.

# Database/Migrations State

- Migraciones: … → `6c4d6570f65c` → **`f9911e78285a`** (`recovery_points`). `alembic check` limpio.
- Tablas propias: projects, environments, run_policies, user_stories, acceptance_criteria, runs, run_events, recovery_points, idempotency_records. LangGraph crea las suyas con `setup()`.

# Tests Executed

```
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
cd backend && uv run alembic upgrade head && uv run alembic check
bash scripts/ci-local.sh
graphify . --code-only
```

# Exact Test Results

- **274 tests backend passed** (0 failed, warnings-as-errors activo):
  - `tests/domain` 59 · `tests/contracts` 80 · `tests/application` 21 · `tests/http` 29 · `tests/browser` 31 · `tests/agent` 26 · `tests/integration` 16 · `tests/architecture` 10 · `tests/test_health.py` 2
- ruff "All checks passed!"; mypy strict "no issues found in 155 source files"; `alembic check` sin drift.
- Frontend: eslint OK, tsc OK, vitest 1 passed, build OK. `ci-local.sh`: "ci-local: all green".

# Acceptance Gates (Phase 05)

| Gate | Resultado |
| --- | --- |
| Run retoma desde último safe checkpoint | **PASS** (3 tests: el worker muere en la página 3 y el reemplazo continúa desde ahí sin repetir 1 y 2; el estado sobrevive a una conexión nueva; la activity persiste el RecoveryPoint con el checkpoint id real) |
| Active context no crece linealmente con steps | **PASS** (3 tests: ventana de 12 acotada, 500 steps → 10 summaries, y el planner nunca recibe más que la ventana) |
| No duplicate side effect en crash window test | **PASS** (2 tests: el efecto que aterrizó antes del crash se observa en vez de repetirse — exactamente un registro) |

# Known Issues

- **El worker no ejecuta episodios todavía** porque no hay `ModelGateway` real (Phase 06). Es una decisión explícita, no un olvido: la activity lo reporta.
- El `RecoveryPoint` que escribe la activity lleva `browser.url` vacío: el graph aún no devuelve la URL observada en el resultado del episodio. Rellenarlo es trabajo de Phase 06/07 cuando el episodio tenga navegación real.
- `more_work` siempre es `False`: un episodio por goal. La planificación multi-episodio llega con el workflow de historias (Phase 07).
- Windows: conflicto de event loops ya descrito; los tests que combinan checkpointer y browser en un proceso no existen (y en Linux no harían falta).
- Los tests de integración hacen skip si el servicio no responde.
- La suite tarda ~1 min por browser + checkpointer.

# Technical Debt

- `open_checkpointer` abre y cierra conexión por episodio; con muchos episodios convendrá un pool.
- El nodo "Retrieve Memory" de docs/06 no existe (Phase 09), a propósito.
- Sin endpoints de `Environment`, sin GET de policies, sin presence/heartbeat en Redis.
- `test-target-app` vive en `backend/tests/target_app/`.
- structlog pendiente (docs/14).

# Risks

- Phase 06 debe inyectar el `ModelGateway` real en el container **sin** cambiar la forma del workflow (ADR 0009) ni el reparto de retries: el modelo no debe reintentar por su cuenta.
- El planner real devolverá acciones que hay que validar contra el action set cerrado; el `GuardedBrowserGateway` ya bloquea lo que la policy prohíbe, pero un modelo que proponga basura debe fallar de forma tipada.
- Toda activity de Temporal invocada por nombre necesita `result_type` explícito.
- CI en Linux pendiente (Phase 13).

# Decisions Still Open

- Cómo se deriva el `goal` de un episodio (hoy es un default declarado en `EpisodeParams`; Phase 07 lo saca de la historia).
- Dónde se genera el `evidence_set_id` y cuándo el graph captura screenshots/traces.
- Estrategia de pooling para el checkpointer.

# Graphify Status

- `graphify-out/graph.json` refrescado (code-only, incremental).

# Services That Are Working

- postgres (`f9911e78285a` + tablas de LangGraph), redis, temporal + temporal-ui, falkordb, api (`http://localhost:8000/docs`), worker. Chromium vía Playwright.

# Services Still Stubbed/Deferred

- `frontend` como servicio compose (Phase 10), `vllm` (06), `vllm-embed` (09), `airllm` (11).

# Exact Next Task

Implement Phase 06 slice 1: add a `ModelGateway` adapter for an OpenAI-compatible vLLM endpoint that returns *structured* planned actions validated against the closed browser action set, rejecting malformed model output with a typed error instead of coercing it — the graph already consumes this port, so nothing above it changes.

# Exact Next Command

En Claude Code: `/implement-phase 06`

# Recommended Skills For Next Session

- `implement-phase` (proceso), `ponytail` (always-on).
- `prompt-engineering-patterns` (structured outputs, versionado de prompts, defensa ante prompt injection) + `error-handling-patterns`.
- `durability-review` si la inferencia entra en una activity larga.
- `architecture-guard` + `test-and-verify` al cierre.
