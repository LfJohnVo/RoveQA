# Session Handoff

Última sesión: 2026-08-19 (Opus 5). **Phases 02-08 completadas**, más la migración del pipeline a contenedores y la validación de vLLM sobre GPU real.

# Current Phase

09 — Knowledge/memory graph (`plans/phase-09-knowledge-memory.md`). Phase 08 está DONE: 7/7 gates PASS y los 14 comandos v1 implementados.

# Phase Status

- Phases 00 – 08: **DONE**.
- Phase 09: **NOT_STARTED**. No existe adapter de Graphiti/FalkorDB ni knowledge candidates; `docs/26-adaptive-learning-graph.md` y `.claude/rules/knowledge.md` fijan las reglas antes de escribir código.

# Last Stable State

- Git branch `main`.
- `bash scripts/ci-local.sh` → **all green**: 379 tests backend (1 skip), 103 CLI, 1 frontend, migraciones sin drift, build frontend, compose config.
- Stack: postgres, redis, temporal, temporal-ui, falkordb, api, worker. Schema en `27a82f4f015d`.
- La suite usa su propia base `agentic_qa_test`. Antes compartía la de la aplicación y la borraba en cada corrida; el síntoma ("mi proyecto desapareció") no se parecía en nada a la causa.
- vLLM sirviendo `Qwen/Qwen3-4B-Instruct-2507` bajo el perfil `gpu` (RTX 5060 Ti 16GB, sm_120).
- Todo gate corre en contenedores. En el host sólo hacen falta `docker compose` y `bash`.

# Architecture Decisions Made

Cierre de deuda antes de Phase 09:

- **La evidencia se captura mientras la página existe.** El graph pide un screenshot antes de juzgar los criterios, lo guarda por el `ArtifactRepository` y devuelve refs; **la activity los indexa** en PostgreSQL. Misma regla que ADR 0009: los nodos deciden, la activity persiste. Un fallo de captura nunca tumba el run — la evidencia vale tenerla y no vale perder una ejecución por ella.
- **Un evidence set por episodio** (`{run_id}-e{index}`), derivado y no elegido: un bundle no puede mezclar dos, y derivarlo lo garantiza sin que nadie tenga que acordarse.
- **La acción `SCREENSHOT` capturaba nada y reportaba éxito.** Era una mentira dentro del action set cerrado sobre la que el agente podía actuar.
- **`model_invocation_id`, modelo y `prompt_version` viajan con la conclusión** (docs/08). Una hipótesis que no puede nombrar su origen no es reproducible ni comparable, y una eval que cambia un prompt no podría distinguir sus resultados de los de la redacción anterior. El dominio prohíbe que un resultado determinista nombre una invocación de modelo.
- **`GET /api/v1/meta/contracts`** expone las versiones que habla el servidor. `doctor` las compara y reporta un desajuste en vez de adaptarse: una CLI que se adapta en silencio produce salida cuyo significado depende de a qué servidor llegó. Un servidor demasiado antiguo para responder se reporta como *no verificable*, que no es lo mismo que compatible.

Phase 08 (CLI):

- **Un solo sitio escribe stdout, y escribe exactamente un valor JSON.** Emitir dos veces lanza en vez de producir dos valores que nadie puede parsear. Todo diagnóstico va a stderr, así que un warning que el comando quiere imprimir de verdad no puede corromper lo que un agente parsea.
- **Los exit codes distinguen una respuesta de su ausencia.** `1` es un verdict terminal no-pass; `7` es un timeout de espera con el run todavía vivo. Colapsarlos dejaría que CI registre un fallo por un run que después pasó.
- **Esperar no es poseer.** Ctrl-C y el deadline del cliente desacoplan y dicen cómo retomar; sólo `run cancel` para un run.
- **Una mutación se reintenta sólo con Idempotency-Key, y reusa la misma en cada intento.** Un retry sin key es cómo una respuesta perdida se convierte en dos runs. Un 409 es una respuesta y no se reintenta.
- **Las responses se validan en runtime, no se castean.** Un verdict desconocido se rechaza porque el exit code se deriva de él y un valor no reconocido se volvería "no pasó" en silencio.
- **Un bundle está completo o visiblemente incompleto.** Se escribe en un directorio de staging con marcador `.partial` desde el primer byte, el manifest va al final, y sólo entonces se promociona con un rename. Un fallo deja el staging como evidencia y **no** destruye el bundle anterior.
- **La provenance se comprueba antes de escribir un byte**: todo artifact debe nombrar el mismo `run_id` y `evidence_set_id` que el manifest. Un bundle que mezcla el screenshot de este run con el trace de otro se lee como coherente y no lo es.
- **El plan importado se versiona por content hash** (docs/12): los mismos bytes son la misma versión, así que enviar un plan es idempotente sin key.
- **`run rerun` copia la versión de plan del run fuente** en vez de re-resolverla: reejecutar un fallo tiene que ejecutar el mismo plan.
- **Un artifact id es un identificador, nunca un path**, y el repositorio verifica el hash al leer.
- **`doctor` sale 8 con la API caída**, no 0 con un problema listado: un doctor que triunfa mientras reporta un setup roto es uno que CI no puede usar.

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

CLI (Phase 08), en `cli/`:

- `src/main.ts` (dispatcher y único escritor de stdout), `src/config.ts`, `src/errors.ts`
- `src/output/{envelope,exit-codes}.ts`, `src/contracts/schemas.ts`
- `src/client/api.ts` (retry/idempotencia/timeouts/bytes), `src/bundle/materialize.ts`
- `src/commands/{plan,run,doctor,setup}.ts`
- Tests: `test/{envelope,config,run,bundle,boundaries,detach}.test.ts`

