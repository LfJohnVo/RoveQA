# API and Event Contracts

## Public API principles
- Versionar la superficie pública: `/api/v1/...`.
- Validar requests **y responses** en runtime en los adapters externos.
- Aceptar/propagar `X-Request-Id`; generar uno cuando falte y devolverlo siempre.
- Mutations que podrían repetirse después de una respuesta perdida aceptan `Idempotency-Key` o documentan idempotencia natural.
- No retry automático de conflictos persistentes como "run already active".
- Lecturas potencialmente grandes usan pagination/streaming/bounds.
- Un wait HTTP puede expirar sin afectar el lifecycle durable del run.

## REST v1

### Projects / stories
- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `POST /api/v1/projects/{project_id}/stories`
- `GET /api/v1/projects/{project_id}/stories?limit=` — **implementado (Phase 10)**: acotado como toda listado. Una story dejó de ser write-only; sin esto una UI sólo podía mostrar la que acababa de enviar.
- `GET /api/v1/stories/{story_id}` — **implementado (Phase 10)**.

`GET /api/v1/projects/{project_id}` incluye `default_run_policy_id` desde Phase 10: un run sin policy nombrada resuelve la del proyecto, así que un proyecto sin ella no puede correr. Exponerlo deja que un cliente lo diga **antes** de que alguien lo intente, en vez de que la precondición aparezca como un error de validación al final del flujo.

### Test plans
- `POST /api/v1/stories/{story_id}/plans` — **implementado (Phase 07)**: compila la historia en una nueva versión inmutable del plan y devuelve el documento portable. La compilación es determinista (sin modelo), así que es rápida y no hay nada que poll-ear. Enviar `plan_id` publica una versión nueva de un plan existente; el servidor asigna `plan_version` incremental.
- `GET /api/v1/plans/{plan_id}/versions/{version}` — **implementado (Phase 07)**: devuelve el documento portable, no una forma propia de la API. Los mismos bytes se pueden guardar a fichero y volver a importar.
- `POST /api/v1/plans` — **implementado (Phase 08)**: importa un documento portable como versión inmutable. Naturalmente idempotente: la versión es el content hash del documento normalizado, así que reenviar los mismos bytes devuelve `200` con la versión existente en vez de `201` con una segunda. Un cliente que perdió la respuesta puede reintentar sin key.
- `PUT /api/v1/plans/{plan_id}` con `If-Match`, `GET /api/v1/plans/{plan_id}` y `POST /api/v1/plans/validate`: pendientes. `plan lint` de la CLI cubre la validación offline.

`contracts/test-plan.schema.json` es el contrato portable. Persistir un plan no puede hacerlo imposible de exportar losslessly.

Los planes son inmutables por versión: no existe update. Un run registra `plan_id + plan_version` al crearse y esa referencia no se vuelve a resolver — un run terminado bajo la versión 3 no cambia de significado cuando se publica la 4.

### Runs
- `POST /api/v1/runs` — acepta `plan_id + plan_version` (**implementado**) o un TestPlan inline válido (pendiente). Requiere `Idempotency-Key`. Sin `plan_version` se resuelve la última **una sola vez**, al crear el run, y se fija: lo que juzga a un run no puede cambiar mientras corre. Sin `plan_id` el run es exploratorio y su verdict sólo puede ser inconclusive.
  - **RunPolicy resolution (normativo)**: el servidor resuelve la RunPolicy efectiva en este orden: `run_policy_id` del plan → default del Environment → default del Project. Si ninguna resuelve, la request falla con error tipado. Un run nunca arranca sin una RunPolicy resuelta con `allowed_origins`. El run persiste el policy id/version resuelto como provenance.
  - **Inline plan versioning (normativo)**: si el plan inline no trae `plan_version`, el servidor asigna una versión canónica = content-hash del plan normalizado. Ese valor es el que registran run, evidence y FailureBundle (`plan_version` es required en el manifest).
- `GET /api/v1/runs/{run_id}` — status/verdict/provenance. Opcional `wait_seconds=1..N` para bounded long-poll y `include_steps=false` por defecto.
- `POST /api/v1/runs/{run_id}/pause`
- `POST /api/v1/runs/{run_id}/resume`
- `POST /api/v1/runs/{run_id}/cancel` — explícito y naturalmente idempotente cuando ya está cancelled; nunca inferido desde un disconnect.

