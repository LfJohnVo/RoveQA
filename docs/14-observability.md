# Observability

## Correlation identifiers
`request_id`, `run_id`, `evidence_set_id`, `episode_id`, `goal_id`, `action_id`, `workflow_id`, `activity_id`, `worker_id`, `browser_session_id`, `model_invocation_id`, `plan_id`, `plan_version`.

Para idempotency, loggear una referencia/hash seguro si hace falta correlación; no imprimir secretos ni valores sensibles completos.

## Logs
Structured JSON logs via structlog. Nunca loggear credentials ni raw sensitive form values por default. CLI debug/progress va a stderr; JSON stdout sigue reservado al contrato machine-readable.

## OpenTelemetry
Traces y metrics para API, Temporal activities, model calls, browser action durations, persistence adapters y materialización de artifacts/failure bundles.

## Metrics v1
- active/queued runs
- run duration
- actions/minute
- action verification failure rate
- recovery count
- checkpoint age
- model latency/tokens/errors
- browser crashes
- worker heartbeats
- Redis lock contention
- idempotency replay/conflict counts
- client wait timeouts/detaches vs explicit cancellations
- failure kinds (`product|plan|environment|policy|agent_budget|model|unknown`)
- failure cluster count vs raw failure count
- failure bundle integrity/materialization failures

## UI operational health
La UI muestra last checkpoint, last worker heartbeat, current status, current goal, current URL/fingerprint, model state y recovery attempts.


## Adaptive memory telemetry
Emitir spans/events/metrics para `memory.retrieve`, `memory.hit`, `memory.accepted`, `memory.revalidated`, `memory.rejected`, `memory.promoted`, `memory.invalidated`, `memory.feedback`, `graph.sync` y `graph.rebuild`.

Métricas mínimas: graph sync lag, retrieval latency, hit/useful rate, stale/contradiction rate, playbook success rate y savings de model calls/browser actions contra el cold baseline. Nunca incluir raw secret-bearing page text en attributes de telemetry.
