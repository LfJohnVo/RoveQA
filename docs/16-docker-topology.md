# Docker Compose Topology

## Services target
- `frontend`
- `api`
- `worker`
- `postgres`
- `redis`
- `temporal`
- `temporal-ui`
- `falkordb`
- `vllm` profile `gpu`
- `vllm-embed` profile `memory-gpu` (Phase 09, pooling/embeddings)
- `airllm` profile `deep`
- optional `test-target-app`

## CLI
`roveqa` no necesita ser un servicio Docker permanente. Es un cliente TypeScript/npm ejecutado por developer machines, coding agents o CI y se conecta al `api` público. Puede tener un container image opcional para CI/reproducibilidad, pero eso no cambia su boundary ni le da acceso directo a las redes internas de DB/Temporal/browser por defecto.

## Storage
Named volumes: postgres, Temporal DB si está separada, FalkorDB. Bind mounts: `./data/runs`, `./data/browser-state`, model cache si se desea.

## Healthchecks
No service debe depender sólo del container start order. API/worker usan readiness checks/backoff para dependencies. Worker no acepta runs hasta que PostgreSQL + Temporal estén ready. `roveqa doctor` debe consultar un readiness/compatibility surface público del API, no inspeccionar containers directamente.

## Profiles
Keep heavy inference optional in local CI. Tests can use deterministic fake model adapter without GPU. Integration profile activates actual vLLM when hardware exists. Phase 09 may activate `memory-gpu` independently for the embedding model; Graphiti itself runs as a backend library/adapter in the worker, not as a mandatory MCP service.
