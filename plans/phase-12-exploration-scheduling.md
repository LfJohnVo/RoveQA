# Phase 12 — Autonomous Exploration + Scheduling

## Objective
Explorar bounded state space y programar regresiones periódicas.

## Tasks
1. Exploration policy: max actions/time/depth/origins/destructive actions.
2. Visited/unvisited state frontier.
3. Novelty/fingerprint based exploration.
4. Temporal schedules for recurring runs.
5. Compare current findings/state map vs baseline.
6. Stop conditions and budget reporting.

## Gates
- Exploration termina por budgets/goal; no loop infinito.
- Scheduled run survives service restart.
- New/changed states generate useful report without blindly flagging all DOM changes.
