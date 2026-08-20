# Continue RoveQA with Opus 5

Instrucción autosuficiente para la siguiente sesión. Estado al cierre de la sesión anterior (2026-08-20): **Phases 00-14 DONE. El repositorio está en v1.0.0-rc.** Phase 14 (release candidate) cierra con sus gates verdes, un soak de 90 minutos (91 runs, 91 terminales, **0 atascados**, 8 perturbaciones de worker y Redis) y un demo de extremo a extremo que destapó **cinco defectos de producto y uno de despliegue**, ninguno visible en el código: el planner no sabía dónde está la aplicación, no sabía qué necesita cada acción, nunca veía la página, una propuesta rechazada mataba el run, el locator rechazaba objetivos correctos por ambigüedad — y Vite bloqueaba al stack entero por el header Host, lo cual delató el propio screenshot del FailureBundle. Antes: Phase 13 con 11/11, Phase 12 con 3/3, Phase 11 con 5/5, Phase 10 con 4/4, Phase 09 con 12/12. Todo corre en contenedores. **946 tests backend + 149 CLI + 46 frontend verdes.** `docs/status/RELEASE_CHECKLIST.md` dice qué se comprobó y con qué comando; `CHANGELOG.md`, qué promete y qué no. **No hay Phase 15 en `plans/`.**

## Pasos obligatorios, en orden

1. Lee `CLAUDE.md` completo. Sus invariantes de arquitectura, durabilidad, seguridad y skills routing gobiernan toda la sesión.
2. Lee `docs/status/PROGRESS.md` (estado por fase con evidencia).
3. Lee `docs/status/HANDOFF.md` completo — contiene decisiones tomadas, comandos ejecutados con resultados reales, gates PASS, known issues, deuda y riesgos.
4. Consulta Graphify si está disponible: existe `graphify-out/graph.json` pero **no incluye Phases 06-09**. Refréscalo (`graphify update .`) antes de fiarte de él, o verifica el source directamente. El grafo NO incluye docs (falta LLM API key); no lo fuerces.
5. Verifica el last stable state antes de cambiar nada:
   ```bash
   make up
   make migrate
   bash scripts/ci-local.sh
   ```
   `make up` va primero: desde Phase 01 el gate incluye migraciones y falla si PostgreSQL no está arriba. Todo corre en contenedores; en el host sólo hacen falta `docker compose` y `bash`. `ci-local.sh` debe terminar en "ci-local: all green" (946 backend + 149 CLI + 46 frontend, ~5 min). El gate resetea el schema de la base de tests antes de migrarlo; eso es deliberado y la base es desechable. Si algo está rojo, aplica `systematic-debugging` antes de continuar; no asumas que lo rompiste tú ni lo "arregles" a ciegas.
6. Continúa EXACTAMENTE desde el `Exact Next Task` del HANDOFF. Hoy no hay nada en vuelo y **no queda ninguna fase por hacer**: `plans/` llega hasta la 14 y está cerrada. Cualquier trabajo nuevo necesita instrucción explícita del usuario — endurecer el candidato, subir de modelo, o abrir un plan nuevo.
   No rehagas ninguna fase cerrada.
7. **No repitas side effects**: el stack compose ya se levantó y validó (volúmenes `roveqa_postgres_data`/`roveqa_falkordb_data` persisten); las imágenes `roveqa-api`/`roveqa-worker`/`roveqa-backend-tests` ya compilan y corren. No re-crees nada de eso salvo que un check demuestre que está roto. No hagas `docker compose down -v` (destruiría datos de Temporal).
8. **No avances de fase sin gates verdes**. Al cerrar: `/test-and-verify <fase>`, `/architecture-guard`, actualizar `PROGRESS.md` y `HANDOFF.md`, y DETENTE — no empieces la fase siguiente sin instrucción explícita del usuario.
9. Sigue usando todas las skills y reglas del proyecto: `ponytail` always-on, routing según `docs/21-claude-skill-routing.md`, `.claude/rules/*` por path, ADR para toda decisión estructural nueva. Los vigentes son ADR 0009 (retry ownership / workflow shape) y ADR 0010 (transaction ownership); no los contradigas.

## Contexto crítico que no debes redescubrir

