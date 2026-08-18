# Session Handoff

Última sesión: 2026-08-18 (Claude Fable 5). Auditoría de blueprint + Phase 00 completa.

# Current Phase
01 — Domain + PostgreSQL Foundation (`plans/phase-01-domain-postgres.md`). Phase 00 está DONE con todos los gates verdes.

# Phase Status
- Phase 00: **DONE** (todos los gates PASS, ver Acceptance Gates).
- Phase 01: **IN_PROGRESS** — slice 1 completado y commiteado: `backend/src/agentic_qa/domain/runs/run.py` (Run + RunStatus/Verdict state machine) con `backend/tests/domain/test_run_state_machine.py` (12 tests verdes, mypy strict verde). Sin ORM, Alembic, ports ni use cases todavía.

# Last Stable State
- Git branch `main`, working tree limpio. Historial: blueprint import → blueprint hardening → slices de Phase 00 (cada uno commiteado con checks verdes).
- `bash scripts/ci-local.sh` → **all green** (última ejecución de esta sesión).
- `docker compose down` ejecutado al cierre; los named volumes `roveqa_postgres_data` y `roveqa_falkordb_data` persisten.

# Architecture Decisions Made
- **ADR 0009 (nuevo)**: retry ownership single-owner (Temporal=infra, LangGraph Recover=semántico, cliente=transport), workflow shape (una activity por episodio con heartbeat, events persistidos desde activities, continue-as-new con umbral), reconciliación checkpoints dominio ↔ checkpointer LangGraph. Referenciado desde plans 02/05 y docs/05.
- Contratos v1 endurecidos ANTES de ser implementados (sin migración necesaria): MemoryContext lleva `observed`/`model_derived`/`validity`; knowledge-experience lleva `created_at`/`trusted`/`origin`/`policy_id`; run-policy lleva `max_model_calls` (required)/`upload_path_allowlist`/pattern de origins; failure-bundle lleva `failed_step_id` y guard anti path-traversal; agent-action cierra schema y exige safety fields si `side_effect=true`; `$id` en los 10 schemas.
- docs/02: `Verdict` es domain value separado de `RunStatus` con mapping definido.
- docs/12: resolución normativa de RunPolicy (plan → environment default → project default; sin policy resuelta no arranca run) y `plan_version` canónica content-hash para planes inline. `Idempotency-Key` es requerida en POST /runs.
- docs/13: matching exacto RFC 6454 de origins; credential handling por `credential_ref` resuelto sólo en el browser adapter; identity model v1 = local-first single-operator, tenant≡project.
- Python 3.13 pinned (uv); pnpm 10.34.5 pinned vía `packageManager` (root cause fix: corepack bajaba pnpm 11 en Docker).
- Imágenes pinneadas: postgres:16-alpine, redis:7-alpine, temporalio/auto-setup:1.29.7, temporalio/ui:2.53.3, falkordb/falkordb:v4.20.3.

# Files Created
- `backend/`: pyproject.toml, uv.lock, .python-version, Dockerfile, .dockerignore, `src/agentic_qa/` (árbol Clean Architecture completo, 36 `__init__.py`, sin lógica), `tests/test_health.py`.
- `frontend/`: scaffold Vite React-TS + package.json (ESLint 9 flat config, Vitest+RTL, jsdom), eslint.config.js, vite.config.ts (vitest env jsdom), `src/App.tsx` (shell mínimo), `src/App.test.tsx`, Dockerfile, .dockerignore, pnpm-lock.yaml.
- `compose.yaml` (raíz), `Makefile`, `scripts/ci-local.sh`, `.gitattributes`.
- `docs/adr/0009-run-workflow-shape-and-retry-ownership.md`.
- `graphify-out/graph.json` + `manifest.json` (code-only).
- `prompts/CONTINUE_WITH_OPUS_5.md`.

