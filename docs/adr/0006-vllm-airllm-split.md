# Fast and deep inference split

Status: Accepted

## Context
La plataforma debe permanecer ligera, durable y reemplazable por adapters.

## Decision
vLLM atiende decisiones rápidas/structured outputs; AirLLM se reserva para deep/cold analysis y no cada browser action.

## Consequences
La implementación y tests deben respetar esta separación. Cualquier cambio sustancial requiere un ADR superseding.
