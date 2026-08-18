# Redis Contract

## Allowed responsibilities
- Distributed locks with TTL.
- Resource reservations/semaphores for browsers, accounts and model slots.
- Worker presence/heartbeats.
- Rate limits.
- Hot caches.
- Redis Streams for low-latency run events delivered to UI.

## Forbidden responsibility
La única copia de cualquier dato necesario para reconstruir un run.

## Suggested key namespaces
- `lock:account:{account_id}`
- `lock:browser:{browser_id}`
- `semaphore:model:{model_key}`
- `worker:{worker_id}:presence`
- `cache:page:{fingerprint}`
- `cache:playbook:{project}:{fingerprint}`
- `stream:run:{run_id}`

## Stream retention
Streams realtime son bounded/trimmed. Eventos que deban sobrevivir para auditoría se persisten en PostgreSQL/event journal o artifact storage antes/de forma coordinada.

## Recovery assumption
`FLUSHALL` de Redis debe degradar performance/coordination temporalmente, no destruir verdad del producto.
