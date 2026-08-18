# Session Handoff

Última sesión: 2026-08-18 (Opus 5). Phases 02 y 03 completadas. Phases 00 y 01 ya estaban DONE.

# Current Phase

04 — Playwright browser gateway (`plans/phase-04-browser-gateway.md`). Phase 03 está DONE con sus 3 gates PASS.

# Phase Status

- Phase 00: **DONE**. Phase 01: **DONE**. Phase 02: **DONE**. Phase 03: **DONE** (3/3 gates, ver Acceptance Gates).
- Phase 04: **NOT_STARTED**. No existe Playwright, ni BrowserGateway, ni RunPolicy/Environment como entidades.

# Last Stable State

- Git branch `main`, working tree limpio. Último commit: cierre de Phase 03.
- `bash scripts/ci-local.sh` → **all green**: 173 tests backend, 1 frontend, migraciones sin drift, build frontend, compose config.
- Stack compose corriendo: postgres, redis, temporal, temporal-ui, falkordb, api, worker. Schema migrado a `492adc523ebb`.
- E2E containerizado verificado: run completo con 3 eventos (`run.created`, 2× `run.status.changed`) presentes tanto en `run_events` como en el stream `stream:run:{id}` de Redis.

# Architecture Decisions Made

Esta sesión (Phase 03), sobre ADR 0009 (workflow shape/retry ownership) y ADR 0010 (transaction ownership):

- **El log durable de eventos es la fuente; Redis Streams es proyección.** `run_events` (PostgreSQL) se escribe en la **misma transacción** que el cambio que describe; el fan-out ocurre después del commit y es best-effort.
- **`(run_id, sequence)` es único** y el `sequence` se deriva dentro de la transacción: un append concurrente no puede reutilizar en silencio una posición de cursor que un cliente ya consumió.
- **Orden de conexión del WebSocket**: suscribir primero, leer historia durable después, luego relay saltando lo ya entregado. Al revés se pierden los eventos publicados mientras se lee la historia.
- **Fallo de realtime nunca falla un run**: `publish_best_effort` captura de forma deliberada y documentada, *porque* el evento ya es durable. Sin publisher, el WebSocket entrega el baseline completo y cierra con `4503` para que el cliente haga polling REST — nunca finge estar vivo.
- **Locks y semáforos comparan el token dentro de Redis (Lua)**: un `GET`-luego-`DEL` desde el cliente puede borrar un lock que expiró y fue readquirido en medio. Hay tests que plantan ese escenario.
- **Los deadlines de slots usan el reloj de Redis (`TIME`)**, no el del caller, para que workers con reloj desviado coincidan en cuándo caducó un lease.
- **Respuestas de redis-py se normalizan y validan en runtime**, no se castean: una forma no reconocida es un bug a exponer, no datos que adivinar.

# Files Created

Backend (Phase 03):

- `application/ports/events.py`, `application/ports/streams.py`, `application/ports/locks.py`, `application/ports/semaphores.py`
- `application/services/event_publishing.py`, `application/queries/list_run_events.py`
- `infrastructure/cache/redis/`: `locks.py`, `semaphores.py`, `streams.py`
- `interfaces/http/routers/realtime.py` (WebSocket `/ws/runs/{id}`)
- `alembic/versions/492adc523ebb_phase_03_run_events.py`
- Tests: `tests/contracts/{test_event_log_contracts,test_lock_contracts,test_semaphore_contracts}.py`, `tests/http/test_realtime.py`, `tests/integration/test_redis_loss.py`, `tests/fakes/{locks,semaphores,streams}.py`

# Files Modified

- `application/commands/{start_run,transition_run}.py`: append de evento en la transacción + publish best-effort tras el commit.
- `application/ports/unit_of_work.py` y ambos UoW: propiedad `events`.
- `infrastructure/persistence/postgres/{models,repositories}.py`: `RunEventModel` + `PostgresRunEventLog`.
- `interfaces/http/{schemas,dependencies,routers/runs,app}.py`: DTOs de evento, `EventPublisherDep`, `GET /runs/{id}/events`, router realtime.
- `bootstrap/{settings,container}.py`: `REDIS_URL`, publisher Redis y cierre del cliente.
- `compose.yaml`: `REDIS_URL` en api y worker (**faltaba**: los contenedores apuntaban a `localhost` y el fan-out fallaba en silencio — lo detectó el e2e, no los tests).
- `backend/pyproject.toml`: `redis`, `httpx2` (dev, requerido por el `TestClient` de Starlette).

# Database/Migrations State

- Migraciones: `a2fc1518b988` → `f3aede0b5c07` → **`492adc523ebb`** (`run_events`, unique `(run_id, sequence)`, FK a runs con CASCADE).
- Verificado: `upgrade head` y `alembic check` limpio.
- Tablas: projects, user_stories, acceptance_criteria, runs, run_events, idempotency_records, alembic_version.

# Docker State

- Servicios corriendo: postgres, redis, temporal, temporal-ui, falkordb, api (`:8000`), worker. Imágenes reconstruidas esta sesión (incluyen `redis`).
- `make up` levanta dependencias; `docker compose up -d api worker` añade la aplicación. Nunca `down -v`.

# Tests Executed

```
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
cd backend && uv run alembic upgrade head && uv run alembic check
docker compose restart redis        # y luego la suite completa
docker compose build api worker && docker compose up -d api worker
curl POST /projects ; POST /runs ; poll GET /runs/{id} ; GET /runs/{id}/events
docker exec roveqa-redis-1 redis-cli XLEN stream:run:{id}
bash scripts/ci-local.sh
```

