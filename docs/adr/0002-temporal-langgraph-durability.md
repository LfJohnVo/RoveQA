# Temporal + LangGraph persistence

Status: Accepted

## Context
La plataforma debe permanecer ligera, durable y reemplazable por adapters.

## Decision
Temporal posee lifecycle durable del run. LangGraph posee state machine cognitiva y checkpoints persistidos en PostgreSQL. No son sustitutos entre sí.

## Consequences
La implementación y tests deben respetar esta separación. Cualquier cambio sustancial requiere un ADR superseding.