**Semántica de los comandos de lifecycle (implementado en Phase 02)**: los tres devuelven `202 Accepted` con `{run_id, accepted}`. Señalan al workflow; **no escriben status**. El status durable cambia cuando el workflow aplica el comando en su siguiente punto seguro, así que un `GET` inmediatamente posterior puede seguir mostrando el estado anterior — eso es correcto, no un bug. Señalar un run ya terminal es un no-op (idempotencia natural).
- `POST /api/v1/runs/{run_id}/rerun` — **implementado (Phase 08)**: nueva ejecución que copia la *versión* de plan del run fuente en vez de re-resolverla. Reejecutar un fallo tiene que ejecutar el mismo plan, o el segundo resultado responde a otra pregunta. Requiere `Idempotency-Key`.
- `GET /api/v1/runs/{run_id}/report` — **implementado (Phase 07)**: reporte construido desde filas durables (run + plan version + criterion results), nunca desde un transcript de modelo. Cada criterio separa `deterministic_observation` de `root_cause_hypothesis`: son claves distintas para que un consumidor pueda filtrar por clave y no por convención.
- `GET /api/v1/runs/{run_id}/findings`
- `GET /api/v1/artifacts/{artifact_id}` — **implementado (Phase 08)**: descarga los bytes. El id es un identificador, nunca un path; la referencia durable lo resuelve y el repositorio verifica el hash al leer, así que un artifact corrupto o sustituido se rechaza en vez de servirse como evidencia.
- `GET /api/v1/runs/{run_id}/artifacts`
- `GET /api/v1/runs/{run_id}/events?after=&limit=`
- `GET /api/v1/runs/{run_id}/failure-context` — **implementado (Phase 08)**: snapshot coherente para FailureBundle, resuelto en una sola consulta desde un run. Cada artifact se comprueba contra el `run_id` y un único `evidence_set_id` antes de salir; mezclar "el último screenshot" con el trace de otro run produce un bundle que se lee como coherente y no lo es.

### Artifacts
- `GET /api/v1/artifacts/{artifact_id}` — metadata o streaming/download autorizado según content negotiation/endpoints separados.

### Exploration (Phase 12)
- `POST /api/v1/runs` acepta `explore: true`. Explorar se pide, no se infiere de la ausencia
  de plan. El flag entra en el fingerprint de la `Idempotency-Key`: la misma key pidiendo una
  exploración y pidiendo un run planificado son peticiones distintas, y la segunda es un 409.
- `GET /api/v1/runs/{run_id}/exploration` — el mapa que dejó un run explorador, lo que gastó,
  y el delta contra la exploración anterior del proyecto. 404 si el run no exploró: un run
  planificado no tiene mapa, y contestar con uno vacío diría que la aplicación no ofrece nada.

El delta se calcula al leer desde dos mapas durables, no se almacena. Un tercer registro
podría discrepar con ambos, y la primera vez que alguien recalculara la comparación y
obtuviera otra respuesta que la guardada, ninguna volvería a ser creíble.

El baseline es la exploración **anterior** del proyecto, no la última que salió bien: un
baseline elegido por resultado esconde una regresión que lleva dos noches fallando detrás de
la última noche que pasó. La primera exploración de un proyecto no lleva delta — descubrir la
aplicación entera no son cuarenta hallazgos.

`unreachable_conclusions` marca que alguna de las dos exploraciones paró por budget, así que
`gone` puede significar "no se llegó" en vez de "se eliminó". Se reporta en vez de ocultarse:
esconder el hallazgo y esconder su salvedad son dos formas de mentir sobre él.

### Schedules (Phase 12)
- `POST /api/v1/projects/{project_id}/schedules` — crea una ejecución recurrente. El
  `schedule_id` lo elige el caller: es la identidad, así que crear dos veces el mismo es un 409 y
  no una segunda regresión nocturna. Por eso tampoco lleva `Idempotency-Key`.
- `GET /api/v1/projects/{project_id}/schedules`
- `POST .../{schedule_id}/pause` y `.../resume` — lo que se hace durante un deploy freeze. Borrar
  en su lugar pierde el cron y a quien lo escribió.
- `DELETE .../{schedule_id}`

`plan_version` ausente significa "resolver el plan más reciente en cada disparo" — correcto para
"corre la suite actual cada noche", incorrecto para una regresión fijada. Es una elección, no un
default que nadie notó.

**Temporal es el único dueño de un schedule**; no hay copia en PostgreSQL. Una copia puede
discrepar con lo que realmente dispara y sería la respuesta equivocada con aspecto de autoritativa.
De ahí sale gratis el gate de la fase: el schedule sobrevive a la API, al worker y al stack entero
porque ninguno lo estaba sosteniendo. Un proceso sin conexión a Temporal responde 503 y no un 201
por un schedule que nadie guardó.

Dos cosas que Temporal **no** devuelve tal como se enviaron, y que por eso viajan en el payload de
la acción: el cron literal (el servidor lo normaliza a un calendar spec) y los parámetros del run
(vuelven como `Payload` en crudo y se decodifican con el data converter del cliente).

Cada disparo arranca `ScheduledRunWorkflow`, que crea el run por el mismo camino que un run pedido
por API — con el workflow id del disparo como `Idempotency-Key`, de modo que un reintento del
disparo encuentra su run en lugar de empezar otra regresión.