# Files Modified
- Contratos: memory-context, knowledge-experience, test-plan ($comment), run-policy (reescrito), failure-bundle, agent-action (reescrito), run-event/browser-action/user-story ($id).
- Docs: 02, 05, 12, 13, 25, 26; plans 02 y 05 (referencia ADR 0009).
- `.claude/settings.json` (deny .env acotado para que `.env.example` sea auditable), `scripts/validate-blueprint.sh` (10 contratos + ADR 0009), `.gitignore`, `docs/status/PROGRESS.md`.

# Database/Migrations State
- Sin schema de aplicación ni Alembic todavía (Phase 01 los crea).
- PostgreSQL del compose crea DB `agentic_qa` (user/pass dev `agentic`/`agentic`). Temporal auto-setup creó sus DBs `temporal`/`temporal_visibility` en el mismo PostgreSQL (persisten en el volumen).

# Docker State
- Stack: **down** al cierre; volúmenes `roveqa_postgres_data` y `roveqa_falkordb_data` persisten con datos de esta sesión.
- Levantar: `make up` (postgres, redis, temporal, temporal-ui, falkordb). Temporal UI: http://localhost:8233. FalkorDB mapeado a host 6380 (evita clash con redis 6379).
- Imágenes construidas y verificadas: `roveqa-backend:dev` (smoke-run imprime versión), `roveqa-frontend:dev` (nginx estático). No están en compose todavía (sus servicios llegan en Phases 02/10).
- vllm/vllm-embed existen tras profiles `gpu`/`memory-gpu` sin modelo pinneado (Phases 06/09).

# Tests Executed
```
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
cd frontend && pnpm lint && pnpm typecheck && pnpm test && pnpm build
bash scripts/validate-blueprint.sh
bash scripts/ci-local.sh
docker compose config --quiet
docker compose up -d postgres redis temporal temporal-ui falkordb
docker exec roveqa-falkordb-1 redis-cli GRAPH.QUERY phase00_check "CREATE (:Probe {id:'p00'})" ; docker compose restart falkordb ; GRAPH.QUERY MATCH → devolvió p00 ; GRAPH.DELETE
docker build backend/ ; docker run --rm roveqa-backend:dev ; docker build frontend/
graphify . --code-only ; graphify explain "agentic_qa"
```

# Exact Test Results
- Backend: ruff "All checks passed!", format "37 files already formatted", mypy strict "Success: no issues found in 36 source files", pytest "2 passed".
- Frontend: eslint sin findings, tsc -b limpio, vitest "1 passed (1)", build OK (dist ~190KB js).
- `ci-local.sh`: "ci-local: all green" (dos ejecuciones, incluida la final).
- Compose: config OK; estados `healthy` en postgres/redis/temporal/falkordb; temporal-ui `running` (sin healthcheck definido, es UI stateless).
- FalkorDB: probe graph sobrevivió `docker compose restart falkordb` (persistencia real del volumen probada).
- Backend image smoke: "agentic_qa 0.1.0 image OK".
- Graphify: graph.json 943 nodos / 941 edges / 109 comunidades; `graphify explain "agentic_qa"` resuelve el paquete y sus importadores.

# Acceptance Gates (Phase 00)
| Gate | Resultado |
|---|---|
| Backend import/health test verde | **PASS** (pytest 2 passed; mypy/ruff también verdes) |
| Frontend unit smoke test + build verde | **PASS** (vitest 1 passed; build OK) |
| `docker compose config` válido | **PASS** |
| Dependencies básicas levantan con healthchecks | **PASS** (4/4 servicios con healthcheck healthy; temporal-ui running) |
| FalkorDB named volume persistente y arranca vacío | **PASS** (volumen montado en su data dir real; arrancó vacío healthy; persistencia probada tras restart) |
| No business logic ni fake architecture | **PASS** (sólo packages vacíos pedidos por el plan; App shell mínimo; grep de imports infra en domain/application limpio) |
| Graphify graph.json + query documentada | **PASS con limitación** (code-only; extracción semántica de docs requiere LLM API key — skip explícito, ver Known Issues) |

