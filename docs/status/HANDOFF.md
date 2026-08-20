# Session Handoff

Última sesión: 2026-08-20 (Opus 5). **Phases 02-14 completadas; v1.0.0-rc.** Phase 14 cierra con sus gates verdes, un soak de 90 minutos sin un solo run atascado y un demo que destapó cinco defectos de producto y uno de despliegue, ninguno visible en el código. Phase 13 cierra con 11/11 gates PASS y cuatro defectos reales encontrados por los propios ejercicios de hardening: un presupuesto que nadie contaba, un token que llegaba al state map, un tope de fichero comprobado después de leerlo, y una compactación de contexto que compactaba un nivel y no el siguiente. Phase 12 cierra con 3/3 gates PASS: exploración autónoma acotada que termina por construcción y no por budgets, schedules cuya supervivencia a un reinicio se verificó en vivo, y una comparación contra baseline que no marca cada cambio de DOM. Phase 11 cierra con 5/5 gates PASS: triage determinista de fallos, durable y acumulativo entre runs, más un endpoint deep opcional detrás del `ModelGateway` verificado contra vLLM vivo con guided decoding real. Phase 10 cerró con 4/4 (UI de control React/MVVM verificada contra el stack vivo) y Phase 09 con 12/12.

# Current Phase

14 — Release candidate (`plans/phase-14-release-candidate.md`), **IN_PROGRESS**.

Hecho:

- **Los artifacts tienen casa.** `api` y `worker` comparten el volumen `artifact_data` en
  `/data/runs`. Antes los bytes vivían dentro del contenedor del worker: la API no podía
  leer ninguno y reemplazar el worker los borraba. Verificado en vivo — la API sirve el
  PNG que capturó el worker.
- **Backup y restore, con drill.** `scripts/backup.sh` y `scripts/restore.sh`; el drill
  demuestra que el restore reemplaza y no fusiona, y que la evidencia vuelve intacta.
- **`docs/status/OPERATIONS_RUNBOOK.md`**: instalación en máquina nueva, backup/restore,
  upgrade, run atascado y operaciones de memoria. Cada comando se ejecutó.

- **El loop del cliente externo, recorrido de verdad.** En un `node:22-alpine` limpio, sin
  acceso al repositorio: `npm install -g` del tarball, `setup`, `doctor` (exit 0 sano, 2
  sin project, y comparando contratos con el servidor), `plan scaffold`, `plan lint`,
  `run create` y `run wait`. Encontró que `roveqa --help` no listaba nada; ahora devuelve
  la lista de comandos como éxito.
- **El skill de verificación se instala sin pisar.** Sobre un repo con su propio
  `CLAUDE.md`: la regla existente sigue ahí después, y una segunda instalación no la
  duplica.

- **Contratos publicados con fixtures.** `contracts/examples/` tiene un ejemplo canónico
  por contrato público, validado contra su schema en cada corrida; el test comprueba
  además que ningún fixture del directorio quede sin validar y que ningún identificador
  parezca real. La política de compatibilidad está escrita junto a ellos.
- **Ejemplo de CI.** `examples/ci/` (workflow) y `cli/examples/verdict-to-junit.mjs`
  (adaptador, distribuido con la CLI). El adaptador no decide el resultado: sale con el
  código que le dio la CLI, y distingue pass, verdict terminal que no es pass, y espera
  vencida con el run vivo.

- **Soak de 90 minutos terminado.** 91 runs, 91 terminales, **0 atascados**, con 8
  perturbaciones rotando worker (que se lleva Chromium) y Redis (`FLUSHALL` + reinicio).
  Ninguna costó un run. Desviación declarada en el script: hoy un run es un episodio, así
  que la propiedad se ejercita sobre un flujo continuo de runs y no sobre uno largo.
- **Demo de extremo a extremo** (`scripts/demo.sh`), ejecutado: dos historias contra la
  aplicación incluida, la CLI de por medio, y un FailureBundle cuyos bytes verifican por
  sha256.
- **`CHANGELOG.md`** (v1.0.0-rc, con la política de migración de los tres contratos) y
  **`docs/status/RELEASE_CHECKLIST.md`**, donde cada casilla lleva el comando que la
  comprueba.

**Cinco defectos, todos de la misma familia: información que el sistema tenía y no le
daba a quien debía usarla.** Ninguno se vio revisando código; los encontraron el soak y el
demo, ejecutándose contra el stack real.

1. **Nadie le decía al planner dónde está la aplicación.** Los origins eran sólo una valla.
   Ningún run salía de `about:blank`.
2. **Nadie le decía qué necesita cada acción.** El dominio exige target semántico y url; el
   prompt listaba nombres. **91 de 91** runs del soak murieron ahí. Las listas se renderizan
   ahora desde los propios frozensets del dominio, que es lo que impide que vuelvan a
   separarse.
3. **Nadie le mostraba la página.** `<page_observation>` era la URL, y se le pedía nombrar un
   elemento que nunca había visto. `describe_page()` existía desde Phase 12 sin estar en el
   camino que planifica.
4. **Una propuesta rechazada mataba el run.** Un modelo inalcanzable y una propuesta que
   nosotros rechazamos llegaban como el mismo string. `PlannedAction.rejected` los separa: la
   segunda pasa por Recover con el motivo en el prompt siguiente.
5. **El adaptador rechazaba objetivos correctos.** El strict mode de Playwright falla si un
   texto coincide dos veces —lo normal en una página real—, así que el planner nombraba algo
   que existe y aprendía que nombrar no sirve. `.first`, con el orden role-first decidiendo
   cuál es el primero.

Y uno de despliegue que delató la propia evidencia: **Vite respondía "Blocked request. This
host ("frontend") is not allowed"** a todo el stack. El screenshot del bundle era esa
página; durante el soak entero el agente no miró la aplicación ni una vez.
`server.allowedHosts` lo arregla.

