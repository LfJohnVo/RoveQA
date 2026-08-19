# Continue RoveQA with Opus 5

Instrucción autosuficiente para la siguiente sesión. Estado al cierre de la sesión anterior (2026-08-18): blueprint auditado y endurecido, **Phases 00-06 DONE** (Phase 06: 3/3 gates PASS), pipeline de desarrollo y tests corriendo íntegramente en contenedores. 324 tests backend verdes (1 skip: modelo real opcional). Siguiente: Phase 07 (story workflow).

## Pasos obligatorios, en orden

1. Lee `CLAUDE.md` completo. Sus invariantes de arquitectura, durabilidad, seguridad y skills routing gobiernan toda la sesión.
2. Lee `docs/status/PROGRESS.md` (estado por fase con evidencia).
3. Lee `docs/status/HANDOFF.md` completo — contiene decisiones tomadas, comandos ejecutados con resultados reales, gates PASS, known issues, deuda y riesgos.
4. Consulta Graphify si está disponible: existe `graphify-out/graph.json` pero **no incluye Phase 06**. Refréscalo (`graphify update .`) antes de fiarte de él, o verifica el source directamente. El grafo NO incluye docs (falta LLM API key); no lo fuerces.
5. Verifica el last stable state antes de cambiar nada:
   ```bash
   make up
   make migrate
   bash scripts/ci-local.sh
   ```
   `make up` va primero: desde Phase 01 el gate incluye migraciones y falla si PostgreSQL no está arriba. Todo corre en contenedores; en el host sólo hacen falta `docker compose` y `bash`. `ci-local.sh` debe terminar en "ci-local: all green" (324 tests backend, ~65s). Si algo está rojo, aplica `systematic-debugging` antes de continuar; no asumas que lo rompiste tú ni lo "arregles" a ciegas.
6. Continúa EXACTAMENTE desde el `Exact Next Task` del HANDOFF:
   > Implement Phase 07 slice 1: derive an episode `goal` from a `UserStory` and its acceptance criteria instead of the declared default in `EpisodeParams`, so a run executes what the story asks for — the workflow shape and the retry split stay exactly as ADR 0009 fixed them.
   Phases 00-06 están cerradas: dominio, persistencia, API, Temporal, eventos, Redis, RunPolicy, browser gateway con recovery, agent graph con checkpointer y resume, y el adapter de inferencia con router/structured outputs YA existen y están testeados. No los rehagas. El comando de arranque es `/implement-phase 07`. Lee el plan de la fase en `plans/`.
7. **No repitas side effects**: el stack compose ya se levantó y validó (volúmenes `roveqa_postgres_data`/`roveqa_falkordb_data` persisten); las imágenes `roveqa-api`/`roveqa-worker`/`roveqa-backend-tests` ya compilan y corren. No re-crees nada de eso salvo que un check demuestre que está roto. No hagas `docker compose down -v` (destruiría datos de Temporal).
8. **No avances de fase sin gates verdes**. Al cerrar: `/test-and-verify 07`, `/architecture-guard`, actualizar `PROGRESS.md` y `HANDOFF.md`, y DETENTE — no empieces Phase 08 sin instrucción explícita del usuario.
9. Sigue usando todas las skills y reglas del proyecto: `ponytail` always-on, routing según `docs/21-claude-skill-routing.md`, `.claude/rules/*` por path, ADR para toda decisión estructural nueva. Los vigentes son ADR 0009 (retry ownership / workflow shape) y ADR 0010 (transaction ownership); no los contradigas.

## Contexto crítico que no debes redescubrir

- Los contratos v1 en `contracts/` fueron endurecidos ANTES de implementarse (memory labels, RunPolicy resolution, Verdict, failed_step_id, path-traversal guard). Impleméntalos tal como están; cambiarlos requiere versionado explícito.
- `Verdict` y `RunStatus` ya están modelados con su mapping (`docs/02-domain-model.md`) y defendidos por CHECK constraints. `COMPLETED` exige verdict: derivarlo es justo el trabajo de Phase 07.
- **`EpisodeOutcome` no transporta hoy el `failure_reason` del episodio**, así que el workflow cierra en `completed/inconclusive` aunque el episodio fallara o fuera denegado por policy. Es lo primero que Phase 07 tiene que arreglar para que el verdict signifique algo.
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
- Sin `VLLM_BASE_URL`/`VLLM_MODEL` el worker arranca igual y la activity reporta "no runtime configurado". No hay GPU en esta máquina: el path del modelo real está probado contra un stub OpenAI-compatible, y el tag del modelo **no está validado en hardware**.
- **`CHECKPOINTED_TYPES` en `infrastructure/agent/langgraph/checkpointer.py` es la lista de lo que un checkpoint puede reconstruir**, con `LANGGRAPH_STRICT_MSGPACK=true`. Si añades un tipo nuevo al estado del graph y olvidas la lista, vuelve como `dict` y rompe el resume; `tests/agent/test_checkpoint_serialization.py` lo detecta.
- La tabla del dominio se llama `recovery_points`, no `checkpoints`: ese nombre lo ocupa LangGraph. `alembic/env.py` excluye las tablas que la librería gestiona.
- `httpx2` está en dev deps porque el `TestClient` de starlette lo exige (con `filterwarnings=error` su ausencia rompe la suite). No lo borres por parecer redundante con `httpx`.
- Python 3.13 vía uv (`backend/.python-version`); pnpm 10.34.5 pinneado en `frontend/package.json`. mypy corre en strict sobre `src` y `tests`, y pytest trata los warnings como errores.
- Para regenerar `uv.lock` sin uv en el host:
  ```bash
  docker run --rm -v "$PWD/backend:/w" -w /w ghcr.io/astral-sh/uv:python3.13-bookworm-slim uv lock
  ```