- **Phase 09 ya resolvió tres incompatibilidades reales con FalkorDB.** No las redescubras: (1) el build de índices que Graphiti lanza en background cierra la conexión y hay que cancelarlo; (2) `group_id` se indexa como full text, así que el scope es un digest y se filtra por igualdad de propiedad; (3) con `embedder=None` Graphiti construye un cliente OpenAI, y por eso no se construye el objeto `Graphiti` en absoluto. Todo está documentado en ADR 0008 y hay tests que lo fijan.
- **Una observación y una hipótesis nunca se funden**, ni en el `dedup_key`, ni en la base de datos, ni en el contrato, ni en el prompt. Es la invariante que sostiene todo el bounded context.
- **Phase 13: un límite que nadie cuenta no es un límite.** La policy prometía `max_actions`, `max_model_calls` y `max_duration_seconds` y el camino planificado no los contaba. Si tocas el graph, esos contadores y la clasificación que producen (`agent_budget` → `blocked`) son lo que impide que un bucle vuelva como fallo de infraestructura, que es la clasificación que hace a Temporal reproducir el bucle.
- **Phase 13: hay dos clases de URL.** Una *para actuar* conserva el query string y vive lo que vive el run; una *para guardar* se recorta a esquema, host y path. Guardar la primera donde va la segunda es cómo un token de sesión sobrevive a su sesión dentro de una tabla que nadie piensa como almacén de credenciales.
- **Phase 13: la compactación se aplica en cada nivel o en ninguno.** Pasos → summary mantiene plano un episodio; sin cota sobre los summaries, lo que crece es la duración del run. Los episodios viejos se cuentan y se dicen al planner, no se olvidan en silencio.
- **Phase 12: una exploración termina por estructura, no por budgets.** Una affordance se ofrece **una sola vez** y las de un estado se encolan sólo la primera vez que se ve. Si tocas el frontier, eso es la garantía que no puedes perder — los budgets sólo acotan cuánto tarda.
- **Phase 12: un estado es lo que la página ofrece, no su DOM.** Ruta normalizada más el conjunto de affordances normalizadas. Sin eso, una lista con una fila más es un lugar nuevo, el crawl no converge y el reporte afirma que la aplicación entera cambió anoche.
- **Phase 12: la policy se consulta ANTES de ofrecer una affordance**, no después de intentarla. Una acción denegada cierra el episodio por diseño, así que un explorador que encolara botones se detendría en el primero. Links navegando (read-only), botones contados como declinados.
- **Phase 12: no hay `evaluate` ni para el explorador.** `describe_page()` lee el árbol de accesibilidad. Un escape hatch de JS por comodidad sería un agujero que ninguna policy ve.
- **Phase 11: la evidencia decide la membresía de un cluster; el modelo sólo propone el porqué.** Los members y la razón del agrupamiento viven en `failure_clusters`/`failure_cluster_members`; la hipótesis vive en `cluster_hypotheses` con `model_derived` forzado por un CHECK. No hay ninguna operación que escriba ambas. Si añades una, rompes el gate central de la fase.
- **El análisis deep es opcional en serio.** `DEEP_BASE_URL` vacío deja el sistema completo: los clusters se agrupan, se almacenan y se sirven, cada uno con `hypothesis: null`. No conviertas la ausencia del modelo grande en un error, ni el pass en algo que pueda fallar un run cuyo verdict ya es durable.
- **El pass commitea los clusters ANTES de llamar al modelo**, y la llamada ocurre fuera de toda transacción. Minutos de inferencia dentro de una transacción están prohibidos por `.claude/rules`, y commitear antes es lo que hace la fase reanudable.
- **El soporte cuenta runs independientes.** Consolidar y dar feedback son idempotentes por run/episodio. Si tocas ese camino, el riesgo no es un error visible: es que una observación flaky se convenza a sí misma de ser confiable.

- **Phase 14: el mismo defecto, cinco veces.** Dónde está la aplicación, qué necesita cada acción, qué hay en la página, por qué se rechazó una propuesta, cuál de dos elementos homónimos importa: en los cinco casos el sistema tenía el dato y no se lo daba a quien tenía que usarlo. Si añades una capacidad al planner, la pregunta que evita el sexto es *¿quién tiene que saber esto para cumplirlo, y se lo estamos diciendo?*
- **Phase 14: los fakes no distinguen "no hay nada" de "no te lo enseñé".** Las cinco tenían tests verdes alrededor. Un `PageState` vacío devuelto por un doble es idéntico a una página que nadie miró, y un prompt que no pide nada pasa cualquier test que no lo lea. Por eso las listas de acciones del prompt se renderizan desde los frozensets del dominio (`NEEDS_TARGET`, `NEEDS_VALUE`) y hay un test que recorre el conjunto: es lo que impide que vuelvan a separarse.
- **Phase 14: `PlannedAction.rejected` separa dos cosas que parecían una.** Un modelo inalcanzable no se reintenta dentro del episodio —la misma pregunta al mismo silencio—; una propuesta que rechazó nuestro propio dominio sí, por Recover, con el motivo grabado como step para que llegue al prompt siguiente. Si tocas el graph, ese es el camino que impide que un error de formato cueste un run entero.
- **Phase 14: `--timeout` de la CLI es milisegundos** y acepta unidad (`300s`, `10m`). Un número pelado sigue siendo ms por compatibilidad. Los tres ejemplos publicados lo usaban como si fueran segundos; si escribes uno nuevo, pon la unidad.
- **Phase 14: con el 4B ningún run llega a `passed`.** Es un límite declarado en el CHANGELOG, no un fallo escondido. El agente navega, lee la página, se corrige y captura evidencia; no declara la meta alcanzada. Antes de tocar código por esto, prueba un modelo mayor: es la variable que no se ha movido.

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