Además, `--timeout` de la CLI es milisegundos y **los tres ejemplos publicados lo usaban como
si fueran segundos** — el de CI esperaba 1,8 s creyendo esperar media hora. Ahora acepta
unidad (`300s`, `10m`) y rechaza basura en vez de convertirla en NaN.

**Después del cierre, sobre el candidato:**

- **La interfaz ya se puede usar desde cero.** No había forma de crear un proyecto salvo
  `curl`: el formulario que faltaba convertía toda la UI en un visor de trabajo empezado en
  otro sitio. `POST /projects` + `POST /run-policies` en un solo gesto, porque un proyecto
  sin policy no puede compilar un plan ni lanzar un run — se listaría, abriría y se negaría
  a hacer nada. Verificado creando un proyecto real desde el navegador.
- **README y guía.** `README.md` es ahora un README de producto; `docs/GUIDE.md` lleva de
  cero a un run con evidencia por las dos vías (interfaz y CLI), con una sección de
  síntomas al final para los tres fallos que de verdad se dan.
- **Grafo refrescado** (`graphify update .`): 6 183 nodos, 15 946 edges, 457 comunidades.
  `docs/22-codebase-graph.md` guarda la medición: **cero** edges saliendo de `domain` y
  **cero** de `application` hacia `infrastructure`. La regla de dependencias medida sobre el
  AST, no afirmada. En el frontend, ninguna View importa infraestructura y los dos edges de
  `viewmodels -> infrastructure` son el punto de composición.

Falta: nada de la fase. Cerrada.

# Phase Status

- Phases 00 – 14: **DONE**.
- Siguiente: no hay Phase 15 en `plans/`. El repositorio está en v1.0.0-rc.

# Last Stable State

- Git branch `main`.
- `bash scripts/ci-local.sh` → **all green**: 946 tests backend (5 skips sin GPU/deep), 149 CLI, 46 frontend, migraciones sin drift, build frontend, compose config.
- Con la GPU arriba los skips corren: `VLLM_BASE_URL=http://vllm:8000 VLLM_MODEL=Qwen/Qwen3-4B-Instruct-2507`. Los skips son el test de modelo real de Phase 06, las dos mediciones de memoria de Phase 09 y los dos de deep analysis de Phase 11 (`DEEP_BASE_URL`/`DEEP_MODEL`).
- Stack: postgres, redis, temporal, temporal-ui, falkordb, api, worker, **frontend** (Vite dev server en el 5173, proxy de `/api` y `/ws` al API). Schema en `8b3ac8f35fa4`.
- El modelo es elegible por configuración: `VLLM_MODEL` más `VLLM_QUANTIZATION`, `VLLM_ENFORCE_EAGER` y `VLLM_EXTRA_ARGS` deciden si uno más grande entra en la tarjeta. `.env.example` lista qué modelos Qwen caben en 16GB. `vllm-embed` (perfil `memory-gpu`) sirve el modelo de embeddings, también elegible.
- El gate resetea el schema de la base de tests antes de migrarlo (`backend/scripts/reset_test_schema.py`). Correr `pytest` antes del gate dejaba tablas que ninguna migración creó y el `alembic upgrade head` siguiente fallaba sobre una tabla que estaba por crear. El script se niega a tocar una base cuyo nombre no contenga `test`.
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

# Architecture Decisions Made (Phase 13)

- **Un límite que nadie cuenta no es un límite.** `max_actions`, `max_model_calls` y
  `max_duration_seconds` estaban en la policy y no se contaban en el camino planificado.
  Ahora se cuentan, y agotarlos clasifica `agent_budget` → verdict `blocked`: el run no
  pudo terminar y no observó nada sobre el producto. Con el mismo cambio, `policy` y
  `model` también llegan a `blocked` — la taxonomía existía desde Phase 07 y el camino
  planificado no podía producirla.
- **Un fallo que no sabemos explicar se queda sin clasificar.** Una acción que falló en la
  página podría ser un entorno roto o un producto roto; adivinar entre los dos es la
  adivinanza que hace sospechoso todo reporte posterior.
- **Dos clases de URL.** Una *para actuar* conserva el query string, porque
  `/records?status=open` es otra página, y vive lo que vive el run. Una *para guardar* se
  recorta a esquema, host y path — que es lo que la identidad y el reporte necesitan, y
  nada donde una credencial pueda esconderse.
- **Una cota se le pregunta al filesystem antes de leer.** Comprobar el largo de algo que
  ya está en memoria es un informe, no un límite.
- **La compactación se aplica en cada nivel o en ninguno.** Pasos → summary mantiene plano
  un episodio; sin cota sobre los summaries, lo que crece es la duración del run. Los
  episodios viejos se cuentan y se dicen, no se olvidan en silencio.
- **Observabilidad desde filas durables, no desde contadores en proceso.** Los contadores
  se reinician con el worker y no dicen nada del run de ayer; un deployment que tiene que
  estar corriendo para explicar lo que pasó no es observable. No hay collector todavía y
  eso es una decisión: es un servicio nuevo y exige necesidad documentada.
- **Una matriz de recuperación con la columna que manda: qué test lo demuestra.** Una fila
  sin test es una afirmación. Escribirla obligó a verificar cada referencia y dejó los
  huecos por escrito.

# Architecture Decisions Made (Phase 12)

- **Una exploración termina por estructura, no por budgets.** Una affordance se ofrece **una
  sola vez** y las de un estado se encolan sólo la primera vez que se ve. Con eso, dos páginas
  que se enlazan mutuamente y un sitio completamente conectado terminan igual; los budgets
  sólo acotan cuánto tarda. Un límite es lo que uno pone cuando no puede demostrar la
  terminación; aquí se puede.
- **Un estado es lo que la página ofrece, no su DOM.** Ruta normalizada más el conjunto de
  affordances, ambos normalizados. Sin eso una lista con una fila más es un lugar nuevo, el
  crawl no converge y el reporte afirma que la aplicación entera cambió anoche.
