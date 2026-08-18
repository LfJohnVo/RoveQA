# Claude Code Operating Procedure

## Session start
1. Start Claude Code at repository root.
2. Read `CLAUDE.md`, `docs/status/PROGRESS.md`, and `docs/status/HANDOFF.md`.
3. Read `docs/21-claude-skill-routing.md` when the task crosses multiple specialties.
4. If no phase is in progress, invoke `/implement-phase XX` for the desired phase.
5. If a phase is already in progress, use `prompts/CONTINUE_SESSION.md` rather than restarting it from scratch.

## Process skills
- `/brainstorming`: close an unresolved design/behavior decision before implementation.
- `/systematic-debugging`: root-cause-first workflow for bugs, crashes and unexpected test failures.

## Architecture and implementation skills
- `/implement-phase XX`: orchestrates one roadmap phase and stops at its gate.
- `/backend-slice <scope>`: implement a backend vertical slice.
- `/frontend-mvvm-slice <scope>`: implement a frontend MVVM slice.
- `/browser-runtime <scope>`: work on Playwright/browser mechanics.
- `/api-design-principles`: HTTP/FastAPI/CLI contracts, idempotency and evolution.
- `/error-handling-patterns`: error taxonomy, mapping, retries, wait/cancel semantics and graceful degradation.
- `/postgresql`: durable schema, migrations, transactions, indexes and query review.
- `/prompt-engineering-patterns`: prompts, structured outputs, evals and prompt-injection boundaries.
- `/adaptive-memory-graph`: Graphiti/FalkorDB, knowledge candidates, retrieval, playbooks, feedback, invalidation, rebuild y memory benchmarks.

## Frontend design skills
- `/interface-design`: product interface hierarchy, tokens, states and persistent design memory.
- `/frontend-design`: visual craft and production-grade frontend implementation.
- `/vercel-react-best-practices`: React performance, effects, data loading, bundles and rendering.

## Review and release skills
- `/architecture-guard`: review dependency boundaries, including CLI->API-only boundary.
- `/durability-review`: review crash/retry/idempotency/wait behavior.
- `/test-and-verify`: final gate before marking work complete.
- `/changelog-generator`: generate auditable release notes from actual Git history after gates pass.

## Skill ordering
Use process skills first, implementation/specialist skills second, and verification skills last. A test failure encountered during implementation switches the task to `systematic-debugging` until root cause is known.

## Subagents
Use subagents for bounded parallel or specialist work, not as independent architects making conflicting decisions.

Recommended delegation:
- `architect`: read-only design review.
- `backend-engineer`: isolated backend slice; loads API/error/PostgreSQL guidance.
- `frontend-engineer`: isolated frontend slice; loads interface/frontend/Vercel React guidance.
- `cli-engineer`: TypeScript agent-first CLI, schemas, JSON/exit-code/idempotency/wait/failure-bundle client contracts.
- `knowledge-engineer`: adaptive runtime memory, Graphiti/FalkorDB projection, durable candidates, embeddings, retrieval/invalidation y cold-vs-warm evals.
- `browser-engineer`: Playwright/recovery work.
- `durability-engineer`: Temporal/checkpoint/retry work.
- `qa-reviewer`: read-only acceptance/test review.
- `devops-engineer`: Compose, healthchecks and runtime configuration.

Do not delegate two agents to modify the same files concurrently unless the user explicitly accepts merge conflict risk.

## Context control
Keep `CLAUDE.md` concise. Task-specific procedures belong in skills. Path-specific conventions belong in `.claude/rules/`. Durable project progress belongs in `docs/status/HANDOFF.md`, not only in conversation history.

## End of phase
1. Run all phase gates.
2. Run architecture review.
3. Run durability review when applicable.
4. Update progress and handoff.
5. Stop; do not silently begin the next phase.