# Known Issues
- Graphify indexó sólo código (61 archivos). Los 106 docs necesitan un LLM API key (`GEMINI_API_KEY`/`ANTHROPIC_API_KEY`/...); cuando haya uno disponible, correr `graphify update .` sin `--code-only` para el grafo completo.
- `temporal-ui` no tiene healthcheck (no expone endpoint de health trivial en la imagen); depende de `temporal` que sí lo tiene.
- Auditoría: las dimensiones architecture/coherence del workflow fallaron por límite de gasto de subagentes y se completaron inline (validate-blueprint + cross-ref grep + lectura de ADRs); cobertura equivalente pero menos profunda que las otras 4 dimensiones.

# Technical Debt
- IMPORTANT de auditoría documentados pero deliberadamente NO resueltos aún (les toca en su fase): schemas para result.json/steps.json del bundle (Phase 07/08), endpoints de memory admin en docs/12 (nota añadida, definición completa en Phase 09), RunPolicy `allowed_action_classes` explícitos (v1 usa los booleans destructive/upload/download documentados en docs/13).
- `frontend/index.css` conserva estilos del template Vite (se reemplazan en Phase 10 con el design system).
- Enforcement automático de "Domain no importa infra" es un grep manual; Phase 01 debe añadir un test de arquitectura (p.ej. import-linter o test propio).

# Risks
- Compatibilidad GPU/modelos vLLM/AirLLM sin validar en el host destino (pin de imágenes/modelos en Phases 06/09/11).
- Temporal 1.29.7 + UI 2.53.3: pairing verificado sólo en cuanto a arranque healthy; validar operaciones reales de workflow en Phase 02.
- Desarrollo en Windows host + runtime Linux en Docker: los checks locales corren en Windows; CI real debería correr también en Linux (Phase 13 hardening).

# Decisions Still Open
- Elección de modelos concretos vLLM generation/embedding y AirLLM (Phases 06/09/11, requieren el host GPU real).
- Estrategia de auth de plataforma post-v1 (reservada; requiere ADR).
- Si `run diff` se queda client-side o se promueve a Application query (docs/12 lo deja evolucionar).

# Graphify Status
- Instalado (graphifyy v0.9.31, uv tool + pip). `graphify-out/graph.json` commiteado (code-only, 943 nodos). Query verificada: `graphify explain "agentic_qa"`. Refrescar con `make graphify-refresh` tras cambios estructurales; el grafo completo con docs queda pendiente de un LLM API key.

# Services That Are Working
- postgres:16-alpine (healthy, volumen persistente, DBs de Temporal creadas).
- redis:7-alpine (healthy).
- temporalio/auto-setup:1.29.7 (healthy vía `temporal operator cluster health`).
- temporalio/ui:2.53.3 (running, http://localhost:8233).
- falkordb v4.20.3 (healthy, módulo graph 42003, persistencia probada).

# Services Still Stubbed/Deferred
- `api`, `worker` (Phase 02), `frontend` como servicio compose (Phase 10), `vllm` (Phase 06), `vllm-embed` (Phase 09), `airllm` (Phase 11), `test-target-app` (Phase 04/15 fixtures).

# Exact Next Task
Implement Phase 01 slice 2: Project/UserStory domain entities plus the repository ports (`RunRepository`, `ProjectRepository`, `StoryRepository` as Protocols in `backend/src/agentic_qa/application/ports/`), with fake in-memory implementations exercised by repository contract tests, before touching SQLAlchemy or Alembic.

# Exact Next Command
En Claude Code: `/implement-phase 01` (la skill detecta el slice 1 ya hecho vía este HANDOFF y continúa con el slice 2)

# Recommended Skills For Next Session
- `implement-phase` (proceso de fase), `ponytail` (always-on).
- `backend-slice` + `postgresql` (dominio + adapters + Alembic).
- `error-handling-patterns` (mapping de fallos DB/transacciones).
- `architecture-guard` + `test-and-verify` al cierre.
- `graphify` para orientación (grafo fresco de esta sesión).