- **La policy se consulta antes de ofrecer, no después de intentar.** Una acción denegada
  cierra el episodio por diseño — eso impide que un agente busque la vuelta a una policy — así
  que un explorador que encolara botones se detendría en el primero. Se pregunta al mismo
  guard, con la misma acción, un paso antes: links navegando (read-only), botones contados.
  Explorar no ensancha nada.
- **Explorar se pide, no se infiere.** Un run sin plan siempre significó "trabaja hacia este
  objetivo con el planner". El flag entra en el fingerprint de la idempotency key.
- **Temporal es el único dueño de un schedule.** Ninguna copia en PostgreSQL: una copia puede
  discrepar con lo que dispara de verdad y sería la respuesta equivocada con aspecto de
  autoritativa. De ahí sale gratis el gate de reinicio.
- **El delta no se almacena.** Se calcula al leer desde dos mapas durables; un tercer registro
  podría discrepar con ambos. El baseline es la exploración anterior, no la última buena.
- **Sin `evaluate`, ni para el explorador.** `describe_page()` lee el árbol de accesibilidad.
  Un escape hatch de JS por comodidad sería un agujero que ninguna policy ve.

# Architecture Decisions Made (Phase 11)

- **La evidencia decide la membresía; el modelo sólo propone el porqué.** Los members, la razón del agrupamiento y los evidence refs son deterministas; la hipótesis vive en otra tabla, con `model_derived` forzado por un CHECK. Ninguna sentencia escribe ambas mitades, así que ninguna puede sobrescribir a la otra. La misma separación viaja en el payload HTTP: `hypothesis` es un objeto anidado, no campos mezclados con los observados.
- **El agrupamiento es exacto, no difuso.** Una clave comparable byte a byte (kind, criterio, status, ruta, fingerprint, observación normalizada) en vez de un umbral de similitud: un umbral pone el borde de un cluster donde nadie puede señalarlo, y la primera vez que funde dos fallos distintos el agrupamiento entero deja de ser creíble. Lo que necesita juicio se le deja al modelo — sobre el representative, nunca sobre la membresía.
- **Un `cluster_id` derivado de la clave.** El mismo problema obtiene el mismo id en cualquier pass, que es lo que convierte el segundo pass en un upsert que acumula members en lugar de una segunda copia. Se hashea el JSON de la clave y no un `join`: un separador que pueda aparecer dentro de un componente haría colisionar dos claves distintas, y una colisión aquí funde dos problemas en silencio.
- **`AGENT_BUDGET` no es un fallo de setup.** Quedarse sin acciones es consecuencia de todo lo anterior, no causa de lo que vino después; tratarlo como cascada silenciaría hallazgos reales.
- **El modelo ve un resumen, no el archivo.** `ClusterAnalysisRequest` no tiene campos donde quepan evidence refs, artifacts o volcados de página. Es estructural y no una política que alguien deba recordar.
- **Commit antes de la parte lenta.** Agrupar → commitear → preguntar → commitear. Una interrupción cuesta hipótesis, nunca el agrupamiento, y ninguna transacción queda abierta durante minutos de inferencia.
- **Una explicación se compra una vez.** Cada run terminado dispara un pass; sin la regla de frescura (cluster nuevo, nunca explicado, o que dobló de tamaño) un proyecto con un muro estable pagaría la misma respuesta una vez por run. Es la lectura operativa de la "repeated-failure condition" del plan.
- **El fallo del modelo se guarda como fallo.** "Nadie pudo explicar esto" y "nadie preguntó" son estados distintos, y sólo uno merece reintentarse cuando el endpoint vuelva.
- **El deep endpoint es cualquier servidor OpenAI-compatible.** El backend sólo conoce `DEEP_BASE_URL`/`DEEP_MODEL`; `vllm-deep` (perfil `deep-gpu`) con un modelo mayor es la configuración documentada por defecto, y un shim de AirLLM encaja sin tocar código. Reutiliza el mismo cliente HTTP que el fast endpoint — un segundo camino sería un segundo sitio donde esconder una llamada sin límites.

# Architecture Decisions Made (Phase 09)

- **Una observación y una hipótesis nunca se funden.** El `dedup_key` incluye `model_derived`, así que la conjetura de un modelo no puede heredar el support de una observación ni, desde ahí, su trust. La base de datos lo defiende también (`NOT (model_derived AND status='trusted')`), porque un adapter, un backfill o un UPDATE a mano pueden llegar a la tabla sin pasar por la entidad.
- **El soporte cuenta runs independientes.** Consolidar es idempotente por run (idempotency record en la misma transacción) y el feedback es único por `(candidate, run, episode, kind)`. Un retry contando dos veces es exactamente cómo una observación flaky se convence a sí misma de ser confiable.
- **Perder confianza es más barato que ganarla.** Promocionar exige acuerdo repetido; una contradicción verificada invalida hasta un `trusted`. Los costos son asimétricos: actuar sobre algo falso corrompe el run siguiente; reaprender algo cierto cuesta una observación.
- **La memoria se corrige por comparación, no por atribución.** El sistema nunca pregunta si un item "ayudó" — eso sería una conclusión de modelo. Compara lo que la memoria afirmaba contra lo que un assert determinista observó. Por eso la reconciliación sólo emite contradicciones: el acuerdo ya lo cuenta el merge del candidate que el run produjo.
- **El estado de sincronización del grafo vive fuera del status del candidate.** El grafo caído no dice nada sobre si el conocimiento es cierto; sobrescribir un tier de promoción con `pending_sync` haría que un outage se leyera como pérdida de confianza.
- **La cola de sync guarda qué cambió, no qué hacer.** Cada entrada se resuelve contra la fila durable al sincronizar, lo que hace la sincronización auto-reparable: por muy atrasado que esté el grafo, reproducir la cola converge a lo que PostgreSQL dice ahora.
- **Tres respuestas de compatibilidad, no dos.** `exact`/`compatible`/`revalidate`/`incompatible`. Sin `revalidate`, cada deploy obliga a elegir entre repetir playbooks obsoletos y tirar la memoria — y la segunda opción deja el sistema permanentemente frío.
- **El ranking es determinista y vive en el dominio.** El grafo *amplía* el pool de candidates; nunca autoriza. Un FalkorDB vacío, atrasado o manipulado puede sugerir candidates existentes distintos; no puede inventar conocimiento ni cambiar lo que uno dice.
- **Redacción en la captura, no en el retrieval.** Un secreto se redacta; un texto con forma de instrucción se **rechaza** — no hay redacción segura para algo que se replayaría dentro de un prompt futuro. Un item irredactable no tumba el run.
- **Graphiti aporta modelo de grafo y driver, no ingestión ni search.** Ver las notas de implementación en ADR 0008: no se construye el objeto `Graphiti`, así que no hay slot vacío del que salga un cliente OpenAI por omisión.

