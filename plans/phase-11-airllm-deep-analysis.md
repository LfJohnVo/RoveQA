# Phase 11 — AirLLM Deep Analysis

## Objective
Añadir cold/deep analysis y failure triage sin ralentizar cada browser step ni gastar modelos grandes en fallos duplicados/cascada.

## Tasks
1. AirLLM adapter tras ModelGateway.
2. Task routing: run critique, root cause, deep plan, memory consolidation.
3. Implementar **deterministic failure triage first**: agrupar fallos por señales estructurales antes de enviar clusters al modelo (failure kind, HTTP/route error, target fingerprint, shared failed criterion/action, known producer/setup failure, normalized deterministic observation).
4. Elegir un representative run/failure por cluster y conservar member run IDs/confidence/reason de agrupación.
5. Enviar a AirLLM sólo representative/contexto agregado cuando análisis semántico aporte valor; nunca descargar/inyectar automáticamente todos los videos/traces del cluster.
6. Distinguir cascada: si falla setup/auth/producer compartido, downstream failures quedan marcados `blocked_downstream` o equivalente y no se contabilizan como defects independientes.
7. Trigger deep analysis at episode/run boundaries and repeated-failure conditions.
8. Async/durable activity con heartbeat y long timeout.
9. Store only outputs/summaries and invocation metadata needed; conservar deterministic cluster evidence separado de la interpretación LLM.

## Gates
- Browser loop funciona si AirLLM no está disponible salvo tarea explícitamente deep-required.
- Deep analysis puede reanudarse/reintentarse sin corromper run.
- Un lote de failures duplicados/cascada puede reducirse a clusters/representatives sin LLM.
- Si AirLLM está deshabilitado, deterministic triage sigue siendo útil y reproducible.
- Una hipótesis de cluster generada por modelo no reemplaza los member IDs/evidence que justifican el cluster.

## Required skills
- `prompt-engineering-patterns`
- `error-handling-patterns`
- `durability-review`
