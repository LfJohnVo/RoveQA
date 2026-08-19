# Session Handoff

Última sesión: 2026-08-18 (Opus 5). **Phases 02, 03, 04, 05 y 06 completadas** en esta sesión, más la migración del pipeline a contenedores.

# Current Phase

07 — Story workflow (`plans/phase-07-*.md`). Phase 06 está DONE con sus 3 gates PASS.

# Phase Status

- Phases 00, 01, 02, 03, 04, 05, 06: **DONE**.
- Phase 07: **NOT_STARTED**. Hoy un run ejecuta un episodio con un goal por defecto; no hay derivación desde `UserStory` ni verdict real.

# Last Stable State

- Git branch `main`, working tree limpio salvo esta actualización de docs.
- `bash scripts/ci-local.sh` → **all green**: 324 tests backend (1 skip), 1 frontend, migraciones sin drift, build frontend, compose config.
- Stack corriendo: postgres, redis, temporal, temporal-ui, falkordb, api, worker. Schema en `f9911e78285a` (Phase 06 no añadió tablas).
- Todo gate corre en contenedores. En el host sólo hacen falta `docker compose` y `bash`.

# Architecture Decisions Made

Phase 06:

- **El Domain nombra capability, nunca modelos.** `TaskType` → `ModelCapability` → endpoint. `ModelRouter` se indexa por capability, así que Phase 09 (embeddings, `POOLING`) y Phase 11 (AirLLM, `DEEP`) registran endpoints sin tocar nada por encima. Una task sin endpoint falla tipada en vez de degradarse al modelo fast: una respuesta de root-cause servida por el modelo rápido parece bien y vale mucho menos.
- **Una decisión no obtenida es un tercer resultado.** `PlannedAction` distingue "haz esto" / "no hace falta nada más" / `failure`. Colapsar los dos últimos es cómo un servidor de modelos caído se convierte en un run que reporta éxito.
- **Fallo tipado, no excepción.** El gateway devuelve `PlannedAction(failure=...)` en vez de lanzar. Lanzar aparecería como crash de activity y dejaría que Temporal reintentara el episodio como fallo de infraestructura (ADR 0009).
- **`side_effect` lo decide el tipo de acción, no el modelo.** Todo lo que está fuera de `READ_ONLY_ACTIONS` se trata como state-changing aunque el modelo diga `false`; el flag sólo sirve para escalar (una navegación que confirma algo). Un modelo persuadido por contenido de página puede proponer mal una acción legal, nunca una ilegal.
- **El delimitador del prompt es una pista, no la frontera.** El texto de página puede intentar cerrar su propio bloque. Lo que contiene a un modelo persuadido está abajo y no se negocia: schema cerrado + `GuardedBrowserGateway` + RunPolicy.
- **Retries de transporte sólo en el cliente** (timeout, connection error, 5xx), acotados por `InferenceBudget`. Un 4xx no se reintenta: es una request que construimos mal y reenviarla manda los mismos bytes. Output inválido tampoco se reintenta ciegamente.
- **El circuit breaker cuenta fallos de transporte, no respuestas malas.** Un modelo que contesta mal está contestando; tumbar el endpoint por un problema de prompt no ayuda a nadie.
- **La concurrencia pertenece al servidor, no al llamador.** Semáforo Redis por endpoint, así que dos workers comparten el presupuesto de una GPU. Saturación sostenida → `ModelUnavailableError` con deadline; una cola sin deadline es un run que no termina y no dice por qué.
- **Una acción denegada por policy cierra el episodio, no se replanifica.** Pedirle al modelo otra ruta después de un rechazo es exactamente el comportamiento que la policy existe para impedir. `StepOutcome.DENIED` (que hasta ahora no producía nadie) distingue el caso de un fallo.
- **El allowlist de deserialización del checkpoint es explícito.** `CHECKPOINTED_TYPES` + `LANGGRAPH_STRICT_MSGPACK=true`. El default de la librería reconstruye cualquier tipo nombrado en la fila y sólo avisa.
- **El worker es el único que carga Playwright y modelo.** La API responde preguntas sobre runs; su imagen (`target: runtime`) no lleva Chromium. El worker usa `target: worker`.