# Files Created

Phase 13 (hardening):

- `docs/status/RECOVERY_MATRIX.md` y `docs/status/PERFORMANCE_PROFILE.md`.
- `backend/src/agentic_qa/domain/browser/urls.py` — `safe_url`, la frontera entre una URL
  para actuar y una para guardar.
- `backend/src/agentic_qa/infrastructure/observability/queries.py` — 13 consultas
  operacionales.
- `backend/scripts/measure_growth.py` — el medidor que produjo el perfil.
- Tests: `tests/qa/test_budget_and_classification.py`,
  `tests/browser/test_secret_containment.py`, `tests/domain/test_safe_urls.py`,
  `tests/integration/test_database_failure.py`,
  `tests/integration/test_operational_queries.py`, `tests/test_bounded_resources.py`,
  `tests/test_growth_profile.py`, `cli/test/file-inputs.test.ts`.

Phase 12 (exploration + scheduling), en `backend/`:

- `src/agentic_qa/domain/exploration/{state,frontier,comparison,actions}.py` — qué es "el mismo
  sitio", el frontier con sus budgets, el diff contra baseline, y cómo se toma una affordance
  sin ensanchar la policy.
- `src/agentic_qa/application/ports/{schedules,exploration}.py`,
  `src/agentic_qa/application/queries/exploration_report.py`.
- `src/agentic_qa/infrastructure/browser/playwright/affordances.py` — parser del ARIA snapshot.
- `src/agentic_qa/infrastructure/workflows/temporal/schedules.py` — `TemporalScheduleGateway`.
- `src/agentic_qa/interfaces/http/routers/{schedules,exploration}.py`.
- `alembic/versions/8b3ac8f35fa4_phase_12_explored_states.py`.
- Tests: `tests/exploration/*` (frontier, affordances, graph explorador, state maps, y un run
  real de punta a punta), `tests/browser/{test_page_description,test_exploring_a_real_app}.py`,
  `tests/http/test_schedules_api.py`, `tests/integration/test_schedules.py`.

Phase 11 (deep analysis + triage), en `backend/`:

- `src/agentic_qa/domain/triage/{signals,clustering}.py` — señales comparables y agrupamiento
  con detección de cascada. Sin I/O y sin modelo.
- `src/agentic_qa/application/ports/{deep_analysis,triage}.py` — `DeepAnalyst`,
  `ClusterAnalysisRequest`/`ClusterHypothesis`/`AnalyzedCluster`, y el repositorio de clusters.
- `src/agentic_qa/application/services/deep_analysis.py` — qué merece un modelo grande.
- `src/agentic_qa/application/commands/analyze_failures.py` — el pass de frontera de run.
- `src/agentic_qa/infrastructure/inference/airllm/gateway.py` — `AirLLMDeepAnalyst`.
- `src/agentic_qa/interfaces/http/routers/triage.py` — `GET /projects/{id}/failure-clusters`.
- `alembic/versions/cc429f184282_phase_11_failure_clusters.py`.
- Tests: `tests/triage/{test_clustering,test_deep_analysis,test_analyze_failures,
  test_deep_analysis_activity,test_triage_from_a_real_run}.py`,
  `tests/inference/{test_deep_analyst,test_deep_analysis_real_model}.py`,
  `tests/http/test_triage_api.py`.

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

Phase 13:

- `domain/agent/state.py`: `MAX_EPISODE_SUMMARIES` y `folded_episodes`.
- `domain/exploration/state.py`, `infrastructure/browser/playwright/gateway.py`: la URL
  que se guarda es la segura.
- `application/services/criterion_verification.py`: `goal_failure_kind`, que es lo que
  hace legible un run detenido.
- `infrastructure/agent/langgraph/graph.py`: cuenta acciones, llamadas y tiempo; clasifica
  el motivo de parada; pasa `folded_episodes` al prompt.
- `infrastructure/inference/prompts.py`, `application/ports/models.py`.
- `cli/src/commands/plan.ts`: el tamaño se pregunta antes de leer.
- `tests/target_app/app.py`: página `/secrets` con una credencial plantada.
- `docs/14-observability.md`.

Phase 12:

- `application/ports/{browser,episodes,workflows,unit_of_work}.py`: `describe_page()`, el budget
  de exploración y el mapa que devuelve, y `explore` en el arranque de un run.
- `application/services/guarded_browser.py`, `application/commands/start_run.py`.
- `domain/exploration/*` (nuevo) y `domain/agent`/`domain/browser` sin cambios: el modo
  explorador no tocó el modelo de acciones.
- `infrastructure/agent/langgraph/{graph,episode_runner,checkpointer}.py`: nodo `explore`, el
  frontier en el estado checkpointeado y su allowlist.
- `infrastructure/browser/playwright/gateway.py`: `describe_page()` resolviendo hrefs.
- `infrastructure/workflows/temporal/{contracts,activities,workflows,worker,gateway}.py`:
  `ScheduledRunWorkflow`, `start_scheduled_run`, el flag `explore` y el workflow gateway que al
  worker le faltaba.
