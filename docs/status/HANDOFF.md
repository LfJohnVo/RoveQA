# Session Handoff

Última sesión: 2026-08-19 (Opus 5). **Phases 02, 03, 04, 05, 06 y 07 completadas** en esta sesión, más la migración del pipeline a contenedores y la validación de vLLM sobre GPU real.

# Current Phase

08 — Agent-first CLI (`plans/phase-08-agent-first-cli.md`). Phase 07 está DONE con sus 5 gates PASS.

# Phase Status

- Phases 00, 01, 02, 03, 04, 05, 06, 07: **DONE**.
- Phase 08: **NOT_STARTED**. No existe la CLI `roveqa`; los contratos que consume (`TestPlan`, endpoints de run y report) ya están publicados.

# Last Stable State

- Git branch `main`.
- `bash scripts/ci-local.sh` → **all green**: 370 tests backend (1 skip), 1 frontend, migraciones sin drift, build frontend, compose config.
- Stack: postgres, redis, temporal, temporal-ui, falkordb, api, worker. Schema en `0f1607fa06e7`.
- vLLM sirviendo `Qwen/Qwen3-4B-Instruct-2507` bajo el perfil `gpu` (RTX 5060 Ti 16GB, sm_120).
- Todo gate corre en contenedores. En el host sólo hacen falta `docker compose` y `bash`.

# Architecture Decisions Made

Phase 07:

- **El plan dice qué verificar, no cómo hacer clic.** La compilación story→plan es determinista y sin modelo, que es lo que hace reproducible "una story conocida pasa o falla". El agente decide las acciones en runtime; lo que sobrevive es el enlace `criterion_id -> step`, sin el cual un run fallido puede decir "algo se rompió" pero no "este criterio no se cumple".
- **Sólo un check determinista puede acusar al producto.** Un `verification_hint` es el literal que la página debe contener y produce un `CriterionResult` reproducible; sin hint se pregunta a un modelo y su respuesta queda etiquetada `model_derived`, lo que deja el run inconclusive. La primera vez que este sistema culpe a un producto por algo que sólo creyó un modelo, todos los reportes posteriores se leen con sospecha.
- **`FailureKind` decide qué puede concluir el run.** Sólo `product` justifica `failed`; environment/policy/agent_budget/model dan `blocked`; plan/unknown dan `inconclusive`. Un criterio sin resultado nunca cuenta como cumplido.
- **El objective que recibe el planner excluye las assertions.** Un agente al que se le dice "la página de confirmación muestra un número de pedido" puede navegar a una página que lo muestre sin haber hecho el pedido.
- **La versión del plan se fija al crear el run**, como la policy. Un run terminado bajo la versión 3 no cambia de resultado cuando se publica la 4; la activity lee la versión registrada, nunca "la última".
- **El verdict se deriva en la activity, desde filas durables**, y sólo el valor cruza a Temporal. Copiar los resultados al history lo haría crecer por episodio, y un verdict calculado desde datos que el workflow nunca vio no podría re-derivarse cuando alguien cuestione el reporte.
- **Los criterios se evalúan con el browser todavía abierto**, al cerrar el episodio: juzgar después sería juzgar una captura en vez de la aplicación.
- **El reporte no depende de ningún transcript de modelo** y separa `deterministic_observation` de `root_cause_hypothesis` en claves distintas, para que un consumidor filtre por clave y no por convención.

GPU/vLLM:

- `--guided-decoding-backend` **no existe** en vLLM 0.27; es `--structured-outputs-config`, cuyo backend por defecto (`auto`) resuelve a xgrammar. La compose anterior no habría arrancado.
- Docker Desktop ejecuta bajo WSL2, donde vLLM desactiva pinned memory por defecto; su worker GPU asigna buffers UVA y muere con "UVA is not available". Se habilita con `VLLM_WSL2_ENABLE_PIN_MEMORY=1`, que vLLM sólo permite en kernels WSL2 >= 4.19.121 (este host: 6.6).

# Files Created

Backend (Phase 07):

