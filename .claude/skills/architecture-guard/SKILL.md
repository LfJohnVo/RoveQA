---
name: architecture-guard
description: Revisa cambios del proyecto para detectar violaciones de Clean Architecture, MVVM, boundaries, dependency inversion y acoplamiento indebido a infraestructura. Usar antes de cerrar fases o al refactorizar módulos.
---
# Architecture guard

Revisar el diff o scope indicado.

Checklist backend:
- Domain libre de frameworks e I/O.
- Application depende de ports, no adapters.
- ORM/Redis/Temporal/Playwright/model clients confinados a infrastructure.
- Delivery sólo traduce protocolo <-> use cases.
- Sin ciclos de dependencias ni god services.

Checklist frontend:
- Views sin fetch/WebSocket/reglas de negocio.
- ViewModels exponen state + commands.
- Application/use cases sin React.
- Infrastructure implementa API/realtime repositories.

Checklist CLI:
- `cli/` es Interface/Delivery; sólo consume el API público.
- No imports/calls directos desde CLI a Playwright, Temporal SDK, LangGraph, PostgreSQL, Redis, vLLM/AirLLM.
- No duplica business/QA verification logic que pertenece a Domain/Application; sólo authoring/validation local de contratos y presentación/orquestación cliente.
- JSON/exit-code/TestPlan/FailureBundle contracts permanecen versionados y testeados.

Checklist transversal:
- Model routing mediante port.
- Redis no es durable truth.
- Side effects recuperables e idempotency ownership explícito.
- `wait`/disconnect de un cliente no controla implícitamente el lifecycle durable.
- Failure/evidence bundles no mezclan provenance de runs/evidence sets/versiones.

Entregar hallazgos por severidad con archivo/línea, razón, regla violada y corrección mínima. Si está limpio, decir explícitamente qué checks se ejecutaron.
