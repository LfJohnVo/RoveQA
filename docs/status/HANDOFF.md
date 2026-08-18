# Session Handoff

Última sesión: 2026-08-18 (Opus 5). **Phases 02, 03 y 04 completadas** en esta sesión.

# Current Phase

05 — LangGraph Agent Core (`plans/phase-05-langgraph-agent-core.md`). Phase 04 está DONE con sus 5 gates PASS.

# Phase Status

- Phases 00, 01, 02, 03, 04: **DONE**.
- Phase 05: **NOT_STARTED**. No existe LangGraph, ni checkpointer, ni agent state.

# Last Stable State

- Git branch `main`, working tree limpio.
- `bash scripts/ci-local.sh` → **all green**: 247 tests backend, 1 frontend, migraciones sin drift, build frontend, compose config.
- Stack corriendo: postgres, redis, temporal, temporal-ui, falkordb, api, worker. Schema en `6c4d6570f65c`.
- Playwright + Chromium instalados y ejercitados por 31 tests reales de browser.

# Architecture Decisions Made

Phase 04 (sobre ADR 0009 y ADR 0010, ambos vigentes):

- **Un run no arranca sin RunPolicy resuelta**: request → default del environment → default del project; si nada resuelve, `422 POLICY_DENIED`. Referencia colgante o de otro proyecto **falla** en vez de caer a algo más permisivo.
- **Las policies son inmutables** (add/get). El run graba `run_policy_id`, así que editarlas reescribiría las reglas de runs ya terminados.
- **Origins RFC 6454 con match exacto**: sin subdominios implícitos, sin paths, sensible a scheme y puerto. Allowlist vacía imposible de construir.
- **El action set es cerrado**: no existe `evaluate`/`execute_script`. El control es la ausencia de la capacidad.
- **El enforcement vive en `GuardedBrowserGateway`, no en el adapter**, y ahora un test de arquitectura impide que Domain/Application/Interfaces importen el adapter Playwright directamente. Sin esa regla, entregar el adapter crudo desactivaría todos los controles sin poner un test en rojo.
- **Provenance viaja con el artifact** (`run_id` + `evidence_set_id` en la identidad y en el path). Un `EvidenceSet` rechaza cualquier artifact ajeno, y un set contaminado no se puede ni construir: por eso un lookup "latest" no puede fabricar evidencia cross-run.
- **Los artifacts se hashean en streaming**; un write que excede el cap se aborta y se borra el parcial, porque un archivo truncado luego parece evidencia válida. La lectura re-verifica el hash.
- **`PageFingerprint` v1 se construye desde estructura, no contenido**: segmentos identificadores colapsan (`/records/{id}`), el orden de controles se normaliza, y un cambio de controles cambia el digest para forzar revalidación.
- **`perform_once` (verify-before-retry)**: ante un ack perdido se pregunta al target si la referencia de *este* run existe, en vez de repetir la acción. Un write no confirmado se reporta como no verificado, nunca se asume exitoso.

# Files Created

Backend (Phase 04):

- `domain/projects/run_policy.py`, `domain/projects/environment.py`
- `domain/browser/actions.py`, `policy_guard.py`, `evidence.py`, `fingerprint.py`
- `application/ports/policies.py`, `browser.py`, `artifacts.py`
- `application/services/policy_resolution.py`, `guarded_browser.py`, `side_effects.py`
- `application/commands/create_run_policy.py`
- `infrastructure/browser/playwright/gateway.py`
- `infrastructure/artifacts/filesystem/repository.py`
- `alembic/versions/6c4d6570f65c_phase_04_environments_and_run_policies.py`
- Tests: `tests/target_app/` (app determinista + servidor efímero), `tests/browser/` (gateway, evidence/artifacts, recovery), `tests/domain/test_run_policy.py`, `tests/domain/test_browser_actions.py`, `tests/application/test_policy_resolution.py`

# Files Modified

- `domain/projects/project.py`, `domain/runs/run.py`: defaults de policy; el run guarda `run_policy_id`/`environment_id`.
- `application/commands/start_run.py`: resuelve policy antes de crear el run.
- `interfaces/http/`: `POST /api/v1/projects/{id}/run-policies`, DTOs, 422 `POLICY_DENIED`.
- `tests/conftest.py`: `DEFAULT_POLICY_PAYLOAD` y `seed_project_with_default_policy`.
- `tests/architecture/test_layer_boundaries.py`: regla del adapter no envuelto.
- `backend/pyproject.toml`: `playwright`; dev: `python-multipart`.

# Database/Migrations State

- Migraciones: `a2fc1518b988` → `f3aede0b5c07` → `492adc523ebb` → **`6c4d6570f65c`**.
- `alembic check` limpio. Tablas: projects, environments, run_policies, user_stories, acceptance_criteria, runs, run_events, idempotency_records.

# Tests Executed

```
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
cd backend && uv run pytest tests/browser        # Chromium real
cd backend && uv run alembic upgrade head && uv run alembic check
bash scripts/ci-local.sh
graphify . --code-only
```

# Exact Test Results

