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
- `vllm-deep` profile `deep-gpu` (Phase 11, análisis de clusters). Compite por la tarjeta con
  `vllm` en un host de una sola GPU: el uso previsto es secuencial (el análisis ocurre después
  de que los runs terminan) o en otra máquina. `DEEP_BASE_URL` vacío deja el sistema completo,
  con clusters sin hipótesis. Un shim de AirLLM encaja aquí sin cambiar el backend.
- optional `test-target-app`

## Frontend (Phase 10)
Vite dev server en el 5173. Proxea `/api` **y** `/ws` al `api`, así el navegador habla con un solo origin y no existe configuración de CORS que sólo aplique en desarrollo — un ajuste que sólo vive en desarrollo es uno que nadie prueba. El realtime está montado en la raíz (`/ws/runs/{id}`), no bajo `/api/v1`, y por eso necesita su propia entrada de proxy.

Un bind mount desde un host Windows o macOS no entrega eventos de fichero al container, así que sin polling el dev server nunca recarga: `VITE_POLL_WATCH` (default `true`) lo activa. En Linux se puede poner en `false` y ahorrar la CPU.

Una imagen de producción del frontend es asunto de Phase 14; esto es la topología de desarrollo.

## CLI
`roveqa` no necesita ser un servicio Docker permanente. Es un cliente TypeScript/npm ejecutado por developer machines, coding agents o CI y se conecta al `api` público. Puede tener un container image opcional para CI/reproducibilidad, pero eso no cambia su boundary ni le da acceso directo a las redes internas de DB/Temporal/browser por defecto.

## Storage
Named volumes: postgres, Temporal DB si está separada, FalkorDB. Bind mounts: `./data/runs`, `./data/browser-state`, model cache si se desea.

## Healthchecks
No service debe depender sólo del container start order. API/worker usan readiness checks/backoff para dependencies. Worker no acepta runs hasta que PostgreSQL + Temporal estén ready. `roveqa doctor` debe consultar un readiness/compatibility surface público del API, no inspeccionar containers directamente.

## Profiles
Keep heavy inference optional in local CI. Tests can use deterministic fake model adapter without GPU. Integration profile activates actual vLLM when hardware exists. Phase 09 may activate `memory-gpu` independently for the embedding model; Graphiti itself runs as a backend library/adapter in the worker, not as a mandatory MCP service.