- `infrastructure/persistence/postgres/{models,repositories,unit_of_work}.py`.
- `interfaces/http/{app,schemas}.py`, `routers/runs.py`.
- `compose.yaml` no cambió en esta fase; `docs/06`, `docs/11`, `docs/12`, `tests/conftest.py` sí.

Phase 11:

- `bootstrap/{settings,agent_runtime,container}.py`: endpoint deep configurable
  (`DEEP_BASE_URL`/`DEEP_MODEL`/`DEEP_TIMEOUT_SECONDS`/`DEEP_MAX_OUTPUT_TOKENS`), registro por
  capability y `deep_analyst` en el contenedor.
- `infrastructure/inference/vllm/client.py`: el lease del slot se deriva del timeout del endpoint.
- `infrastructure/inference/{prompts,schemas}.py`: prompt y schema de análisis de cluster.
- `infrastructure/persistence/postgres/{models,repositories,unit_of_work}.py`: tres tablas nuevas
  y `list_recent_failures`.
- `infrastructure/workflows/temporal/{contracts,activities,workflows,worker}.py`: la activity
  `analyze_failures` con heartbeat, al final del workflow.
- `interfaces/http/{app,schemas}.py`, `application/ports/{results,idempotency,unit_of_work}.py`.
- `compose.yaml` (`vllm-deep`, perfil `deep-gpu`), `.env.example`, `docs/08`, `docs/11`,
  `docs/12`, `docs/16`.


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

- Migraciones: … → `00dfb54608c5` (`artifacts`) → `27a82f4f015d` (provenance de modelo) → `faaec9b601ae` (`knowledge_candidates`) → `63d1345551d7` (feedback + graph sync) → `cc429f184282` (`failure_clusters`, `failure_cluster_members`, `cluster_hypotheses`) → **`8b3ac8f35fa4`** (`explored_states`, `exploration_runs`). `alembic check` limpio, y el downgrade de la última verificado.
- **La migración de Phase 05 borraba las tablas de LangGraph.** Autogenerate las capturó antes de que `alembic/env.py` las excluyera. En una base vacía los drops fallan y la cadena entera no se puede aplicar: una instalación nueva era imposible, y sobre una existente el upgrade destruía el estado de resume de cualquier run en vuelo. Eliminados de esa migración (no estaba desplegada en ningún sitio) y añadido `tests/integration/test_migrations_from_empty.py`, que aplica la cadena completa a una base desechable en cada corrida y prohíbe que una migración nombre una tabla de la librería.
- La suite migra su propia base con `POSTGRES_DSN=$POSTGRES_TEST_DSN alembic upgrade head`: fiarse de `create_all` la dejaba en el schema de cuando se creó una tabla, y una columna nueva nunca aparecía.
- La tabla `artifacts` guarda **referencias** (identidad, provenance, hash, tamaño); los bytes siguen en el filesystem (docs/11).

# Tests Executed

```
bash scripts/ci-local.sh
docker compose --profile gates run --rm backend-tests pytest
docker compose --profile gpu up -d vllm
# Phase 11: el adapter deep contra un servidor real con guided decoding
docker compose --profile gates run --rm \
  -e DEEP_BASE_URL=http://vllm:8000 -e DEEP_MODEL=Qwen/Qwen3-4B-Instruct-2507 \
  backend-tests pytest tests/inference/test_deep_analysis_real_model.py -v
docker compose --profile gates run --rm backend-tests pytest tests/triage -v
docker compose --profile gates run --rm -e VLLM_BASE_URL=http://vllm:8000 -e VLLM_MODEL=Qwen/Qwen3-4B-Instruct-2507 backend-tests pytest
docker compose --profile gates run --rm -e VLLM_BASE_URL=http://vllm:8000 -e VLLM_MODEL=Qwen/Qwen3-4B-Instruct-2507 backend-tests pytest tests/knowledge/test_memory_benchmark_real_model.py -v -s
docker compose up -d --build api worker   # verificación en vivo de /api/v1/projects/{id}/memory/*
```

# Exact Test Results

Phase 13:

- **937 tests backend + 120 CLI + 46 frontend**, `ci-local: all green` (ruff, ruff format,
  mypy strict sobre 296 ficheros, `alembic check` sin drift, pytest).
- Perfil medido (`scripts/measure_growth.py`, 2026-08-20): el estado de un run pasa de
  430 B (1 episodio) a 1 182 B (20) y se queda en **1 212 B a 200 episodios y 1 234 B a
  1 000**; el prompt se queda en **2 717 caracteres** desde los 20 episodios en adelante.
  Un episodio de 5 000 pasos pesa lo mismo que uno de 10. Antes del arreglo, mil episodios
  eran ~50 KB de estado en cada checkpoint.
- Las tablas de checkpoints de LangGraph dominan el disco (1 048 kB / 680 kB / 480 kB tras
  una corrida completa del suite); todo lo demás está por debajo de 64 kB.

Phase 12:

- **859 tests backend recolectados**, `ci-local: all green` (ruff, ruff format, mypy strict
  sobre 284 ficheros, `alembic upgrade head` + `alembic check` sin drift, pytest).
- `tests/exploration` (77, memoria + PostgreSQL donde el contrato lo permite),
  `tests/browser/{test_page_description,test_exploring_a_real_app}.py` (8 contra Chromium),
  `tests/integration/test_schedules.py` (7 contra el Temporal real).
- **Contra un run real**: `tests/exploration/test_exploring_a_real_run.py` → 4 passed. Dos
  exploraciones de la app de pruebas por la activity de Temporal, con Chromium y PostgreSQL
  reales: la primera deja mapa durable y **sin** delta (descubrir la aplicación entera no son
  cuarenta hallazgos), la segunda compara contra la primera y produce **cero hallazgos** sobre
  una aplicación que no cambió.