- **247 tests backend passed** (0 failed, warnings-as-errors activo):
  - `tests/domain` 59 · `tests/contracts` 80 · `tests/application` 21 · `tests/http` 29 · `tests/browser` 31 · `tests/integration` 16 · `tests/architecture` 10 · `tests/test_health.py` 2 (+ recovery incluidos en browser)
- ruff "All checks passed!"; mypy strict "no issues found in 138 source files" **sin ningún `type: ignore`**; `alembic check` sin drift.
- Frontend: eslint OK, tsc OK, vitest 1 passed, build OK. `ci-local.sh`: "ci-local: all green".

# Acceptance Gates (Phase 04)

| Gate | Resultado |
| --- | --- |
| No arbitrary JS tool expuesto al agente | **PASS** (action set cerrado verificado contra la lista v1 de docs/07; test que exige ausencia de `evaluate`/`execute_script`) |
| Browser restart recovery demostrado | **PASS** (`chrome://crash` real → contexto reconstruido → sesión sigue autenticada por storage state, sin repetir el login; fingerprint re-verificado tras el resume) |
| Artifact manifest consistente y con provenance verificable | **PASS** (hash/size en streaming, path con provenance, lectura que re-verifica el hash, oversize abortado sin dejar parcial) |
| No "latest artifact" lookup cross-run | **PASS** (`EvidenceSet` rechaza artifacts de otro run/set; un set contaminado no se construye) |
| Origin policy enforced | **PASS** (match exacto testeado contra subdominios, lookalikes, scheme y puerto; bloqueo verificado sobre Chromium real; una página de prompt injection no logra ampliar la policy) |

# Known Issues

- **El browser aún no está cableado a un run**: el gateway, la policy y el recovery existen y están probados, pero nada en el workflow los usa todavía. Ese cableado es exactamente Phase 05 (`run_episode` ejecutando el graph con el browser).
- No se capturan screenshots/traces automáticamente durante un run; `screenshot_bytes()` y el `ArtifactRepository` existen pero los llama el test, no el runtime.
- Los tests de integración (postgres, Temporal, Redis) hacen skip si el servicio no responde; `ci-local.sh` sólo falla ruidosamente por PostgreSQL.
- El fan-out de eventos falla en silencio por diseño: verificar Redis end-to-end, no sólo con la suite.
- La suite completa tarda ~50s por los tests de browser; considerar un marker para separarlos si molesta en bucles cortos.
- structlog pendiente (docs/14).

# Technical Debt

- No hay endpoints para `Environment` (la entidad y la tabla existen; los tests usan el default del project).
- No hay GET/listado de policies por API (sólo POST).
- `run_policy_id` es nullable en `runs` por compatibilidad; cuando no queden runs antiguos, considerar NOT NULL.
- `test-target-app` vive en `backend/tests/target_app/`; promoverlo a servicio compose si Phase 12/13 lo necesita fuera de los tests.
- `PageFingerprint` no incluye hash de DOM ni visual hash (docs/07 los menciona como opcionales); se añaden cuando el planner los necesite.
- Sin presence/heartbeat de workers, rate limits ni caches en Redis.
- WebSocket sin auth ni límite de conexiones (v1 local-first).

# Risks

- Phase 05 debe rellenar `run_episode` **sin** cambiar la forma del workflow (ADR 0009) y debe pasar el browser siempre envuelto (el test de arquitectura lo protege, pero sólo para imports; una instancia construida dentro de infrastructure y pasada hacia arriba lo esquivaría).
- Toda activity de Temporal invocada por nombre necesita `result_type` explícito.
- CI en Linux pendiente (Phase 13); todo se verifica en Windows contra contenedores Linux.

# Decisions Still Open

- Dónde vive el `evidence_set_id` de un run: generado por episodio, por step o por run (Phase 05 lo decidirá al capturar evidencia real).
- Si el checkpointer de LangGraph usa el mismo engine/pool que el resto o uno propio.
- Retención/purga de `run_events`, `idempotency_records` y artifacts (Phase 13).

# Graphify Status

- `graphify-out/graph.json` refrescado tras Phase 04 (code-only, incremental).

# Services That Are Working

- postgres (`6c4d6570f65c`), redis (locks, semáforos, streams), temporal + temporal-ui, falkordb, api (`http://localhost:8000/docs`, WebSocket `/ws/runs/{id}`), worker. Chromium disponible vía Playwright.

# Services Still Stubbed/Deferred

- `frontend` como servicio compose (Phase 10), `vllm` (06), `vllm-embed` (09), `airllm` (11).

# Exact Next Task

Implement Phase 05 slice 1: define the LangGraph agent state schema and its PostgreSQL-backed checkpointer, reconciling it with the domain `checkpoints` table exactly as ADR 0009 specifies (RecoveryPoint rows referencing a LangGraph checkpoint id plus browser recovery data), before adding any node — the resume path is what every later node depends on.

# Exact Next Command

En Claude Code: `/implement-phase 05`

# Recommended Skills For Next Session

- `implement-phase` (proceso), `ponytail` (always-on).
- `durability-review` (checkpoints, resume, uncertainty window) + `postgresql` (tablas de checkpoint).
- `backend-slice` y `error-handling-patterns`.
- `browser-runtime` cuando el graph empiece a conducir el browser.
- `architecture-guard` + `test-and-verify` al cierre.
