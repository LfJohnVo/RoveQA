# Phase 05 — LangGraph Agent Core

## Objective
Agent loop durable usando un FakeModelGateway determinista inicialmente.

## Tasks
1. Agent state schema mínimo.
2. Nodes Observe/Retrieve/Plan/Act/Verify/Recover/Checkpoint/CloseEpisode.
3. PostgreSQL-backed checkpointer.
4. Context compaction y EpisodeSummary.
5. Fake planner/action model para tests reproducibles.
6. Temporal Activity que ejecuta/resume graph con heartbeat.
7. Kill/restart test durante run multi-step.

## Gates
- Run retoma desde último safe checkpoint.
- Active context no crece linealmente con steps.
- No duplicate side effect en crash window test.