- **En vivo**: schedule creado por la API, `docker compose restart temporal api worker`, y
  sigue ahí intacto; un cron `* * * * *` disparó y creó un run cuyo idempotency key es
  `run:scheduled-every-minute-check-2026-08-20T08:34:00Z`.
- La migración `8b3ac8f35fa4` aplica desde vacío, `alembic check` no detecta drift, y su
  downgrade y re-upgrade se verificaron.

Phase 11:

- **748 tests backend recolectados**, `ci-local: all green` (ruff, ruff format, mypy strict sobre
  260 ficheros, `alembic upgrade head` + `alembic check` sin drift, pytest).
- `tests/triage` (48 en memoria + PostgreSQL) y `tests/inference/test_deep_analyst.py` (15) verdes.
- **Contra el modelo real**: `tests/inference/test_deep_analysis_real_model.py` → 2 passed contra
  vLLM vivo (`DEEP_BASE_URL=http://vllm:8000`, `Qwen/Qwen3-4B-Instruct-2507`). El servidor real,
  con guided decoding real, produjo un `ClusterAnalysis` válido que el adapter convirtió en una
  hipótesis etiquetada con su `model_invocation_id`, modelo y `prompt_version`.
- **Contra un run real**: `tests/triage/test_triage_from_a_real_run.py` → 4 passed. Chromium abre
  la página, el criterio falla, y la activity deja un cluster cuyos members apuntan a la fila de
  `criterion_results` que el run escribió — sin ningún modelo grande configurado.
- La migración `cc429f184282` aplica desde vacío, `alembic check` no detecta drift, y su downgrade
  y re-upgrade se verificaron.


- **642 passed, 3 skipped** sin GPU; **645 passed** con vLLM vivo. Los 3 skips son mediciones que exigen un endpoint de modelo real y se niegan a fingirlo.
  - `tests/knowledge` es nuevo en Phase 09 y corre en dos implementaciones (in-memory y PostgreSQL) donde el contrato lo permite.
- ruff "All checks passed!"; mypy strict "no issues found in 243 source files"; `alembic check` sin drift.
- Verificación en vivo: `GET/POST /api/v1/projects/{id}/memory/{status,validate,rebuild,sync}` responden 200 contra el FalkorDB real; con `falkordb` parado, `memory status` reporta `UNAVAILABLE` y sale 0, `memory validate` nombra el problema y sale 1, y al reiniciarlo vuelve a `available`. Un run real completo por Temporal ejecuta `consolidate_experience` y declina aprender de un verdict `inconclusive`, diciéndolo en el log.
- `ci-local: all green`. Frontend: eslint, tsc, vitest 1 passed, build OK.
- **Modelo real**: `tests/inference/test_real_model.py` pasa contra vLLM vivo en la RTX 5060 Ti (1 passed en 4.61s).

# Acceptance Gates (Phase 13)

| Gate | Resultado |
| --- | --- |
| Matriz de recuperación documentada y verde para los fallos soportados | **PASS** (`docs/status/RECOVERY_MATRIX.md`: 20 filas con el test de cada una. El hueco que ella misma nombraba —nadie inyectaba un fallo de PostgreSQL— se cerró con `tests/integration/test_database_failure.py` contra la base real) |
| Redis flush test verde | **PASS** (`tests/integration/test_redis_loss.py`, desde Phase 03) |
| Prompt injection no puede escapar de la RunPolicy | **PASS** (`tests/browser/test_playwright_gateway.py::test_untrusted_page_content_cannot_widen_the_policy`, contra Chromium real) |
| Sin secretos críticos en logs/artifacts | **PASS** (`tests/browser/test_secret_containment.py` con una credencial plantada en dos formas reales; encontró que un token en query string llegaba al state map y al prompt) |
| La terminación/timeout de la CLI nunca cancela implícitamente un run | **PASS** (`cli/test/detach.test.ts`, subprocess real + SIGINT) |
| Una mutación repetida con la misma identidad no duplica side effects | **PASS** (`cli/test/run.test.ts`, `tests/application/test_use_cases.py`, y el reintento tras fallo de base de datos deja exactamente una transición y un evento) |
| FailureBundle rechaza provenance mezclada y nunca expone uno incompleto como completo | **PASS** (`cli/test/bundle.test.ts`) |
| El JSON machine-readable sigue siendo válido en todo camino de error probado | **PASS** (`cli/test/envelope.test.ts` contra el schema publicado) |
| Inputs grandes/adversarios acotados por límites explícitos | **PASS** (`tests/test_bounded_resources.py` y `cli/test/file-inputs.test.ts`: cada límite recibe un input que lo rompería y la constante aparece en el assert. Encontró que la CLI leía el fichero entero antes de comprobar su tamaño) |
| Perder el grafo degrada sólo la optimización, y el rebuild restaura la proyección | **PASS** (`tests/knowledge/test_graph_sync.py`, desde Phase 09) |
| Memoria envenenada/obsoleta/de otro tenant no influye en el planner como contexto confiable | **PASS** (`tests/knowledge/`, desde Phase 09) |

Tareas del plan cubiertas: inyección de fallos (worker, Chromium, Redis, vLLM, FalkorDB, PostgreSQL), fixture de prompt injection, revisión de redacción, baseline operacional, perfil de rendimiento, caos de detach/idempotencia en la CLI, matriz de corrupción de bundles, validación de respuestas malformadas, pureza del stdout JSON, recursos acotados, fixtures de agent-budget, seguridad de lectura de ficheros, y caos/envenenamiento de la memoria adaptativa.

**Alcance declarado:** no hay un *harness* reutilizable de fault injection; cada fallo lo inyecta el test que lo prueba, que es lo que la matriz documenta. El perfil de rendimiento lista al final tres cosas que siguen sin medirse (latencia de checkpoint bajo carga concurrente, materialización de un bundle grande, coste de retrieval con un grafo grande).

# Acceptance Gates (Phase 12)

