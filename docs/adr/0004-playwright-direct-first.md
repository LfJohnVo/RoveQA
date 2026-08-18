# Playwright direct first, MCP adapter optional

Status: Accepted

## Context
La plataforma debe permanecer ligera, durable y reemplazable por adapters.

## Decision
Runtime ejecuta Playwright mediante un BrowserGateway propio. MCP es adapter opcional para interoperabilidad, no una dependencia del Domain ni del loop principal.

## Consequences
La implementación y tests deben respetar esta separación. Cualquier cambio sustancial requiere un ADR superseding.
