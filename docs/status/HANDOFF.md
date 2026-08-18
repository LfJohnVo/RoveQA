# Session Handoff

Última sesión: 2026-08-18 (Opus 5). Phases 02 y 03 completadas; **Phase 04 en curso (2 de 5 slices)**.

# Current Phase

04 — Browser Gateway (`plans/phase-04-browser-gateway.md`). **IN_PROGRESS**: los dos slices que desbloqueaban la fase están hechos y verdes; falta el browser real.

# Phase Status

- Phases 00, 01, 02, 03: **DONE** (gates verificados; ver histórico en git y PROGRESS).
- Phase 04: **IN_PROGRESS**.
  - Slice 1 **DONE**: Environment + RunPolicy + resolución normativa.
  - Slice 2 **DONE**: action set tipado cerrado + enforcement de policy inbypasseable.
  - Slices 3-5 **PENDIENTES**: `test-target-app`, adapter Playwright, evidence/artifacts, recovery e integrity tests.

# Last Stable State

- Git branch `main`, working tree limpio.
- `bash scripts/ci-local.sh` → **all green**: 216 tests backend, 1 frontend, migraciones sin drift, build frontend, compose config.
- Stack corriendo: postgres, redis, temporal, temporal-ui, falkordb, api, worker. Schema en `6c4d6570f65c`.
- **Playwright y Chromium ya instalados** en el venv del backend (`uv run playwright install chromium` ejecutado con éxito): el próximo slice arranca sin esperar descargas.

# Architecture Decisions Made

Esta sesión (Phase 04, slices 1-2):

- **Un run no arranca sin RunPolicy resuelta.** Orden normativo (docs/12): policy pedida → default del environment → default del project. Si no resuelve, `422 POLICY_DENIED`. Una referencia colgante o de otro proyecto **falla** en vez de caer a una policy más permisiva.
- **Las policies son inmutables** (sólo add/get). Un run graba `run_policy_id`, así que editarla in-place reescribiría las reglas de runs ya terminados. Cambiar reglas = crear policy nueva y apuntar el default.
- **Origins RFC 6454 con match exacto**: sin subdominios implícitos, sin prefijos de path, sensible a scheme y puerto. Una policy con allowlist vacía es imposible de construir.
- **El action set es cerrado**: no existe `evaluate`/`execute_script`. El control es la ausencia de la capacidad, no un flag que la proteja.
- **El enforcement vive en un wrapper (`GuardedBrowserGateway`), no en el adapter.** Un adapter que olvidara el check seguiría satisfaciendo el port; un run que sólo recibe el gateway guardado no puede saltarse la policy. Las acciones denegadas **lanzan**, no se degradan a no-op silencioso.
- **Una acción que cambia estado no se puede construir** sin declarar `side_effect`, estrategia de idempotencia y estrategia de verificación.

# Files Created

Backend (Phase 04 hasta ahora):

- `domain/projects/run_policy.py`, `domain/projects/environment.py`
- `domain/browser/actions.py`, `domain/browser/policy_guard.py`
- `application/ports/policies.py`, `application/ports/browser.py`
- `application/services/policy_resolution.py`, `application/services/guarded_browser.py`
- `application/commands/create_run_policy.py`
- `alembic/versions/6c4d6570f65c_phase_04_environments_and_run_policies.py`
- Tests: `tests/domain/test_run_policy.py`, `tests/domain/test_browser_actions.py`, `tests/application/test_policy_resolution.py`

# Files Modified

- `domain/projects/project.py` y `domain/runs/run.py`: `default_run_policy_id`; el run guarda `run_policy_id` y `environment_id`.
- `application/commands/start_run.py`: resuelve la policy antes de crear el run; el fingerprint de idempotencia incluye environment y policy.
- `application/ports/repositories.py` + ambas implementaciones: `ProjectRepository.save`.
- `interfaces/http/`: `POST /api/v1/projects/{id}/run-policies`, DTOs de policy, `environment_id`/`run_policy_id` en la creación de runs, `PolicyNotResolvedError` → 422 `POLICY_DENIED`.
- `tests/conftest.py`: `DEFAULT_POLICY_PAYLOAD` y `seed_project_with_default_policy` compartidos (todos los tests que arrancan runs siembran policy).
- `backend/pyproject.toml`: `playwright`.

# Database/Migrations State

- Migraciones: `a2fc1518b988` → `f3aede0b5c07` → `492adc523ebb` → **`6c4d6570f65c`** (`run_policies`, `environments`, y `runs.run_policy_id`/`runs.environment_id`).
- `alembic check` limpio.

# Tests Executed

```
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
cd backend && uv run alembic upgrade head && uv run alembic check
bash scripts/ci-local.sh
graphify . --code-only
```

# Exact Test Results