- `domain/qa/test_plan.py` — `TestPlan`, `PlanStep`, `PlanBudget`, `compile_story`, `objective`.
- `domain/qa/verification.py` — `CriterionResult`, `FailureKind`, `derive_verdict`.
- `application/contracts/test_plan.py` — documento portable (export/import lossless).
- `application/commands/compile_plan.py`, `application/ports/plans.py`, `application/ports/results.py`
- `application/services/criterion_verification.py`, `application/queries/run_report.py`
- `interfaces/http/routers/plans.py` — stories + plans.
- `alembic/versions/603bec952128_phase_07_test_plans.py`, `alembic/versions/0f1607fa06e7_phase_07_criterion_results.py`
- Tests: `tests/qa/{test_test_plan,test_verification,test_criterion_verification,test_story_run_e2e}.py`

# Files Modified

- `domain/runs/run.py`: `plan_id`/`plan_version` con invariante de identidad completa.
- `application/ports/models.py`: `judge()` + `JudgementRequest`/`CriterionJudgement`.
- `application/commands/start_run.py`: resuelve y fija la versión del plan.
- `infrastructure/agent/langgraph/graph.py`: nodo `verify_criteria` antes de cerrar el episodio.
- `infrastructure/agent/langgraph/checkpointer.py`: los tipos de verificación entran en `CHECKPOINTED_TYPES`.
- `infrastructure/workflows/temporal/{activities,contracts,workflows}.py`: goal desde el plan, resultados persistidos, verdict real.
- `infrastructure/inference/vllm/gateway.py` + `prompts.py`: judgement con structured output.
- `infrastructure/persistence/postgres/{models,mappers,repositories,unit_of_work}.py`: `test_plans` y `criterion_results`.
- `interfaces/http/{app,schemas}.py`, `routers/runs.py`: endpoints de plan y `GET /runs/{id}/report`.
- `compose.yaml`: servicio `vllm` validado en GPU; `contracts/` montado read-only en `backend-tests`.
- `docs/02`, `docs/12`.

# Database/Migrations State

- Migraciones: … → `f9911e78285a` → `603bec952128` (`test_plans` + `runs.plan_id/plan_version`) → **`0f1607fa06e7`** (`criterion_results`). `alembic check` limpio.

# Tests Executed

```
bash scripts/ci-local.sh
docker compose --profile gates run --rm backend-tests pytest
docker compose --profile gates run --rm -e VLLM_BASE_URL=http://vllm:8000 -e VLLM_MODEL=Qwen/Qwen3-4B-Instruct-2507 backend-tests pytest tests/inference/test_real_model.py -v
docker compose --profile gpu up -d vllm
```

# Exact Test Results

- **370 passed, 1 skipped** (el skip es el test de modelo real cuando no hay endpoint configurado).
  - `tests/qa` 46 · `tests/inference` 48 · `tests/domain` 63 · `tests/contracts` 80 · `tests/application` 21 · `tests/http` 29 · `tests/browser` 31 · `tests/agent` 27 · `tests/integration` 16 · `tests/architecture` 10 · `test_health` 2
- ruff "All checks passed!"; mypy strict "no issues found in 188 source files"; `alembic check` sin drift.
- `ci-local: all green`. Frontend: eslint, tsc, vitest 1 passed, build OK.
- **Modelo real**: `tests/inference/test_real_model.py` pasa contra vLLM vivo en la RTX 5060 Ti (1 passed en 4.61s).

# Acceptance Gates (Phase 07)

