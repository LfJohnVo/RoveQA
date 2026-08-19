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

### Memory admin (Phase 09)
La superficie de administración de memoria (`memory status|rebuild|validate`) se especifica en `docs/26-adaptive-learning-graph.md` y se añade aquí cuando Phase 09 la implemente como endpoints públicos (`GET /api/v1/projects/{id}/memory/status`, `POST .../memory/rebuild` con `Idempotency-Key`, `POST .../memory/validate`). La CLI sigue siendo thin-client sobre estos endpoints.

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