# Files Created

Backend (Phase 06):

- `domain/inference/tasks.py` — `TaskType`, `ModelCapability`, `InferenceBudget`.
- `infrastructure/inference/`: `router.py`, `schemas.py`, `prompts.py`, `circuit.py`, `metrics.py`, `errors.py`
- `infrastructure/inference/vllm/`: `client.py` (transporte, timeouts, retry, circuito, semáforo, métricas), `gateway.py` (`ModelGateway`).
- `bootstrap/agent_runtime.py` — wiring worker-only de modelo + browser + checkpointer.
- Tests: `tests/inference/{test_schemas,test_router,test_client,test_gateway,test_concurrency,test_real_model}.py`, `tests/agent/test_checkpoint_serialization.py`

# Files Modified

- `application/ports/models.py`: `PlannedAction.failure` con invariante (una decisión fallida no lleva acción).
- `infrastructure/agent/langgraph/graph.py`: el nodo `plan` distingue fallo de "nada que hacer"; `act` captura `ActionDeniedError`; `verify` registra `DENIED` y cierra.
- `infrastructure/agent/langgraph/checkpointer.py`: `CHECKPOINTED_TYPES` + `build_serializer()`.
- `bootstrap/{settings,container}.py`: config de modelo, `with_agent_runtime`, cierre del cliente HTTP.
- `infrastructure/workflows/temporal/worker.py`: cablea el runtime.
- `backend/Dockerfile`: stage `worker` (runtime + Chromium).
- `compose.yaml`: `worker` en el stage nuevo con config de modelo y `LANGGRAPH_STRICT_MSGPACK`; `vllm` con `--model`/guided decoding, volumen de modelos, GPU y puerto 8100 (8000 ya es de la API).
- `backend/pyproject.toml`: `httpx` y `pydantic` pasan a dependencias de runtime.
- `.env.example`, `docs/05`, `docs/06`, `docs/08`.

# Database/Migrations State

- Sin migraciones nuevas en Phase 06. Head sigue en **`f9911e78285a`**; `alembic check` limpio.

# Tests Executed

```
bash scripts/ci-local.sh
docker compose --profile gates run --rm backend-tests pytest
docker compose --profile gates run --rm backend-tests pytest tests/inference/test_concurrency.py -v
docker compose run --rm -v <scratch>:/check worker python /check/wiring_check.py
docker compose exec -T api python  # e2e por la API real
```

# Exact Test Results

- **324 passed, 1 skipped** (el skip es el test opcional contra modelo real, sin `VLLM_BASE_URL`).
  - `tests/inference` 48 · `tests/domain` 63 · `tests/contracts` 80 · `tests/application` 21 · `tests/http` 29 · `tests/browser` 31 · `tests/agent` 27 · `tests/integration` 16 · `tests/architecture` 10 · `test_health` 2
- ruff "All checks passed!"; mypy strict "no issues found in 173 source files"; `alembic check` sin drift.
- `ci-local: all green`. Frontend: eslint, tsc, vitest 1 passed, build OK.
- e2e por la API con el stack reconstruido: `run: completed inconclusive`, eventos `['run.created', 'run.status.changed', 'run.status.changed']`.
- e2e en la imagen `worker` con un endpoint OpenAI-compatible de stub: 3 llamadas al modelo (navigate → click → finished), Chromium real, `safe_point=episode_closed` con checkpoint id.

# Acceptance Gates (Phase 06)

| Gate | Resultado |
| --- | --- |
| Invalid model output no llega a Playwright | **PASS** (graph real + browser recorder: prosa en vez de JSON, `action_type: evaluate`, click sin target y completion vacía → `executed == []` y episodio cerrado con motivo. Más: una acción propuesta por el modelo sigue pasando por la RunPolicy) |
| Concurrency limit demostrado | **PASS** (8 tests contra semáforo in-memory y Redis real: con capacity 1 y 2, 6 llamadas concurrentes nunca superan el pico declarado; dos clientes independientes comparten el presupuesto del endpoint; saturación con deadline reporta `ModelUnavailableError`) |
| Agent system test con modelo real opcional y fake obligatorio | **PASS** (fake obligatorio: `tests/inference/test_gateway.py` sobre el graph completo y `tests/agent/test_episode_activity.py` sobre la activity; real opcional: `tests/inference/test_real_model.py`, skip sin endpoint configurado) |

