# Continue RoveQA with Opus 5

Instrucción autosuficiente para la siguiente sesión. Estado al cierre de la sesión anterior (2026-08-19): **Phases 00-08 DONE** (Phase 08: 7/7 gates PASS y los 14 comandos v1). vLLM validado sobre GPU real (RTX 5060 Ti); todo el pipeline corre en contenedores. 372 tests backend + 100 CLI verdes. Siguiente: Phase 09 (knowledge/memory graph).

## Pasos obligatorios, en orden

1. Lee `CLAUDE.md` completo. Sus invariantes de arquitectura, durabilidad, seguridad y skills routing gobiernan toda la sesión.
2. Lee `docs/status/PROGRESS.md` (estado por fase con evidencia).
3. Lee `docs/status/HANDOFF.md` completo — contiene decisiones tomadas, comandos ejecutados con resultados reales, gates PASS, known issues, deuda y riesgos.
4. Consulta Graphify si está disponible: existe `graphify-out/graph.json` pero **no incluye Phases 06-07**. Refréscalo (`graphify update .`) antes de fiarte de él, o verifica el source directamente. El grafo NO incluye docs (falta LLM API key); no lo fuerces.
5. Verifica el last stable state antes de cambiar nada:
   ```bash
   make up
   make migrate
   bash scripts/ci-local.sh
   ```
   `make up` va primero: desde Phase 01 el gate incluye migraciones y falla si PostgreSQL no está arriba. Todo corre en contenedores; en el host sólo hacen falta `docker compose` y `bash`. `ci-local.sh` debe terminar en "ci-local: all green" (372 backend + 100 CLI, ~90s). Si algo está rojo, aplica `systematic-debugging` antes de continuar; no asumas que lo rompiste tú ni lo "arregles" a ciegas.
6. Continúa EXACTAMENTE desde el `Exact Next Task` del HANDOFF:
   > Implement Phase 09 slice 1: persist durable `KnowledgeCandidate` rows in PostgreSQL from a finished run's verified outcomes, with provenance and reliability, **before** any Graphiti/FalkorDB adapter exists — the graph is a rebuildable projection, so the durable side has to come first or there is nothing to rebuild from.
   Phases 00-08 están cerradas: dominio, persistencia, API, Temporal, eventos, Redis, RunPolicy, browser gateway con recovery, agent graph con checkpointer y resume, inferencia vLLM con structured outputs, TestPlan + verificación de criterios + verdict + reporte, y la CLI agent-first completa en `cli/` con 100 tests. No las rehagas. Lee `plans/phase-09-knowledge-memory.md`, `docs/26-adaptive-learning-graph.md` y `.claude/rules/knowledge.md`.
7. **No repitas side effects**: el stack compose ya se levantó y validó (volúmenes `roveqa_postgres_data`/`roveqa_falkordb_data` persisten); las imágenes `roveqa-api`/`roveqa-worker`/`roveqa-backend-tests` ya compilan y corren. No re-crees nada de eso salvo que un check demuestre que está roto. No hagas `docker compose down -v` (destruiría datos de Temporal).
8. **No avances de fase sin gates verdes**. Al cerrar: `/test-and-verify 09`, `/architecture-guard`, actualizar `PROGRESS.md` y `HANDOFF.md`, y DETENTE — no empieces Phase 10 sin instrucción explícita del usuario.
9. Sigue usando todas las skills y reglas del proyecto: `ponytail` always-on, routing según `docs/21-claude-skill-routing.md`, `.claude/rules/*` por path, ADR para toda decisión estructural nueva. Los vigentes son ADR 0009 (retry ownership / workflow shape) y ADR 0010 (transaction ownership); no los contradigas.

## Contexto crítico que no debes redescubrir

