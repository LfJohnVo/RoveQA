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
- `POST /api/v1/plans` — crear definición/version inicial; idempotent trigger.
- `GET /api/v1/plans/{plan_id}`
- `GET /api/v1/plans/{plan_id}/versions/{version}`
- `PUT /api/v1/plans/{plan_id}` — crear nueva versión usando `If-Match`/expected version o equivalente.
- `POST /api/v1/plans/validate` — validación sin ejecución; opcional si CLI puede validar completamente offline.

`contracts/test-plan.schema.json` es el contrato portable. Persistir un plan no puede hacerlo imposible de exportar losslessly.

### Runs
- `POST /api/v1/runs` — acepta `plan_id + version` o un TestPlan inline válido. Requiere `Idempotency-Key`.
  - **RunPolicy resolution (normativo)**: el servidor resuelve la RunPolicy efectiva en este orden: `run_policy_id` del plan → default del Environment → default del Project. Si ninguna resuelve, la request falla con error tipado. Un run nunca arranca sin una RunPolicy resuelta con `allowed_origins`. El run persiste el policy id/version resuelto como provenance.
  - **Inline plan versioning (normativo)**: si el plan inline no trae `plan_version`, el servidor asigna una versión canónica = content-hash del plan normalizado. Ese valor es el que registran run, evidence y FailureBundle (`plan_version` es required en el manifest).
- `GET /api/v1/runs/{run_id}` — status/verdict/provenance. Opcional `wait_seconds=1..N` para bounded long-poll y `include_steps=false` por defecto.
- `POST /api/v1/runs/{run_id}/pause`
- `POST /api/v1/runs/{run_id}/resume`
- `POST /api/v1/runs/{run_id}/cancel` — explícito y naturalmente idempotente cuando ya está cancelled; nunca inferido desde un disconnect.
- `POST /api/v1/runs/{run_id}/rerun` — nueva ejecución con provenance a run/plan fuente; idempotency key.
- `GET /api/v1/runs/{run_id}/findings`
- `GET /api/v1/runs/{run_id}/artifacts`
- `GET /api/v1/runs/{run_id}/events?after=&limit=`
- `GET /api/v1/runs/{run_id}/failure-context` — snapshot/proyección coherente para FailureBundle.

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