- **216 tests backend passed** (0 failed, warnings-as-errors activo):
  - `tests/domain` 59 · `tests/contracts` 80 · `tests/application` 21 · `tests/http` 29 · `tests/integration` 16 · `tests/test_health.py` 2 · `tests/architecture` 9
- ruff "All checks passed!"; mypy strict "no issues found in 125 source files" **sin ningún `type: ignore`**; `alembic check` sin drift.
- Frontend: eslint OK, tsc OK, vitest 1 passed, build OK. `ci-local.sh`: "all green".

# Acceptance Gates (Phase 04) — estado parcial

| Gate | Estado |
| --- | --- |
| No arbitrary JS tool expuesto al agente | **PASS** (`test_there_is_no_javascript_action` + action set cerrado verificado contra la lista v1 de docs/07) |
| Origin policy enforced | **PASS a nivel de dominio/aplicación** (match exacto testeado contra subdominios, lookalikes, scheme y puerto; `GuardedBrowserGateway` bloquea antes de ejecutar). Falta confirmarlo con el adapter Playwright real. |
| Browser restart recovery demostrado | **PENDIENTE** (slice 4/5) |
| Artifact manifest consistente con provenance verificable | **PENDIENTE** (slice 4) |
| No "latest artifact" lookup cross-run | **PENDIENTE** (slice 4) |

# Known Issues

- El `GuardedBrowserGateway` existe pero **nadie lo instancia todavía** en producción: el wiring real llega con el adapter Playwright (slice 3). Hasta entonces el enforcement está probado pero no ejercitado end-to-end.
- Los tests de integración (postgres, Temporal, Redis) hacen skip si el servicio no responde; `ci-local.sh` sólo falla ruidosamente por PostgreSQL.
- `run_episode` sigue sin trabajo real (Phase 05), así que todo run completa `inconclusive`.
- El fan-out de eventos falla en silencio por diseño: verificar configuración de Redis end-to-end, no sólo con la suite.
- structlog aún pendiente (docs/14).

# Technical Debt

- No hay endpoints para crear/listar `Environment` (sólo existe la entidad y su tabla); los tests usan el default del project. Añadirlos cuando la UI o la CLI los necesiten.
- No hay listado ni GET de policies por API (sólo POST).
- `run_policy_id` es nullable en `runs` por compatibilidad con runs anteriores a Phase 04; cuando no queden, considerar hacerlo NOT NULL.
- Sigue sin haber presence/heartbeat de workers, rate limits ni caches en Redis.
- WebSocket sin auth ni límite de conexiones (v1 local-first).
- `frontend/index.css` conserva estilos del template Vite (Phase 10).

# Risks

- El adapter Playwright debe recibir **siempre** el gateway guardado. Si alguien inyecta el adapter crudo, el enforcement desaparece sin romper ningún test actual: el próximo slice debería añadir un test de arquitectura que lo impida.
- Phase 05 debe rellenar `run_episode` sin cambiar la forma del workflow (ADR 0009).
- Toda activity de Temporal invocada por nombre necesita `result_type` explícito.
- CI en Linux pendiente (Phase 13).

# Decisions Still Open

- Si el `test-target-app` se implementa como app estática servida por el propio test o como servicio compose (docs/15 pide auth, CRUD, errores 500 controlados, DOM dinámico y fixtures de prompt injection).
- Formato del `PageFingerprint` v1 (docs/07 lista los componentes; falta fijar el hash).
- Retención/purga de `run_events` e `idempotency_records` (Phase 13).

# Graphify Status

- `graphify-out/graph.json` refrescado tras estos slices (code-only, incremental).

# Services That Are Working

- postgres (`6c4d6570f65c`), redis, temporal + temporal-ui, falkordb, api (`http://localhost:8000/docs`, WebSocket `/ws/runs/{id}`), worker.

# Services Still Stubbed/Deferred

- `test-target-app` (slice 3), `frontend` como servicio compose (Phase 10), `vllm` (06), `vllm-embed` (09), `airllm` (11).

# Exact Next Task

Implement Phase 04 slice 3: create the deterministic `test-target-app` (a small local site with a form, a delayed response and a controlled 500) and the Playwright `BrowserGateway` adapter using semantic role/label locators with one BrowserContext per run, wiring it so callers only ever receive it wrapped in `GuardedBrowserGateway` — Playwright and Chromium are already installed, so no download is needed.

# Exact Next Command

En Claude Code: `/implement-phase 04`

# Recommended Skills For Next Session

- `implement-phase` (proceso), `ponytail` (always-on).
- `browser-runtime` (locators, isolation, recovery, artifacts) + `error-handling-patterns`.
- `durability-review` (verify-before-retry, storage state, side effects).
- `architecture-guard` + `test-and-verify` al cierre.