Limitación conocida: el workflow del disparo termina en cuanto el run existe, así que la overlap
policy del schedule ve un disparo de un segundo y no un run de una hora. Una regresión más lenta
que su propio intervalo se apilará.

### Failure triage (Phase 11)
- `GET /api/v1/projects/{project_id}/failure-clusters?limit=` — clusters de fallos del proyecto,
  el más reciente primero.

Read-only y sin recomputar nada. Los clusters se escriben en fronteras de run por una activity
durable; un GET que reagrupara al vuelo daría una respuesta distinta según quién preguntara y
cuándo.

El payload mantiene las dos mitades separadas en la forma misma: `members` y `reason` son lo
observado, `hypothesis` es un objeto aparte con `model_derived: true`, y un cliente no tiene manera
de presentar la segunda con el formato de la primera. `counted_as_defects` cuenta sólo los clusters
`independent`: reportar también los `blocked_downstream` convertiría un entorno caído en una docena
de bugs.

Un cluster sin hipótesis es normal, no un error — significa que nadie le preguntó a un modelo
grande, porque no hay endpoint deep configurado o porque ya estaba explicado.

### Memory admin (Phase 09)
Administración de memoria (Phase 09), scoped por proyecto y con `environment_id` como query param:

- `GET /api/v1/projects/{project_id}/memory/status` — reporta y no cambia nada.
- `POST /api/v1/projects/{project_id}/memory/validate` — busca desacuerdo entre lo durable y la proyección, **sin repararlo**. Separar validate de rebuild importa: si validar reparara, la única forma de saber si el grafo está sano sería reescribirlo, y eso destruye la evidencia de qué falló.
- `POST /api/v1/projects/{project_id}/memory/rebuild` — reconstruye la proyección desde PostgreSQL.
- `POST /api/v1/projects/{project_id}/memory/sync` — drena el backlog sin reconstruir; es lo que se corre cuando el grafo vuelve.

**Sin `Idempotency-Key`.** Estas operaciones son naturalmente idempotentes: derivan la proyección de filas que ya existen, así que correrlas dos veces produce el mismo grafo y correrlas tras un fallo parcial simplemente termina el trabajo. Exigir una key agregaría ceremonia sin proteger nada.

Los cuatro responden desde PostgreSQL, así que siguen funcionando con el grafo caído — que es justo cuando alguien los usa. Un grafo inalcanzable se **reporta** (`graph_available: false`), no se convierte en 5xx: el lado durable está intacto y el backlog conservó el trabajo. Lo único que falla duro es pedir un rebuild cuando no hay proyección configurada (503), porque un 200 ahí le haría creer al operador que existe.

La CLI sigue siendo thin-client sobre estos endpoints.

`run diff` puede empezar como comparación determinista client-side de dos snapshots públicos; si el cálculo se vuelve domain logic compartida, promoverlo a un Application query/API sin duplicarlo en UI/CLI.

## Run creation idempotency

```text
client POST /runs + Idempotency-Key K
           |
           | response lost
           v
client retries same logical request + K
           |
           v
same logical run_id / response
```

Nunca crear un segundo run/side effect sólo porque el cliente no recibió el primer ACK. La idempotency record es durable (PostgreSQL), no Redis-only.

## Wait semantics

`GET /runs/{id}?wait_seconds=20` puede bloquear como máximo ese window y devolver estado no terminal. La CLI repite bounded long-polls hasta su deadline total.

```text
client deadline / Ctrl-C -> DETACH
POST /runs/{id}/cancel   -> CANCEL
```

No confundir `408/timeout` del cliente con `cancelled` del dominio.

## WebSocket
`/ws/runs/{run_id}` entrega realtime envelopes, pero la UI debe poder reconstruir su estado base con REST si pierde conexión. Redis Streams ayuda a fan-out/hot replay, pero PostgreSQL/run state sigue siendo authoritative.

## Event envelope
```json
{
  "event_id": "uuid",
  "run_id": "uuid",
  "type": "agent.step.completed",
  "occurred_at": "RFC3339",
  "sequence": 123,
  "payload": {},
  "artifact_refs": []
}
```

## Important event types
`run.created`, `run.started`, `run.status.changed`, `episode.started`, `episode.completed`, `agent.goal.changed`, `agent.action.prepared`, `agent.action.verified`, `browser.page.changed`, `browser.console.error`, `browser.network.error`, `finding.created`, `checkpoint.created`, `evidence.set.created`, `model.inference.started/completed`, `worker.heartbeat`, `run.completed`, `run.failed`.

## CLI envelope
`contracts/cli-envelope.schema.json` define JSON machine-readable. stdout contiene un único envelope; logs/progress/debug van a stderr.