# Known Issues

- **Sin GPU disponible en esta máquina**: el path del modelo real está probado contra un servidor OpenAI-compatible de stub y con `httpx.MockTransport`, no contra vLLM. El tag `VLLM_MODEL` y el backend de guided decoding **no están validados en hardware**; hay que verificarlos en el host con GPU antes de fijarlos.
- `more_work` siempre es `False`: un episodio por goal. Multi-episodio llega con Phase 07.
- El `RecoveryPoint` sigue con `browser.url` vacío: el resultado del episodio no devuelve la URL observada.
- `EpisodeOutcome` no transporta `failure_reason`, así que el workflow cierra en `completed/inconclusive` incluso cuando el episodio falló o fue denegado. Es coherente con lo declarado (el verdict se deriva en Phase 07) pero es lo primero que Phase 07 debe arreglar.
- Los tests de integración hacen skip si el servicio no responde.
- La suite tarda ~65s.

# Technical Debt

- `open_checkpointer` abre y cierra conexión por episodio; con muchos episodios convendrá un pool.
- Los prompts viven en `infrastructure/inference/prompts.py` sin versionado explícito. En cuanto haya evals (docs/08) hará falta un identificador de versión de prompt en `model_invocation_id`.
- `model_invocation_id`, prompt/model version y `model_derived=true` en la evidencia (docs/08 "Evidence boundary") todavía no se persisten; hoy la decisión sólo lleva `rationale`.
- El nodo "Retrieve Memory" de docs/06 no existe (Phase 09), a propósito.
- Sin endpoints de `Environment`, sin GET de policies, sin presence/heartbeat en Redis.
- structlog pendiente (docs/14); las métricas de inferencia son contadores en proceso + una línea de log por llamada.

# Risks

- Phase 07 deriva el verdict de resultados reales. Hoy el workflow devuelve `inconclusive` fijo; cambiarlo toca la máquina de estados de `Run`, que ya prohíbe `COMPLETED` sin verdict.
- Un modelo real producirá mucha más variedad que el stub: conviene medir `invalid_outputs` (ya se cuenta aparte de `failures`) al integrar el primer modelo de verdad.
- Toda activity de Temporal invocada por nombre necesita `result_type` explícito.
- Si alguien añade un tipo nuevo al estado del graph sin ponerlo en `CHECKPOINTED_TYPES`, el resume se rompe. `tests/agent/test_checkpoint_serialization.py` lo detecta (verificado por mutación: vuelve como `dict`).

# Decisions Still Open

- Cómo se deriva el `goal` de un episodio desde la historia y sus acceptance criteria (Phase 07).
- Cómo se decide el verdict a partir de los resultados de episodios.
- Dónde se genera el `evidence_set_id` y cuándo el graph captura screenshots/traces.
- Estrategia de pooling para el checkpointer.

# Graphify Status

- `graphify-out/graph.json` de la sesión anterior; no refrescado tras Phase 06.

# Services That Are Working

- postgres (`f9911e78285a` + tablas de LangGraph), redis, temporal + temporal-ui, falkordb, api (`http://localhost:8000/docs`), worker. Chromium vía Playwright dentro de la imagen `worker`.

# Services Still Stubbed/Deferred

- `frontend` como servicio compose (Phase 10), `vllm` (definido bajo perfil `gpu`, sin validar en hardware), `vllm-embed` (09), `airllm` (11).

# Exact Next Task

Implement Phase 07 slice 1: derive an episode `goal` from a `UserStory` and its acceptance criteria instead of the declared default in `EpisodeParams`, so a run executes what the story asks for — the workflow shape and the retry split stay exactly as ADR 0009 fixed them.

# Exact Next Command

En Claude Code: `/implement-phase 07`

# Recommended Skills For Next Session

- `implement-phase` (proceso), `ponytail` (always-on).
- `backend-slice` + `api-design-principles` para los contratos de historia/verdict.
- `durability-review` al tocar el workflow.
- `architecture-guard` + `test-and-verify` al cierre.
