---
name: error-handling-patterns
description: Diseña manejo de errores resiliente y consistente entre Domain, Application, FastAPI, CLI, Temporal, browser, Redis, PostgreSQL y model providers. Usar al implementar fallos, retries, recovery, error mapping o degradación.
---
# Error handling patterns

## Classify first
Clasificar errores antes de decidir qué hacer:
- validation/input;
- domain/business rule;
- auth/permission;
- conflict/idempotency/version;
- rate/resource capacity;
- transient dependency/transport;
- permanent dependency/configuration;
- programmer/invariant violation;
- cancellation;
- client wait timeout/detach;
- plan ambiguity/agent budget/inconclusive cuando aplique al QA runtime.

## Layering
- Domain devuelve/lanza errores de dominio sin detalles de framework.
- Application traduce a resultados/códigos de caso de uso y decide policy de negocio.
- Infrastructure encapsula errores de SQLAlchemy, Redis, Playwright, HTTP/model clients y los mapea a ports.
- FastAPI traduce errores de aplicación a HTTP en un solo boundary consistente.
- CLI traduce HTTP/public envelopes a exit codes y UX; no inventa estados de dominio ni convierte un transport timeout en run failure.

## Retry discipline
- Reintentar sólo errores transitorios y sólo cuando la operación sea idempotente o verificable.
- Conservar la misma idempotency key al reintentar el mismo logical mutation después de una response perdida.
- Evitar retry storms: no apilar retries agresivos en CLI/HTTP client + API/app + Temporal sin presupuesto/owner claro.
- 409 persistente no se reintenta sólo por ser 409.
- Temporal Activities deben declarar timeout/retry/heartbeat apropiados; Workflows no hacen I/O directo.
- Redis no disponible debe degradar coordination/cache cuando sea seguro, no destruir durable truth.

## Wait and cancellation
- Client timeout, Ctrl-C o disconnect de `run wait` = detach.
- Cancellation del run = command explícito.
- Reportar `inconclusive/running` con next action cuando el cliente deja de esperar antes de terminal.

## Observability and UX
- Conservar `run_id`, `step_id`, `workflow_id`, `request_id`, idempotency identity y provider/browser context útil.
- Loguear causa técnica internamente; devolver mensajes seguros externamente.
- Frontend/CLI deben representar error, disconnected, recovering, retrying y waiting-timeout como estados distintos.
- Nunca capturar `Exception` sólo para ignorarla; suppressed best-effort failures deben poder diagnosticarse en debug sin contaminar machine stdout.

## Tests
Probar mapping, retries agotados, timeout, cancellation, duplicate side effect, lost response, malformed 2xx response y recovery después de crash donde aplique.
