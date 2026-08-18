---
name: api-design-principles
description: Diseña y revisa APIs HTTP/FastAPI y contratos CLI consistentes, versionables e idempotentes. Usar al crear endpoints, DTOs, pagination, filtering, command APIs, error contracts, OpenAPI, CLI JSON/exit codes o cambios de compatibilidad.
---
# API design principles

## Resource model
- Preferir recursos y nouns estables en URLs; acciones sólo cuando representan commands que no encajan limpiamente en CRUD.
- Usar métodos HTTP y status codes semánticamente correctos.
- Mantener transport DTOs separados de entities del Domain.
- Diseñar contratos desde el consumidor y acceptance criteria antes del handler.

## Commands and long-running runs
- Para iniciar una ejecución, devolver identidad/estado del run; no mantener una request HTTP abierta durante horas.
- Pause/resume/cancel deben ser commands explícitos con transiciones válidas.
- Side effects reintentables requieren idempotency key o verify-before-retry cuando aplique.
- Si una response puede perderse, conservar la idempotency record de forma durable y rechazar reuse incompatible de la misma key.
- Exponer status durable desde PostgreSQL/Temporal, no desde presencia efímera de Redis.
- Un bounded long-poll puede esperar segundos; su timeout no equivale a cancellation del recurso durable.

## Collections and payload bounds
- Usar cursor pagination para streams/listas grandes o mutables; offset sólo donde sea suficiente y documentado.
- Filtros y sorting con nombres consistentes, allowlist y límites.
- Establecer límites máximos de page size, plan size y response buffering.
- Preferir streaming para artifacts grandes.

## Errors
- Definir un error envelope/problem format estable con machine-readable code, message seguro, correlation/request ID y detalles de validación cuando correspondan.
- No filtrar tracebacks, SQL, prompts internos, tokens ni secretos.
- Diferenciar 4xx del cliente/estado de negocio y 5xx/dependencias.
- Validar response bodies críticos en runtime; un 2xx malformed no se transforma en success por un cast estático.

## CLI contracts
- `--output json` emite un único objeto/envelope parseable a stdout; diagnostics a stderr.
- Exit codes son parte del public contract y deben corresponder a typed error/verdict.
- `wait timeout` conserva run ID/last status/next action.
- Contracts portables (`TestPlan`, `CLIEnvelope`, `FailureBundle`) llevan schema version y contract tests.

## Evolution
- Evitar breaking changes silenciosos.
- Preferir cambios aditivos; versionar cuando la compatibilidad no pueda preservarse razonablemente.
- Mantener OpenAPI, JSON schemas, CLI fixtures y docs alineados en el mismo change set.
- Agregar contract tests para endpoints, eventos y machine-facing outputs críticos.
