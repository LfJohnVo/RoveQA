# Redis is ephemeral coordination

Status: Accepted

## Context
La plataforma debe permanecer ligera, durable y reemplazable por adapters.

## Decision
Redis se usa para locks, semáforos, caches, presence y realtime streams. La pérdida total de Redis no puede destruir la verdad durable de un run.

## Consequences
La implementación y tests deben respetar esta separación. Cualquier cambio sustancial requiere un ADR superseding.