| Gate | Resultado |
| --- | --- |
| La exploración termina por budgets/goal; nunca en loop infinito | **PASS** (`tests/exploration/test_frontier.py` y `test_exploring_graph.py` corren el loop **sin tope de iteraciones**: si no terminara, el test se cuelga. Ciclo de dos páginas, sitio completamente conectado, corredor más largo que el budget, y profundidad que poda en vez de detener. Y sobre Chromium real en `tests/browser/test_exploring_a_real_app.py`) |
| Un run programado sobrevive un reinicio de servicio | **PASS** (verificado en vivo: schedule creado por la API → `docker compose restart temporal api worker` → sigue ahí con su cron, su pin de plan y su nota. Un cron de cada minuto disparó de verdad y creó un run cuyo idempotency key es el workflow id del disparo. `tests/integration/test_schedules.py` cubre el round-trip contra el Temporal real, incluido un cliente nuevo como sustituto de un proceso reiniciado) |
| Estados nuevos/cambiados generan un reporte útil sin marcar cada cambio de DOM | **PASS** (dos exploraciones reales del mismo sitio, con Chromium y PostgreSQL, producen **cero hallazgos**; una página que gana un control produce exactamente uno, dicho como "ganó", no como una página que desapareció y otra que apareció. Una lista con una fila más, ids distintos y otro año en el footer no son hallazgos) |

Las 6 tareas del plan están hechas: exploration policy derivada de la RunPolicy (`ExplorationBudget.under`), frontier visitado/pendiente con profundidad, novedad por fingerprint de estado, Temporal schedules con pause/resume, comparación contra baseline, y stop conditions con budget reporting (incluido lo que **no** se intentó por policy).

**Limitación conocida:** el worker sólo construye un episode runner cuando hay endpoint de modelo configurado, así que hoy explorar exige uno aunque no lo llame nunca. Y el workflow de un disparo de schedule termina en cuanto el run existe, así que la overlap policy ve un disparo de un segundo y no un run de una hora: una regresión más lenta que su propio intervalo se apilará.

# Acceptance Gates (Phase 11)

| Gate | Resultado |
| --- | --- |
| El browser loop funciona si el modelo deep no está disponible | **PASS** (`tests/inference/test_deep_analyst.py::TestWiring`: sin endpoint deep el router sigue sirviendo FAST y `build_deep_analyst` devuelve `None`; con endpoint deep el planning sigue yendo al fast. Y sobre un run real: `tests/triage/test_triage_from_a_real_run.py` corre Chromium, falla un criterio y almacena el cluster sin ningún modelo grande en juego) |
| El análisis deep se puede reanudar/reintentar sin corromper el run | **PASS** (idempotency record por run + upserts: el segundo pass no pregunta nada y no escribe nada, verificado en memoria y contra PostgreSQL; la activity se traga un store roto y devuelve 0 en vez de convertir un run completado en un workflow fallido; heartbeat verificado dentro de `ActivityEnvironment`) |
| Un lote de fallos duplicados/cascada se reduce a clusters sin LLM | **PASS** (`tests/triage/test_clustering.py`: 20 runs contra el mismo muro → 1 cluster y 0.95 de reducción; un entorno caído → 1 defecto independiente y el resto `blocked_downstream`) |
| Con el deep deshabilitado, el triage sigue siendo útil y reproducible | **PASS** (el mismo input en cualquier orden produce los mismos clusters y los mismos ids; los clusters se almacenan y se sirven por HTTP con `hypothesis: null`) |
| Una hipótesis generada por modelo no reemplaza member IDs/evidence | **PASS** (tablas separadas con FK y CHECK `model_derived`; `AnalyzedCluster` mantiene las dos mitades en campos distintos; el test recorre members y evidence refs después de que el modelo respondió) |

Las 9 tareas del plan están hechas: adapter deep tras `ModelGateway`, routing por capability, triage determinista primero, representative con member IDs y razón, sólo el resumen agregado viaja al modelo, cascada marcada y no contabilizada, trigger en frontera de run con condición de repetición, activity durable con heartbeat y timeout de una hora, y almacenamiento sólo de outputs/metadata con la evidencia determinista separada.

**Alcance declarado:** el trigger es la frontera de *run*, no la de episodio — un análisis entre episodios retrasaría el siguiente por minutos, que es justo lo que la fase evita. El `route` todavía no participa del agrupamiento porque `criterion_results` no guarda la URL donde se respondió el criterio.

# Acceptance Gates (Phase 10)

| Gate | Resultado |
| --- | --- |
| Las Views no importan API clients | **PASS** (`test/boundaries.test.ts` lee las líneas de import de cada capa y verifica además que sólo la composition root nombre un adapter concreto; incluye una violación plantada. Encontró una real: `ConnectionState` vivía en el puerto y una View lo importaba, así que se movió al dominio donde pertenece) |
| Recargar la página reconstruye el run desde REST | **PASS** (test con el socket mudo: todo lo que aparece vino del log durable; y verificado en vivo recargando un run terminado) |
| Un reconnect del WebSocket no duplica eventos visuales | **PASS** (el fold del timeline es idempotente y ordena por sequence, no por llegada; probado en el dominio y renderizado) |
| frontend lint/type/test/build verdes | **PASS** (46 tests; `strict` de TypeScript activado en esta fase, y los tests ahora también se typechequean) |

Las 9 tareas del plan están hechas: knowledge browser, app shell/routing/tokens, project list/detail, story editor con compilación, run launch, run ViewModel REST+WebSocket, timeline con findings y evidencia, pause/resume/cancel, y estados de desconexión.

# Acceptance Gates (Phase 09)