- Los contratos v1 en `contracts/` fueron endurecidos ANTES de implementarse (memory labels, RunPolicy resolution, Verdict, failed_step_id, path-traversal guard). Impleméntalos tal como están; cambiarlos requiere versionado explícito.
- `Verdict` y `RunStatus` ya están modelados con su mapping (`docs/02-domain-model.md`) y defendidos por CHECK constraints.
- **Sólo un check determinista puede acusar al producto.** `FailureKind.PRODUCT` es el único que justifica `failed`; una duda de modelo deja el run inconclusive. No lo relajes para hacer verde un reporte.
- **La versión del plan se fija al crear el run.** Ni la activity ni el reporte resuelven "la última": leen `run.plan_id/plan_version`.
- El `verification_hint` de un criterio es el literal que la página debe contener; su ausencia manda el criterio al modelo y por tanto a inconclusive.
- **Commands reciben `UnitOfWork` y commitean; queries reciben el repository** (ADR 0010). Persistir y commitear va SIEMPRE antes de cualquier side effect externo.
- **El fan-out de eventos es best-effort y falla en silencio por diseño.** Un cambio de configuración de Redis puede romperlo sin poner ningún test en rojo: verifica end-to-end (`XLEN stream:run:{id}`), no sólo con la suite.
- Toda activity de Temporal invocada por nombre necesita `result_type` explícito, o el converter devuelve un dict y la anotación de retorno miente.
- **Un run no arranca sin RunPolicy resuelta** y las policies son inmutables. Cualquier test que arranque un run debe sembrar una: usa `seed_project_with_default_policy` / `DEFAULT_POLICY_PAYLOAD` de `tests/conftest.py`.
- **`destructive_actions: false` significa run de sólo lectura, no "sin borrados".** Todo lo que no está en `READ_ONLY_ACTIONS` (click, fill, select, check, uncheck, upload, press_key) queda denegado. Un run de QA que tenga que escribir necesita `destructive_actions: true`.
- Una acción denegada por policy **no lanza** desde el graph: se registra como `StepOutcome.DENIED` y cierra el episodio sin replanificar. Si vuelves a hacerla escapar, Temporal reintentará el episodio como fallo de infraestructura.
- El enforcement de browser vive en `GuardedBrowserGateway`, no en el adapter: el adapter Playwright debe entregarse **siempre** envuelto.
- `perform_once` (verify-before-retry) ya existe en `application/services/side_effects.py`: úsalo para cualquier side effect nuevo en vez de reintentar a ciegas.
- El graph consume el port `ModelGateway`; el adapter vLLM ya lo implementa. `PlannedAction` tiene tres resultados (acción / nada que hacer / `failure`) y colapsarlos convierte un modelo caído en un run exitoso.
- El agent runtime se cablea **sólo en el worker** (`bootstrap/agent_runtime.py`, llamado desde `with_agent_runtime`). La imagen de la API no lleva Chromium: `api` usa el stage `runtime`, `worker` el stage `worker`.
- Sin `VLLM_BASE_URL`/`VLLM_MODEL` el worker arranca igual y la activity reporta "no runtime configurado". **Hay GPU**: una RTX 5060 Ti 16GB (sm_120). `docker compose --profile gpu up -d vllm` sirve `Qwen/Qwen3-4B-Instruct-2507` en el puerto 8100 del host (8000 dentro de la red). El primer arranque descarga el modelo; el healthcheck da 600s por eso.
- vLLM 0.27 **no** acepta `--guided-decoding-backend` (es `--structured-outputs-config`), y bajo WSL2 necesita `VLLM_WSL2_ENABLE_PIN_MEMORY=1` o el engine muere con "UVA is not available". Ambas cosas ya están en compose; no las quites.
- **`CHECKPOINTED_TYPES` en `infrastructure/agent/langgraph/checkpointer.py` es la lista de lo que un checkpoint puede reconstruir**, con `LANGGRAPH_STRICT_MSGPACK=true`. Si añades un tipo nuevo al estado del graph y olvidas la lista, vuelve como `dict` y rompe el resume; `tests/agent/test_checkpoint_serialization.py` lo detecta.
- La tabla del dominio se llama `recovery_points`, no `checkpoints`: ese nombre lo ocupa LangGraph. `alembic/env.py` excluye las tablas que la librería gestiona.
- `httpx2` está en dev deps porque el `TestClient` de starlette lo exige (con `filterwarnings=error` su ausencia rompe la suite). No lo borres por parecer redundante con `httpx`.
- Python 3.13 vía uv (`backend/.python-version`); pnpm 10.34.5 pinneado en `frontend/package.json`. mypy corre en strict sobre `src` y `tests`, y pytest trata los warnings como errores.
- **La CLI es un delivery adapter**: `cli/test/boundaries.test.ts` falla si importa Playwright/Temporal/LangGraph/PostgreSQL/Redis o los declara como dependencia. No lo relajes.
- **Un solo sitio escribe stdout** (`emit` en `cli/src/main.ts`) y emitir dos veces lanza. Todo lo demás va a stderr.
- **Exit 1 ≠ exit 7**: 1 es un verdict no-pass, 7 es un wait timeout con el run vivo.
- `run flaky` da una key nueva a cada réplica; reusar una devolvería el mismo run N veces y reportaría estabilidad perfecta.
- `agent install claude` sólo toca el bloque entre `<!-- roveqa:begin -->` y `<!-- roveqa:end -->` y se niega a pisar un skill escrito a mano sin `--force`.
- La suite backend usa `agentic_qa_test`, no la base de la aplicación. Si `POSTGRES_TEST_DSN` vuelve a apuntar a `agentic_qa`, correr los tests borra los datos que sirve la API.
- Para regenerar `uv.lock` sin uv en el host:
  ```bash
  docker run --rm -v "$PWD/backend:/w" -w /w ghcr.io/astral-sh/uv:python3.13-bookworm-slim uv lock
  ```