# Exact Test Results

- **173 tests backend passed** (0 failed, warnings-as-errors activo):
  - `tests/test_health.py` 2 · `tests/domain` 23 · `tests/contracts` 80 (repos 20 + unit of work 12 + event log 12 + locks 18 + semáforos 18) · `tests/application` 14 · `tests/http` 29 · `tests/integration` 16 (5 constraints + 3 postgres + 5 Temporal + 3 Redis loss) · `tests/architecture` 9
- ruff "All checks passed!"; mypy strict "no issues found in 113 source files"; `alembic check` "No new upgrade operations detected".
- Frontend: eslint OK, tsc OK, vitest 1 passed, build OK. `ci-local.sh`: "all green".
- E2E containerizado: status `completed`, 3 eventos durables con `request_id` propagado en `run.created`, `XLEN stream:run:{id}` = 3.

# Acceptance Gates (Phase 03)

| Gate | Resultado |
| --- | --- |
| UI/client puede reconectar y recuperar baseline durable | **PASS** (`GET /runs/{id}/events?after=` con `next_after`; WebSocket entrega historia y luego live; `test_a_client_rebuilds_its_baseline_after_losing_realtime` tras un flush) |
| Redis loss no cambia resultados ya confirmados de un run | **PASS** (`test_a_flushed_redis_leaves_the_run_and_its_history_intact`; además restart real del contenedor + suite completa verde; y un publisher que siempre falla no impide crear ni completar un run) |
| Locks expiran/renuevan con ownership seguro | **PASS** (18 casos memory/Redis, incluido `test_an_expired_holder_cannot_release_the_new_owners_lock`) |

# Known Issues

- **Los `run_events` no se publican al stream si el evento se crea fuera de un caller que pase publisher.** Hoy lo pasan `start_run` (API) y las activities (worker); cualquier nuevo productor de eventos debe acordarse.
- Los tests de integración (postgres, Temporal, Redis) **hacen skip** si el servicio no responde; `ci-local.sh` sólo falla ruidosamente por PostgreSQL (migraciones).
- El WebSocket no tiene autenticación ni límite de conexiones por run (v1 local-first, docs/13); Phase 13 debe revisarlo.
- `run_episode` sigue sin trabajo real hasta Phase 05, así que todo run completa `inconclusive`.
- structlog aún no está: logs con stdlib + contextvar (pendiente docs/14).

# Technical Debt

- No hay presence/heartbeat de workers en Redis (`worker:{id}:presence`, docs/09) ni rate limits ni caches: el plan de Phase 03 los menciona como responsabilidades permitidas, pero ninguna fase actual los necesita todavía.
- El WebSocket usa `limit=500` fijo para el catch-up inicial; si un run supera 500 eventos el cliente debe paginar por REST antes de conectar. Documentarlo en el contrato del cliente (Phase 08/10).
- `Environment` y `RunPolicy` siguen sin existir como entidades/tablas — **Phase 04 los necesita** para la resolución normativa de RunPolicy (docs/12) y el origin allowlist.
- Sin purga de `idempotency_records` ni trimming configurable de streams por proyecto.
- `frontend/index.css` conserva estilos del template Vite (Phase 10).

# Risks

- El fan-out mal configurado falla **en silencio** por diseño (best-effort). Fue exactamente lo que pasó con `REDIS_URL` ausente en compose: los tests estaban verdes y sólo el e2e lo reveló. Cualquier cambio de configuración de Redis necesita una verificación e2e, no sólo tests.
- Phase 05 debe rellenar `run_episode` sin cambiar la forma del workflow (ADR 0009).
- Toda activity nueva invocada por nombre necesita `result_type` explícito (bug ya sufrido en Phase 02).
- CI en Linux pendiente (Phase 13); todo se verifica en Windows contra contenedores Linux.

# Decisions Still Open

- Si el WebSocket debe soportar múltiples runs por conexión o filtros por tipo de evento (lo decidirá la UI en Phase 10).
- Política de retención/purga de `run_events` para runs largos (Phase 13).
- Cómo se resuelve la RunPolicy efectiva cuando existan Environment/Project defaults (Phase 04).
- Modelos concretos vLLM/AirLLM y auth de plataforma post-v1 (requiere ADR).

# Graphify Status

- `graphify-out/graph.json` refrescado tras Phase 03 (code-only, incremental).

# Services That Are Working

- postgres (schema `492adc523ebb`), redis (locks, semáforos, streams), temporal + temporal-ui, falkordb, api (`http://localhost:8000`, `/docs`, WebSocket `/ws/runs/{id}`), worker.

# Services Still Stubbed/Deferred

- `frontend` como servicio compose (Phase 10), `vllm` (06), `vllm-embed` (09), `airllm` (11), `test-target-app` (04).

# Exact Next Task

Implement Phase 04 slice 1: add `Environment` and `RunPolicy` as domain entities with their PostgreSQL tables and migration, plus the normative RunPolicy resolution at run creation (plan → environment default → project default, failing typed when none resolves) — the browser gateway cannot enforce an origin allowlist before the policy it reads actually exists.

# Exact Next Command

En Claude Code: `/implement-phase 04`

# Recommended Skills For Next Session

- `implement-phase` (proceso), `ponytail` (always-on).
- `browser-runtime` (Playwright, acciones tipadas, recovery) + `error-handling-patterns`.
- `postgresql` (tablas de environment/policy) y `backend-slice`.
- `durability-review` (verify-before-retry, storage state, side effects del browser).
- `architecture-guard` + `test-and-verify` al cierre.
