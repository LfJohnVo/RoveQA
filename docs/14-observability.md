# Observability

## Correlation identifiers
`request_id`, `run_id`, `evidence_set_id`, `episode_id`, `goal_id`, `action_id`, `workflow_id`, `activity_id`, `worker_id`, `browser_session_id`, `model_invocation_id`, `plan_id`, `plan_version`.

Para idempotency, loggear una referencia/hash seguro si hace falta correlación; no imprimir secretos ni valores sensibles completos.

## Logs
Structured JSON logs via structlog. Nunca loggear credentials ni raw sensitive form values por default. CLI debug/progress va a stderr; JSON stdout sigue reservado al contrato machine-readable.

## Baseline operacional (Phase 13)

Lo que hay hoy, y por qué es esto y no un collector.

**Las preguntas que un operador hace de verdad se responden desde PostgreSQL**, porque las
escribieron los propios runs. `infrastructure/observability/queries.py` es ese conjunto:
una consulta con nombre por pregunta —runs por estado, veredictos de la semana, duración
p50/p95, distribución de `failure_kind`, cuánto de lo que reportamos descansa en la
opinión de un modelo, reducción del triage, clusters que nadie explicó, edad del último
checkpoint, tráfico de idempotencia, backlog del grafo, conocimiento por estado, cobertura
de exploración y huella de artifacts en disco.

Contadores en un proceso responden lo mismo peor: se reinician con el worker, no dicen
nada del run que terminó ayer, y leerlos exige que el proceso que los tiene siga vivo. Un
deployment que tiene que estar corriendo para explicar lo que pasó no es observable.

Las consultas **se ejecutan en el suite** (`tests/integration/test_operational_queries.py`)
contra el schema real, vacío y con datos. Ese es el motivo de tenerlas como código y no
como fragmentos en un documento: una consulta que dejó de coincidir con el schema es peor
que ninguna, porque alguien leería su resultado vacío como "no hay fallos". Escribirlas ya
encontró una que nombraba una columna inexistente.

Ninguna devuelve contenido de página, prompts ni nada donde pueda esconderse una
credencial; hay un test que lo comprueba por palabra prohibida, porque un dashboard es de
los sitios a los que ese texto llega más lejos.

`InferenceMetrics` y `MemoryMetrics` siguen existiendo para lo que sí hacen bien: latencia
y tokens por llamada, que ninguna tabla registra. Emiten una línea de log por llamada, así
que su historia vive en el log.

**Todavía no hay collector.** Añadir uno es un servicio nuevo y exige la necesidad
documentada que `CLAUDE.md` pide; cuando exista, el trabajo será exportar estas mismas
señales, no descubrirlas.

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