| Gate | Resultado |
| --- | --- |
| Un cold run verificado produce candidates durables con provenance correcta | **PASS** (`tests/knowledge/test_learning_from_a_real_run.py`: browser real contra la target app → evidencia → consolidación; cada candidate nombra su run y su evidence set) |
| Graphiti materializa sólo knowledge reusable | **PASS** (sólo `promoted`/`trusted` se proyectan; un candidate degradado se retira del grafo — `tests/knowledge/test_graph_sync.py`) |
| Un segundo run sobre fingerprint compatible reutiliza memoria y reduce planner calls o exploración | **PASS contra el modelo real** (Qwen3-4B en la RTX 5060 Ti): 4→2 planner calls y 3→1 browser actions, ambos runs terminando en `/records` |
| Benchmark ≥20% en una métrica primaria | **PASS**: 50%/67% con modelo real, 60%/75% con el double. Decisión registrada: **PROMOTE** (`docs/status/MEMORY_EVAL_phase09.md`) |
| Fingerprint/version mismatch marca `revalidate` y evita replay ciego | **PASS** (memoria de la versión 2.1.0 llega como `revalidate` en 3.0.0; el planner la comprueba y no la sigue) |
| Un playbook contradicho por evidencia verificada pierde reliability/se invalida | **PASS** (una contradicción verificada invalida hasta un `trusted`; el run siguiente no lo recibe) |
| Graph caído deja candidates pendientes y el run conserva correctness | **PASS** (verificado también en vivo: con `falkordb` parado, `memory status` responde `UNAVAILABLE` con exit 0 y `validate` sale 1 nombrando el problema; al volver, el backlog drena) |
| Borrar FalkorDB y reconstruir desde PostgreSQL | **PASS** (`rebuild_project` reconstruye sin reejecutar un solo test, no restaura lo invalidado y no toca otro proyecto) |
| Cross-project/role leakage devuelve cero memoria ajena | **PASS** (en SQL, en el dominio y en el grafo por `group_id`; tres capas, tres tests) |
| Secret/prompt-injection fixture no termina promovida | **PASS** (secretos redactados, texto con forma de instrucción **rechazado** — no redactado — y reportado) |
| Hipótesis de modelo permanece etiquetada y no reemplaza observación | **PASS** (dominio, base de datos, contrato portable y el propio prompt) |
| `MemoryContext` respeta límites y cada item lleva provenance/reliability/compatibility/selection_reason | **PASS** (validado contra `contracts/memory-context.schema.json`) |

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

- El `route` no participa del agrupamiento de fallos: `criterion_results` guarda la respuesta del
  criterio, no la URL donde se respondió. El agrupamiento funciona sin él (kind, criterio, status,
  observación normalizada); con él separaría dos fallos del mismo criterio en páginas distintas.
- Los failure clusters no tienen superficie de usuario más allá del endpoint REST: ni CLI ni UI.
- `open_checkpointer` abre y cierra conexión por episodio.
- La proyección escribe nodos y **no** relaciones. El modelo de docs/10 sigue siendo el objetivo; las aristas llegan cuando un gate las necesite.
- Sin endpoint de embeddings configurado por defecto, el retrieval ordena de forma determinista sobre un pool emparejado por texto. Es el bottleneck registrado en la eval.
- Sin endpoints de `Environment` ni GET de policies.
- structlog pendiente (docs/14).

# Risks

- `vllm` y `vllm-deep` comparten la tarjeta. Los perfiles lo hacen deliberado, pero levantar los
  dos a la vez en un host de una sola GPU hará que el segundo falle al cargar o que ambos vayan
  lentos. El uso previsto es secuencial, o una segunda máquina.

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

- postgres (`8b3ac8f35fa4` + tablas de LangGraph), redis, temporal + temporal-ui, falkordb, api, worker, frontend, vllm (perfil `gpu`). Chromium vía Playwright en la imagen `worker`.

# Services Still Stubbed/Deferred

- Ninguno. `frontend` (10), `vllm-embed` (09) y `vllm-deep` (11) existen como servicios compose
  bajo sus perfiles; los dos de GPU están apagados por defecto porque comparten la tarjeta.

# Exact Next Task

**Ninguna. `plans/` está agotado: Phase 14 era la última y cerró.**

El repositorio es un release candidate con gates verdes. Lo que venga ahora es decisión del
usuario, no continuación de un plan. Las tres cosas que este cierre deja señaladas, por si
sirven de punto de partida:

1. **Probar un modelo mayor.** Es la única variable del demo que no se ha movido, y la
   causa declarada de que ninguna historia llegue a `passed`. `VLLM_MODEL` más
   `VLLM_QUANTIZATION`/`VLLM_ENFORCE_EAGER`; `.env.example` lista qué cabe en 16GB. No hace
   falta tocar código para intentarlo, y hacerlo antes de tocar código es lo correcto.
2. **Etiquetar la v1.0.0-rc**, siguiendo `docs/status/RELEASE_CHECKLIST.md`. Ninguna casilla
   de "antes de etiquetar" exige código nuevo.
3. **Si aparece un sexto defecto de la misma familia**, la pregunta que lo encuentra antes es
   *¿quién tiene que saber esto para cumplirlo, y se lo estamos diciendo?* — no *¿está bien
   el código?*.

Cerrado y sin necesidad de revisitar: volumen de artifacts, backup/restore con drill, runbook
de operaciones, loop del cliente externo con instalación de skill, fixtures de contratos,
adaptador de CI, soak y demo.

# Exact Next Command

Verify the state you inherited before changing anything:

```
make up
bash scripts/ci-local.sh
```

The UI is at http://localhost:5173 once `docker compose up -d frontend` is running.

# Recommended Skills For Next Session

- `implement-phase` (proceso), `ponytail` (always-on).
- Para Phase 14: `changelog-generator` (sólo con gates verdes), `test-and-verify` + `architecture-guard` al cierre, y `api-design-principles` si se congelan contratos.
- Para trabajo de UI: `frontend-mvvm-slice` + `vercel-react-best-practices`, más `interface-design` y `frontend-design` en superficies nuevas.
- `adaptive-memory-graph` + `postgresql` si se vuelve sobre la memoria (embeddings, relaciones del grafo).
- `test-and-verify` + `architecture-guard` al cierre.
