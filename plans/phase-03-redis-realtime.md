# Phase 03 — Redis Coordination + Realtime

## Objective
Añadir locks, semáforos, presence y run event streams sin convertir Redis en source of truth.

## Tasks
1. LockManager port + Redis adapter con TTL/ownership token.
2. ResourceSemaphore para model/browser slots.
3. Redis Stream publisher/consumer y WebSocket fanout.
4. REST event catch-up desde durable events.
5. Redis restart/flush integration test.

## Gates
- UI/client puede reconectar y recuperar baseline durable.
- Redis loss no cambia resultados ya confirmados de un run.
- Locks expiran/renuevan con ownership seguro.
