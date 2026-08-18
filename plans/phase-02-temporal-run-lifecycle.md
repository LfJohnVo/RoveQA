# Phase 02 — Run API + Temporal Lifecycle

## Objective
Start/pause/resume/cancel de runs durables sin browser todavía, con identidad de request e idempotencia desde el primer mutation contract.

## Tasks
1. FastAPI endpoints y DTO/error contract.
2. `X-Request-Id`: aceptar o generar, propagar a logs/events y devolver en response.
3. `POST /runs` con `Idempotency-Key` durable; mismo logical request/key devuelve el mismo logical run/resultado sin crear duplicate workflow.
4. Persistir idempotency records en PostgreSQL con request fingerprint/response identity y reglas de expiración/reuse documentadas; Redis no es source of truth.
5. Workflow `AgentRunWorkflow` con state durable, siguiendo la forma de workflow/retry ownership de ADR 0009.
6. Activities mínimas para persist status/events.
7. Pause/resume vía signals/updates adecuados; cancel semantics explícita y naturalmente idempotente cuando corresponde.
8. `GET /runs/{id}` con status durable; dejar seam para bounded long-poll usado por Phase 08 sin alojar loops de horas en FastAPI.
9. Worker heartbeat/identity metadata.
10. Temporal workflow tests incluyendo worker restart scenario si el test harness lo permite.
11. Lost-response test: simular que el servidor crea el run pero el cliente pierde el ACK; retry con la misma idempotency key no duplica el workflow.

## Gates
- Run sigue existiendo y su workflow puede continuar tras restart del worker.
- API request no aloja loop largo.
- Workflows no realizan I/O directo.
- Status DB y workflow no divergen silenciosamente.
- Request ID visible de extremo a extremo en tests/log fixture.
- Duplicate `POST /runs` con la misma idempotency key/request fingerprint no crea un segundo run.
- Reuse incompatible de una idempotency key falla de forma tipada en vez de ejecutar otra mutation.

## Required skills
- `backend-slice`
- `api-design-principles` for run command/status endpoints
- `error-handling-patterns`
- `postgresql` for durable idempotency records
- `durability-review`
