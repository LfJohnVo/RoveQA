# Phase 13 — Chaos, Security and Observability Hardening

## Objective
Demostrar recuperación multi-hour, contratos agent-first robustos y controles de seguridad bajo fallos reales/hostiles.

## Tasks
1. Fault injection harness.
2. Kill worker, Chromium, Redis, vLLM during representative runs.
3. Temporary DB/network failures where safe.
4. Prompt-injection fixture pages.
5. Secret/redaction review.
6. OpenTelemetry dashboards/queries baseline.
7. Performance profile for checkpoints/artifacts/context compaction.
8. CLI detach/recovery chaos: kill/Ctrl-C `roveqa run wait`; durable run continúa y un nuevo CLI puede retomar wait.
9. Lost-response/idempotency chaos: drop ACK de run trigger; retry con misma key no duplica run/side effects.
10. FailureBundle corruption matrix: cross-run/cross-evidence/cross-plan-version/hash mismatch/partial write deben ser rechazados.
11. Runtime-response validation fault fixtures: 2xx malformed nunca produce success envelope.
12. JSON stdout purity matrix para success/errors/debug/progress/signals.
13. Bounded-resource tests: histories/steps/response bodies/plan size/file inputs no pueden crecer/leer sin límite.
14. Agent-budget fixtures: assertions OR/multi-branch y journeys excesivos deben terminar con classification clara (`plan`/`agent_budget`/`inconclusive`) en vez de false product failure.
15. File-read security tests para CLI inputs: missing file, directory, oversized file, secret file misuse/path policy cuando corresponda.
16. Adaptive-memory chaos: kill FalkorDB/Graphiti during retrieval/consolidation, verify pending sync/fallback, rebuild from empty graph.
17. Memory poisoning/staleness matrix: cross-project candidate, prompt-injection candidate, model hypothesis, fingerprint mismatch, contradicted playbook y secret-bearing payload deben rechazarse/revalidarse según policy.

## Gates
- Recovery matrix documented and green for supported failures.
- Redis flush test green.
- Prompt injection cannot escape RunPolicy.
- No critical secrets in logs/artifacts test fixture.
- CLI termination/timeout nunca cancela implícitamente un run.
- Replayed mutation con same idempotency identity no duplica side effects.
- FailureBundle integrity rejects mixed provenance and never exposes incomplete bundles as complete.
- Machine JSON output remains valid on every tested error path.
- Large/adversarial inputs are bounded by explicit limits rather than process memory/disk accident.
- Graph loss/outage degrades optimization only and rebuild restores learned projection.
- Poisoned/stale/cross-tenant memory cannot influence planner as trusted context.

## Required skills
- `systematic-debugging` for discovered failures
- `error-handling-patterns`
- `api-design-principles` for CLI/API contract hardening
- `postgresql` for DB reliability/performance/idempotency findings
- `vercel-react-best-practices` for frontend performance findings
- `adaptive-memory-graph`
- `durability-review`