Backend (Phase 08):

- `application/commands/import_plan.py` (content-hash versioning)
- `application/queries/failure_context.py`, `interfaces/http/routers/artifacts.py`
- `alembic/versions/00dfb54608c5_phase_08_artifacts_index.py` (tabla `artifacts`)
- `infra/postgres/init-test-db.sql`

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

- Migraciones: … → `603bec952128` → `0f1607fa06e7` → `00dfb54608c5` (`artifacts`) → **`27a82f4f015d`** (provenance de modelo en `criterion_results`). `alembic check` limpio.
- **La migración de Phase 05 borraba las tablas de LangGraph.** Autogenerate las capturó antes de que `alembic/env.py` las excluyera. En una base vacía los drops fallan y la cadena entera no se puede aplicar: una instalación nueva era imposible, y sobre una existente el upgrade destruía el estado de resume de cualquier run en vuelo. Eliminados de esa migración (no estaba desplegada en ningún sitio) y añadido `tests/integration/test_migrations_from_empty.py`, que aplica la cadena completa a una base desechable en cada corrida y prohíbe que una migración nombre una tabla de la librería.
- La suite migra su propia base con `POSTGRES_DSN=$POSTGRES_TEST_DSN alembic upgrade head`: fiarse de `create_all` la dejaba en el schema de cuando se creó una tabla, y una columna nueva nunca aparecía.
- La tabla `artifacts` guarda **referencias** (identidad, provenance, hash, tamaño); los bytes siguen en el filesystem (docs/11).

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

# Acceptance Gates (Phase 08)

| Gate | Resultado |
| --- | --- |
| Un agente puede `plan lint → run create → run wait → run failure → rerun` sólo con salida machine-readable | **PASS** (verificado contra el stack vivo, arrancando desde `.roveqa/config.json` escrito por `setup`) |
| Ningún comando invoca Playwright/vLLM/AirLLM/PostgreSQL/Redis/Temporal | **PASS** (`test/boundaries.test.ts` escanea imports estáticos, dinámicos y `require`, además de las dependencias declaradas, y se verifica contra una violación plantada) |
| Matar la CLI durante `run wait` deja el run intacto | **PASS** (subprocess real + SIGINT: sale 7, imprime "detaching" en stderr y el stub no recibe ningún cancel) |
| Un retry duplicado no crea side effects duplicados | **PASS** (la key se reusa entre intentos; un 409 no se reintenta) |
| Los tests de FailureBundle rechazan identidades mezcladas | **PASS** (run distinto y evidence set distinto, ambos rechazados antes de escribir un byte) |
| `--output json` emite exactamente un valor parseable en todo camino | **PASS** (éxito, error, y con un warning que el comando sí quiere imprimir; validado contra `cli-envelope.schema.json`) |
| Planes y bundles hacen round-trip por sus schemas | **PASS** |

# Acceptance Gates (Phase 07)

| Gate | Resultado |
| --- | --- |
| Una story conocida pasa/falla de forma reproducible | **PASS** (e2e real: PostgreSQL, checkpointer LangGraph, Chromium y target app. La misma story se ejecuta dos veces y pasa las dos; con una expectativa que la página no confirma, falla nombrando `ac-created` y apuntando a `assert-ac-created`) |
| El TestPlan valida contra su schema y exporta/importa losslessly | **PASS** (validación contra `contracts/test-plan.schema.json` montado read-only, no una copia; round trip por JSON conservando el tipo de los valores de metadata; versión de contrato desconocida rechazada) |
| Cada failed criterion apunta a evidence/action timeline del mismo run | **PASS** (`criterion_results` con FK a `runs`, único por `(run_id, criterion_id)`, y `step_id` apuntando al plan step) |
| Report no depende del transcript completo del LLM | **PASS** (`build_run_report` lee run + plan version + resultados; el documento separa `deterministic_observation` de `root_cause_hypothesis`) |
| Un plan malo termina blocked/inconclusive en vez de culpar al producto | **PASS** (e2e con criterio sin ancla determinista → inconclusive, `defects == ()`; más 9 tests de `derive_verdict` cubriendo cada `FailureKind`) |

# Known Issues

- `run diff` y `run flaky` no consultan un resumen semántico (el plan lo permite como paso posterior al delta determinista; v1 no tiene summarizer).
- `run flaky` ejecuta las réplicas en serie. Es lo honesto —réplicas concurrentes interactúan por el estado de la app bajo prueba— pero significa que `--count 20` tarda 20 runs.
- `more_work` sigue siendo `False`: un episodio por plan. Un plan que necesite varios episodios llega cuando exista el motivo.
- `POST /api/v1/plans` con plan inline, `GET /plans/{id}`, `PUT` con `If-Match` y `POST /plans/validate` están documentados y no implementados (docs/12 los marca).
- Los tests de integración hacen skip si el servicio no responde.
- La suite tarda ~60s; el e2e de story añade ~15s por su Chromium.

# Technical Debt

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

Implement Phase 09 slice 1: persist durable `KnowledgeCandidate` rows in PostgreSQL from a finished run's verified outcomes, with provenance and reliability, **before** any Graphiti/FalkorDB adapter exists — the graph is a rebuildable projection (`.claude/rules/knowledge.md`), so the durable side has to come first or there is nothing to rebuild from.

# Exact Next Command

En Claude Code: `/implement-phase 09`

# Recommended Skills For Next Session

- `implement-phase` (proceso), `ponytail` (always-on).
- `adaptive-memory-graph` + `postgresql` (Phase 09 los exige), y `prompt-engineering-patterns` si toca extraction/embeddings.
- `test-and-verify` + `architecture-guard` al cierre.
