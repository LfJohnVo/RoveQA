# Implementation Roadmap

| Phase | Resultado | Gate principal |
|---|---|---|
| 00 | Repo/tooling/docs baseline | lint/test commands reproducibles |
| 01 | Domain + PostgreSQL foundation | migrations + domain tests |
| 02 | Run API + Temporal lifecycle | durable start/pause/resume/cancel |
| 03 | Redis coordination/realtime | locks/streams survive Redis loss semantically |
| 04 | Playwright browser gateway | typed actions + evidence + recovery basics |
| 05 | LangGraph agent loop | durable checkpoints + deterministic fake model |
| 06 | vLLM model adapter/router | structured model outputs + concurrency control |
| 07 | User story QA workflow | story -> plan -> run -> findings/report |
| 08 | Agent-first CLI + verification contracts | stable JSON/exit codes + atomic failure bundle + idempotent run loop |
| 09 | Adaptive QA Learning Graph | Graphiti/FalkorDB + verified feedback + rebuild + cold/warm benchmark |
| 10 | React MVVM control UI | projects/runs/live timeline/actions |
| 11 | AirLLM deep analysis | episode/run critique on cold path |
| 12 | Exploration + scheduled regression | autonomous bounded exploration |
| 13 | Chaos/security/observability hardening | multi-hour recovery suite |
| 14 | Release candidate | docs/runbooks/perf baseline |

Regla: ninguna fase debe introducir una dependencia futura sólo para “preparar” sin un use case real de esa fase.