| Gate | Resultado |
| --- | --- |
| Una story conocida pasa/falla de forma reproducible | **PASS** (e2e real: PostgreSQL, checkpointer LangGraph, Chromium y target app. La misma story se ejecuta dos veces y pasa las dos; con una expectativa que la página no confirma, falla nombrando `ac-created` y apuntando a `assert-ac-created`) |
| El TestPlan valida contra su schema y exporta/importa losslessly | **PASS** (validación contra `contracts/test-plan.schema.json` montado read-only, no una copia; round trip por JSON conservando el tipo de los valores de metadata; versión de contrato desconocida rechazada) |
| Cada failed criterion apunta a evidence/action timeline del mismo run | **PASS** (`criterion_results` con FK a `runs`, único por `(run_id, criterion_id)`, y `step_id` apuntando al plan step) |
| Report no depende del transcript completo del LLM | **PASS** (`build_run_report` lee run + plan version + resultados; el documento separa `deterministic_observation` de `root_cause_hypothesis`) |
| Un plan malo termina blocked/inconclusive en vez de culpar al producto | **PASS** (e2e con criterio sin ancla determinista → inconclusive, `defects == ()`; más 9 tests de `derive_verdict` cubriendo cada `FailureKind`) |

# Known Issues

- `more_work` sigue siendo `False`: un episodio por plan. Un plan que necesite varios episodios llega cuando exista el motivo.
- `evidence_refs` de `CriterionResult` existe y nadie lo llena todavía: los artifacts de Phase 04 no están enlazados a los resultados. Es lo que falta para que el gate de evidencia sea completo y no sólo trazable por `step_id`/`run_id`.
- El `RecoveryPoint` sigue con `browser.url` vacío.
- `POST /api/v1/plans` con plan inline, `GET /plans/{id}`, `PUT` con `If-Match` y `POST /plans/validate` están documentados y no implementados (docs/12 los marca).
- Los tests de integración hacen skip si el servicio no responde.
- La suite tarda ~60s; el e2e de story añade ~15s por su Chromium.

# Technical Debt

- Los prompts no tienen versión explícita; hace falta antes de las evals de docs/08.
- `model_invocation_id` y prompt/model version no se persisten con las conclusiones del modelo (docs/08 "Evidence boundary").
- `open_checkpointer` abre y cierra conexión por episodio.
- El nodo "Retrieve Memory" de docs/06 no existe (Phase 09), a propósito.
- Sin endpoints de `Environment` ni GET de policies.
- structlog pendiente (docs/14).

# Risks

- La primera imagen de vLLM son 37.5GB y el modelo se descarga en el primer arranque: el `start_period` del healthcheck es 600s por eso. Un arranque en frío no es un fallo.
- El perfil `gpu` reserva la GPU entera; correr vLLM y el gate de browser a la vez compite por memoria de la máquina.
- Toda activity de Temporal invocada por nombre necesita `result_type` explícito.
- Un tipo nuevo en el estado del graph que falte en `CHECKPOINTED_TYPES` rompe el resume; `tests/agent/test_checkpoint_serialization.py` lo detecta.

# Decisions Still Open

- Cómo se enlazan artifacts/evidence_set a cada `CriterionResult`.
- Si un plan debe poder pedir varios episodios y qué los delimita.
- Dónde se genera el `evidence_set_id` y cuándo el graph captura screenshots/traces.
- Estrategia de pooling para el checkpointer.

# Graphify Status

- `graphify-out/graph.json` desactualizado (anterior a Phase 06). Refrescar antes de fiarse de él.

# Services That Are Working

- postgres (`0f1607fa06e7` + tablas de LangGraph), redis, temporal + temporal-ui, falkordb, api, worker, vllm (perfil `gpu`). Chromium vía Playwright en la imagen `worker`.

# Services Still Stubbed/Deferred

- `frontend` como servicio compose (Phase 10), `vllm-embed` (09), `airllm` (11).

# Exact Next Task

Implement Phase 08 slice 1: a `roveqa run` command that starts a run through the public HTTP API and prints a single JSON envelope on stdout, with progress and warnings on stderr — the CLI is another delivery adapter and may not import Playwright, Temporal, LangGraph or the database.

# Exact Next Command

En Claude Code: `/implement-phase 08`

# Recommended Skills For Next Session

- `implement-phase` (proceso), `ponytail` (always-on).
- `api-design-principles` (contrato CLI, exit codes, JSON purity) + `error-handling-patterns`.
- `test-and-verify` + `architecture-guard` al cierre.
