# Graph Report - roveqa  (2026-08-20)

## Corpus Check
- 532 files · ~229,745 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 6183 nodes · 15946 edges · 457 communities (400 shown, 57 thin omitted)
- Extraction: 79% EXTRACTED · 21% INFERRED · 0% AMBIGUOUS · INFERRED: 3306 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `916faed3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- BrowserAction
- FilesystemArtifactRepository
- NotFoundError
- properties
- devDependencies
- InMemoryResourceSemaphore
- LockManager
- memory-context.schema.json
- AsyncClient
- InvalidEntityError
- RunPolicy
- properties
- properties
- UnitOfWork
- run_policy.py
- RunActivities
- PlanningRequest
- test_policy_resolution.py
- CriterionOutcome
- test_graph.py
- postgres/repositories.py
- postgres_test_dsn
- langgraph/graph.py
- test_realtime.py
- ScriptedModelGateway
- null
- compilerOptions
- ActionTarget
- FailureSignal
- CriterionResult
- PostgresUnitOfWork
- ClusterHypothesis
- InMemoryUnitOfWork
- null
- properties
- Container
- properties
- conftest.py
- Repositories
- RunTransitionError
- properties
- compilerOptions
- PlaywrightBrowserGateway
- container.py
- required
- test_api_contract.py
- properties
- properties
- GraphitiMemoryProjection
- sync_pending
- AlreadyExistsError
- FailureKind
- root_cause_hypothesis
- budget
- enum
- required
- projects.py
- unit_of_work_factory
- test_gateway.py
- VLLMModelGateway
- enum
- properties
- deny
- test-plan.schema.json
- plugins
- experience.py
- PostgresFailureClusterRepository
- worker.py
- test_layer_boundaries.py
- RuntimeError
- Quality
- KnowledgeExperienceCandidate
- browser-action.schema.json
- properties
- properties
- validity
- items
- env.py
- ModelEndpoint
- main.ts
- list_run_events.py
- contracts.py
- vllm/gateway.py
- type
- properties
- cli-envelope.schema.json
- required
- enum
- properties
- provenance
- CandidateKind
- test_schema_constraints.py
- properties
- properties
- CandidateStatus
- cli/package.json
- NewRunEvent
- AnalyzeFailuresCommand
- enum
- recommended_fix_target
- enum
- type
- ResourceSemaphore
- properties
- enum
- provenance
- enum
- enum
- enum
- select
- test_schedules_api.py
- test_health.py
- errors.ts
- agent-action.schema.json
- enum
- required
- enum
- error
- failure-bundle.schema.json
- seed_project_with_default_policy
- type
- side_effect
- required
- items
- enum
- TemporalScheduleGateway
- verification_strategy
- expected_postconditions
- message
- type
- freshness
- reliability
- to_document
- summary
- description
- environment_id
- name
- run_policy_id
- source_story_id
- TestPlan
- action_id
- test_client.py
- Adaptive QA Learning Graph
- frontend/tsconfig.json
- ci-local.sh
- validate-blueprint.sh
- HANDOFF.md
- from_document
- redact_payload
- routers/memory.py
- commands/run.ts
- derive_verdict
- routers/schedules.py
- PageState
- exploration_outcome
- Frontier
- compatibility_of
- contradicted_by
- test_memory_api.py
- Affordance
- apply_feedback
- test_temporal_workflow.py
- test_exploring_graph.py
- schemas.ts
- contracts/test_plan.py
- PlanBudget
- LockHandle
- agentic-qa
- page
- compilerOptions
- test_operational_queries.py
- api.ts
- agent.ts
- diff.ts
- parse_affordances
- InferenceMetrics
- test_deep_analyst.py
- commands/memory.ts
- Patterns adopted
- client.ts
- MemoryMetrics
- test_deep_analysis_activity.py
- test_memory_benchmark.py
- API and Event Contracts
- ports/gateways.ts
- test_database_failure.py
- bundle.test.ts
- flaky.ts
- Runtime responsibilities
- dependencies
- MemoryContextRequest
- envelope.test.ts
- routers/exploration.py
- policy
- Combination rules
- test_deep_analysis_real_model.py
- Settings
- ExplorationProgress
- test_memory_in_the_prompt.py
- TestOneDeterministicDisagreementWithdrawsIt
- Bounded contexts
- runs/run.ts
- test_evidence_chain.py
- test_triage_from_a_real_run.py
- Agent-First CLI Design
- Operations Runbook
- RunGateway
- safe_url
- test_exploring_a_real_run.py
- test_learning_from_a_real_run.py
- envelope.ts
- include
- properties
- required
- Product Spec
- frontend/tsconfig.test.json
- Phase 08 — Agent-First CLI and Verification Contracts
- Durability and Recovery
- Inference Layer
- Knowledge Graph
- Claude Code Operating Procedure
- run-page.test.tsx
- TestUserStory
- TestWhatItDeclinedToTake
- Claude Code Project Instructions
- Data and Artifacts
- Testing Strategy
- ADR 0008 — Adaptive QA Learning Graph with Graphiti + FalkorDB
- HttpRunGateway
- FakeRunGateway
- Agentic Web QA — Claude Code Build Kit
- Session Handoff
- Interface System
- Security Model
- Observability
- Development-Time Codebase Graph (Graphify)
- Memory Evaluation — reach the records page
- Release Checklist
- run-events.ts
- Memory Evaluation — <flow>
- normalize_origin
- API design principles
- Error handling patterns
- doctor.ts
- Agent Runtime
- Docker Compose Topology
- ADR 0009 — Run workflow shape, retry ownership and checkpoint reconciliation
- memory-page.test.tsx
- findings.ts
- v1.0.0-rc — 2026-08-20
- Graphify — codebase graph workflow
- PostgreSQL
- Prompt engineering patterns
- cli/test/boundaries.test.ts
- contract-examples.test.ts
- Browser Runtime
- Redis Contract
- scripts
- watch-run.ts
- HttpStoryGateway
- use-projects-viewmodel.ts
- use-run-viewmodel.ts
- stories-page.test.tsx
- Phase 06 — vLLM + Model Router
- Phase 09 — Adaptive QA Learning Graph (Graphiti + FalkorDB)
- demo.sh
- Interface design
- Ponytail — minimal safe engineering
- Systematic debugging
- Backend Clean Architecture
- Frontend — Clean Architecture + MVVM
- ADR 0010 — Transaction ownership: commands own a UnitOfWork, queries take repositories
- Performance Profile
- Recovery Matrix
- frontend/package.json
- timeline.ts
- FakeStoryGateway
- Phase 01 — Domain + PostgreSQL Foundation
- Phase 02 — Run API + Temporal Lifecycle
- Phase 04 — Browser Gateway
- Phase 07 — User Story QA Workflow
- Phase 10 — React MVVM Control UI
- Phase 11 — AirLLM Deep Analysis
- Phase 13 — Chaos, Security and Observability Hardening
- Phase 14 — Release Candidate
- soak.sh
- [Decision title]
- content_version
- Frontend design
- Vercel React best practices
- roveqa CLI
- ci-adapter.test.ts
- items
- MCP Strategy
- Clean Architecture + MVVM
- Temporal + LangGraph persistence
- Redis is ephemeral coordination
- Playwright direct first, MCP adapter optional
- Filesystem artifacts first
- Fast and deep inference split
- Agent-first CLI contracts, not TestSprite runtime dependency
- knowledge/memory.ts
- story.ts
- stories-page.tsx
- Phase 00 — Repository Bootstrap
- Phase 03 — Redis Coordination + Realtime
- Phase 05 — LangGraph Agent Core
- Phase 12 — Autonomous Exploration + Scheduling
- reset_test_schema.py
- .__aexit__
- Brainstorming
- Changelog generator
- bundle-contracts.mjs
- Third-Party Agent Tooling
- Official References
- React + TypeScript + Vite
- use-memory-viewmodel.ts
- use-run-report-viewmodel.ts
- findings-list.tsx
- start-run-page.tsx
- FakeProjectGateway
- FakeRunEventStream
- Continue RoveQA with Opus 5
- verdict-to-junit.mjs
- Contract examples
- Definition of Done
- connection.ts
- viewmodels/gateways.ts
- connection-indicator.tsx
- verdict-badge.tsx
- run-page.tsx
- backup.sh
- restore.sh
- backend.md
- cli.md
- frontend.md
- knowledge.md
- temporal.md
- testing.md
- adaptive-memory-graph/SKILL.md
- architecture-guard/SKILL.md
- backend-slice/SKILL.md
- browser-runtime/SKILL.md
- durability-review/SKILL.md
- frontend-mvvm-slice/SKILL.md
- graphify/references/upstream.md
- implement-phase/SKILL.md
- ponytail/references/upstream.md
- test-and-verify/SKILL.md
- 17-implementation-roadmap.md
- adr/README.md
- PROGRESS.md
- eslint-plugin-react-hooks
- ci/README.md
- eslint
- jsdom
- @testing-library/react
- @testing-library/user-event
- typescript-eslint
- vite
- vitest
- project.ts
- plans/README.md
- CONTINUE_SESSION.md
- PHASE_REVIEW.md
- START_HERE.md

## God Nodes (most connected - your core abstractions)
1. `KnowledgeExperienceCandidate` - 172 edges
2. `RunPolicy` - 172 edges
3. `Run` - 157 edges
4. `CriterionResult` - 146 edges
5. `NotFoundError` - 142 edges
6. `UnitOfWork` - 138 edges
7. `Project` - 119 edges
8. `Verdict` - 114 edges
9. `BrowserAction` - 112 edges
10. `InvalidEntityError` - 105 edges

## Surprising Connections (you probably didn't know these)
- `repository()` --indirect_call--> `relative()`  [INFERRED]
  cli/test/agent.test.ts → frontend/test/boundaries.test.ts
- `AnalyzeFailuresCommand` --uses--> `AlreadyExistsError`  [INFERRED]
  backend/src/agentic_qa/application/commands/analyze_failures.py → backend/src/agentic_qa/application/errors.py
- `AnalyzeFailuresCommand` --uses--> `NotFoundError`  [INFERRED]
  backend/src/agentic_qa/application/commands/analyze_failures.py → backend/src/agentic_qa/application/errors.py
- `AnalyzeFailuresCommand` --uses--> `AnalyzedCluster`  [INFERRED]
  backend/src/agentic_qa/application/commands/analyze_failures.py → backend/src/agentic_qa/application/ports/deep_analysis.py
- `AnalyzeFailuresCommand` --uses--> `DeepAnalyst`  [INFERRED]
  backend/src/agentic_qa/application/commands/analyze_failures.py → backend/src/agentic_qa/application/ports/deep_analysis.py

## Import Cycles
- None detected.

## Communities (457 total, 57 thin omitted)

### Community 0 - "BrowserAction"
Cohesion: 0.05
Nodes (56): ActionOutcome, Browser gateway port.  Application asks for typed actions and never touches Pl, What actually happened, kept separate from what was intended., ActionDeniedError, Exception, A browser gateway that cannot execute what the policy forbids.  Enforcement li, The run policy forbade an action; it was never executed., BrowserAction (+48 more)

### Community 1 - "FilesystemArtifactRepository"
Cohesion: 0.07
Nodes (31): ArtifactTooLargeError, Exception, The artifact exceeded the configured cap and was not stored., EvidenceContaminationError, EvidenceSet, A manifest was asked to hold artifacts that do not share one provenance., Artifacts captured under one run and one coherent context., PageFingerprint (+23 more)

### Community 2 - "NotFoundError"
Cohesion: 0.04
Nodes (76): ArtifactRepositoryDep, compile_plan(), CompilePlanCommand, _next_version(), Compile a user story into a stored, versioned TestPlan.  Versioning is the point, Monotonic integers as strings. The contract allows any string; sequential     in, create_story(), CreateStoryCommand (+68 more)

### Community 3 - "properties"
Cohesion: 0.04
Nodes (48): additionalProperties, default, type, default, type, items, type, default (+40 more)

### Community 4 - "devDependencies"
Cohesion: 0.11
Nodes (19): eslint-plugin-react-refresh, devDependencies, @eslint/js, eslint-plugin-react-refresh, globals, @testing-library/jest-dom, @types/node, @types/react (+11 more)

### Community 5 - "InMemoryResourceSemaphore"
Cohesion: 0.13
Nodes (9): Take a slot, or None when the resource is already at capacity., Extend a held slot. False when the lease already lapsed., Give the slot back. False when this reservation no longer holds one., SlotReservation, _millis(), Redis, Redis resource semaphore.  One sorted set per resource: members are reservation, RedisResourceSemaphore (+1 more)

### Community 6 - "LockManager"
Cohesion: 0.13
Nodes (17): LockManager, Protocol, Distributed lock port.  Locks are coordination, never truth (docs/09, ADR 0003):, Return a handle, or None when the lock is already held., Extend the lease. False when the token no longer owns the key., Release only if still the owner. False when the token no longer owns it., Lock manager contract.  The ownership tests are the point: a holder whose lease, The classic distributed-lock bug, asserted rather than assumed.      A GET-then- (+9 more)

### Community 7 - "memory-context.schema.json"
Cohesion: 0.17
Nodes (11): additionalProperties, $id, environment_id, project_id, schema_version, required, $schema, title (+3 more)

### Community 8 - "AsyncClient"
Cohesion: 0.10
Nodes (15): create_project(), AsyncClient, The API signals intent; only the workflow's activities write status., Durable status follows the workflow, never the request that asked for it., The request hands the run to the durable engine and returns immediately., Durable catch-up: what a client replays after losing its live connection., A story is not write-only.      Phase 07 could create one and compile it; noth, Create a project with a default run policy: a run cannot start without one. (+7 more)

### Community 9 - "InvalidEntityError"
Cohesion: 0.09
Nodes (15): Recurring runs.  A schedule is durable state, and it has exactly one owner: Temp, Evidence identity and provenance (docs/11).  An `EvidenceSet` is a coherent coll, InvalidEntityError, An entity was constructed with values its invariants forbid., What happens to knowledge after a later run uses it.  Consolidation writes wha, Environment: a deployment of the target application a run executes against., _reject_duplicates(), _require_step_id() (+7 more)

### Community 10 - "RunPolicy"
Cohesion: 0.09
Nodes (81): RunEvent, A recurring run, described the way the caller asked for it.      Carries the pla, RunSchedule, Project, RunPolicy, UserStory, _allowed_targets(), StrEnum (+73 more)

### Community 11 - "properties"
Cohesion: 0.06
Nodes (36): items, type, type, type, items, type, type, $id (+28 more)

### Community 12 - "properties"
Cohesion: 0.06
Nodes (30): items, type, type, $id, type, payload, run_id, type (+22 more)

### Community 13 - "UnitOfWork"
Cohesion: 0.03
Nodes (87): ArtifactIndex, Artifact storage port.  Filesystem today, S3/MinIO later (ADR 0005) — which is, Durable index of captured artifacts (docs/11: references in the database)., Recovery point repository port., Protocol, Append durably, assigning the next per-run sequence.          Called inside the, Events with sequence > after, ascending, capped at limit.          `after` is th, RunEventLog (+79 more)

### Community 14 - "run_policy.py"
Cohesion: 0.11
Nodes (17): EnvironmentRepository, Protocol, Repositories for environments and run policies., Persist a new policy. Raises AlreadyExistsError when the id is taken.          T, RunPolicyRepository, RunPolicy: the rules a run may not exceed (Projects bounded context).  Mirrors `, Boom, Exception (+9 more)

### Community 15 - "RunActivities"
Cohesion: 0.15
Nodes (11): Run, Execute one episode of the agent loop.          The activity stays thin: it re, Store what an exploration mapped, or nothing for a planned episode.          N, What earlier runs learned about this application, or nothing.          Failure, Turn a finished run into durable knowledge. Returns how many candidates hold., Bring the graph projection up to date. Returns how many nodes it wrote., Persist criterion results and derive the run's verdict from them.          The, Record the artifacts the episode captured.          The bytes were already wri (+3 more)

### Community 16 - "PlanningRequest"
Cohesion: 0.05
Nodes (66): main(), prompt_for(), Measure what grows, and print it.  Run inside the gates container:      dock, run_for(), table_sizes(), test_dsn(), PlanningRequest, Model gateway port.  The agent asks for a decision and receives a *typed* acti (+58 more)

### Community 17 - "test_policy_resolution.py"
Cohesion: 0.38
Nodes (10): make_policy(), RunPolicy resolution order (docs/12).  A run without a resolved policy has no or, seed(), test_a_policy_from_another_project_is_refused(), test_an_environment_of_another_project_is_refused(), test_no_policy_anywhere_fails_instead_of_defaulting(), test_the_environment_default_comes_before_the_project_default(), test_the_project_default_is_the_last_resort() (+2 more)

### Community 18 - "CriterionOutcome"
Cohesion: 0.07
Nodes (33): Index one artifact. Idempotent by artifact id., Resolve an id to its reference. Downloads go through this, so an id is, Protocol, The newest safe point, which is where a resume validates against., Newest first, bounded — a long run must not be read unboundedly., RecoveryPointRepository, Persist a new environment. Raises AlreadyExistsError when the id is taken., EvidenceRef (+25 more)

### Community 19 - "test_graph.py"
Cohesion: 0.17
Nodes (22): AlwaysFailingBrowser, click(), navigate(), Any, Agent graph behaviour over deterministic doubles.  The graph depends on the br, The summary of an unrecoverable episode says it failed, and says why., Outcomes are observed per step, so a recovered failure is still visible., Nodes decide when a moment is safe; persisting it happens outside the graph. (+14 more)

### Community 20 - "postgres/repositories.py"
Cohesion: 0.06
Nodes (55): MemoryFeedback, _budget_to_domain(), criterion_result_to_domain(), criterion_result_to_model(), environment_to_domain(), environment_to_model(), feedback_to_domain(), feedback_to_model() (+47 more)

### Community 21 - "postgres_test_dsn"
Cohesion: 0.11
Nodes (24): counting_graph(), CountingState, Any, TypedDict, LangGraph's PostgreSQL checkpointer against the real database.  The resume path, The domain stores this id on a RecoveryPoint, so it must be retrievable., Two drivers, one database: the translation lives in one place., The durability claim a worker restart depends on.      State is written with one (+16 more)

### Community 22 - "langgraph/graph.py"
Cohesion: 0.05
Nodes (60): AsyncPostgresSaver, ArtifactRepository, Protocol, Persist one artifact and return its identity, hash and size., Read an artifact back, verifying it still matches its recorded hash., BrowserGateway, Protocol, Capture the page as it is now.          A capability rather than an action out (+52 more)

### Community 23 - "test_realtime.py"
Cohesion: 0.11
Nodes (22): BrokenRunEventPublisher, InMemoryRunEventPublisher, InMemoryRunEventSubscription, RunEvent, In-memory run event publisher with the same delivery semantics as Redis., Realtime transport is down; the run must not notice., build_container(), client() (+14 more)

### Community 24 - "ScriptedModelGateway"
Cohesion: 0.08
Nodes (46): _check_deterministically(), _criterion_of(), _judge_semantically(), _labelled(), FailureKind, PlanStep, Evaluate a plan's acceptance criteria against the page the run ended on.  The, Keep the model's words visibly the model's, next to what was actually seen. (+38 more)

### Community 25 - "null"
Cohesion: 0.11
Nodes (26): type, null, string, format, type, type, description, type (+18 more)

### Community 26 - "compilerOptions"
Cohesion: 0.05
Nodes (38): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, exactOptionalPropertyTypes, jsx, lib, module (+30 more)

### Community 27 - "ActionTarget"
Cohesion: 0.04
Nodes (94): ActionTarget, Semantic locator. Coordinates are deliberately absent from v1., BrowserSession, BaseException, Self, TracebackType, Owns the Playwright process and browser for the life of a run., Launch Chromium with an isolated context, optionally restoring auth state. (+86 more)

### Community 28 - "FailureSignal"
Cohesion: 0.05
Nodes (46): DeepAnalysisService, Decides which clusters are worth a large model, and asks about those only., _build_cluster(), _cluster_id(), ClusterStatus, StrEnum, Grouping failures, and telling causes apart from consequences.  Two jobs, both, What is worth sending to a model, if anything is.          Only independent cl (+38 more)

### Community 29 - "CriterionResult"
Cohesion: 0.04
Nodes (44): Store one exploration's map and what it spent.          Idempotent per `(run_id,, Store results for a run, replacing any previous answer for the same criteria., The criterion a report leads with. Deterministic failures come first,         b, Only reproducible product failures. This is what a bug report may cite., The states one exploration reached, keyed by signature., StateMap, ExplorationReport, What the run spent and what it found. Rendered for a human, read by a diff. (+36 more)

### Community 30 - "PostgresUnitOfWork"
Cohesion: 0.11
Nodes (4): PostgresUnitOfWork, BaseException, Self, TracebackType

### Community 31 - "ClusterHypothesis"
Cohesion: 0.05
Nodes (48): AnalyzeFailuresResult, _freshness_rule(), datetime, Analyse a finished run's failures: group first, ask a model second, store both., Ask about a cluster only when the answer could have changed.      This is the, Reduce stored results to comparable signals, dropping what cannot be grouped., _signals(), _store_hypotheses() (+40 more)

### Community 32 - "InMemoryUnitOfWork"
Cohesion: 0.13
Nodes (5): uow(), InMemoryUnitOfWork, BaseException, Self, TracebackType

### Community 33 - "null"
Cohesion: 0.12
Nodes (22): maxLength, type, description, pattern, type, type, null, object (+14 more)

### Community 34 - "properties"
Cohesion: 0.09
Nodes (22): minLength, type, format, type, minLength, type, type, type (+14 more)

### Community 35 - "Container"
Cohesion: 0.05
Nodes (52): ConsolidateExperienceResult, Consolidate a finished run into durable knowledge.  Runs once per run, enforce, Start a run, idempotently.  Ordering is the durability contract (ADR 0010): th, Pin the plan version now, or run without a plan (exploratory).      Resolving, _resolve_plan(), start_run(), StartRunCommand, StartRunResult (+44 more)

### Community 36 - "properties"
Cohesion: 0.10
Nodes (21): minLength, type, properties, minLength, type, artifact_id, kind, relative_path (+13 more)

### Community 37 - "conftest.py"
Cohesion: 0.15
Nodes (19): _ensure_schema(), lock_manager(), postgres_session(), postgres_session_scope(), AsyncEngine, AsyncSession, Redis, Shared fixtures.  `repositories` is parametrized over every repository impleme (+11 more)

### Community 38 - "Repositories"
Cohesion: 0.24
Nodes (9): Repositories, make_story(), Project, UserStory, Repository contract suite.  Every implementation of the ports must satisfy these, seed_project(), TestProjectRepository, TestRunRepository (+1 more)

### Community 39 - "RunTransitionError"
Cohesion: 0.16
Nodes (19): DomainError, Exception, Base for every violated domain invariant., A run lifecycle invariant was violated., RunTransitionError, make_run(), Run, RunStatus (+11 more)

### Community 40 - "properties"
Cohesion: 0.10
Nodes (20): minimum, type, minimum, type, contradiction_count, failure_count, quality, reliability (+12 more)

### Community 41 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+11 more)

### Community 42 - "PlaywrightBrowserGateway"
Cohesion: 0.09
Nodes (16): AriaRole, Exception, The gateway cannot carry out this action as described.      A fact about the *, UnperformableActionError, _aria_role(), PlaywrightBrowserGateway, Request, The viewport as it is now. Never the full page: a tall page produces an (+8 more)

### Community 43 - "container.py"
Cohesion: 0.06
Nodes (45): build_container(), connect_workflows(), Composition root.  The only place that knows both Application ports and Infras, Database-only container. Temporal needs an async connect, see `connect_workflows, _as_text(), _decode(), _encode(), _parse_read_reply() (+37 more)

### Community 44 - "required"
Cohesion: 0.11
Nodes (18): additionalProperties, $id, candidate_id, environment_id, kind, model_derived, observed, payload (+10 more)

### Community 45 - "test_api_contract.py"
Cohesion: 0.10
Nodes (22): LogRecord, RequestIdLogFilter, asgi_client(), captured_error_logs(), client(), ExplodingUnitOfWork, LogRecord, HTTP contract: status codes, error envelope, request id and idempotency. (+14 more)

### Community 46 - "properties"
Cohesion: 0.11
Nodes (18): minLength, type, format, type, minLength, type, minLength, type (+10 more)

### Community 47 - "properties"
Cohesion: 0.11
Nodes (18): maxLength, minLength, type, default, type, properties, criterion_id, critical (+10 more)

### Community 48 - "GraphitiMemoryProjection"
Cohesion: 0.05
Nodes (47): EmbeddingGateway, Protocol, Embedding gateway port.  A separate port from `ModelGateway` because the two fai, Which model produced the vectors.          Recorded with the projection: embeddi, Vectors in the same order as the inputs.          Raises rather than returning s, _as_texts(), GraphitiEmbedder, GraphMemoryModelUseError (+39 more)

### Community 49 - "sync_pending"
Cohesion: 0.08
Nodes (29): _failure(), datetime, UnitOfWorkFactory, Keep the graph projection in step with durable knowledge.  One queue, one dire, Rebuild one project's projection from durable knowledge.      The recovery pat, Committed per entry, not per batch: an interrupted pass must keep the progress, Drain the backlog once. Safe to call repeatedly and safe to interrupt., rebuild_project() (+21 more)

### Community 50 - "AlreadyExistsError"
Cohesion: 0.10
Nodes (23): AlreadyExistsError, A repository rejected an insert because the identity is already taken.      Adap, IdempotencyRecord, Persist a record. Raises AlreadyExistsError when (scope, key) is taken., StrEnum, StopReason, ExplorationRunModel, ExploredStateModel (+15 more)

### Community 51 - "FailureKind"
Cohesion: 0.06
Nodes (45): PlannedAction, The planner's decision.      Three outcomes, deliberately distinguishable:, GuardedBrowserGateway, PlanStep, PlanStepType, steps_by_criterion(), FailureKind, StrEnum (+37 more)

### Community 52 - "root_cause_hypothesis"
Cohesion: 0.12
Nodes (17): maximum, minimum, type, model_derived, number, const, type, confidence (+9 more)

### Community 53 - "budget"
Cohesion: 0.12
Nodes (17): additionalProperties, minProperties, properties, type, maximum, minimum, type, maximum (+9 more)

### Community 54 - "enum"
Cohesion: 0.12
Nodes (16): enum, AUTH_REQUIRED, CONFIG_ERROR, CONFLICT, FORBIDDEN, INTERNAL_ERROR, NOT_FOUND, POLICY_DENIED (+8 more)

### Community 55 - "required"
Cohesion: 0.13
Nodes (16): required, evidence_set_id, kind, project_id, run_id, schema_version, required, artifact_id (+8 more)

### Community 56 - "projects.py"
Cohesion: 0.13
Nodes (20): create_project(), CreateProjectCommand, Project, Create a project.  Commands own their transaction and commit; queries take repos, create_run_policy(), CreateRunPolicyCommand, Create a run policy, optionally making it the project default.  Policies are imm, list_projects() (+12 more)

### Community 57 - "unit_of_work_factory"
Cohesion: 0.13
Nodes (25): consolidate_experience(), ConsolidateExperienceCommand, _invalidate_what_this_run_disproved(), datetime, Withdraw memory this run's deterministic results disprove.      The other half, Build fresh units of work over one shared store/database.      A factory rathe, unit_of_work_factory(), UnitOfWorkFactory (+17 more)

### Community 58 - "test_gateway.py"
Cohesion: 0.12
Nodes (23): Runtime configuration read from the environment.  Secrets never live in code o, In-memory resource semaphore with real lease expiry., build_gateway(), completion(), make_policy(), plan_once(), Any, The phase gate: invalid model output never reaches the browser.  These run the * (+15 more)

### Community 59 - "VLLMModelGateway"
Cohesion: 0.06
Nodes (34): CriterionJudgement, JudgementRequest, Ask a model whether an acceptance criterion looks satisfied.      Last in the, BrowserDecision, DecisionTarget, BaseModel, Semantic verification. Last in the priority order, never first (docs/06)., One step the model proposes. `finished=true` means it proposes nothing. (+26 more)

### Community 60 - "enum"
Cohesion: 0.13
Nodes (15): enum, assert_text, assert_url, back, check, click, extract, fill (+7 more)

### Community 61 - "properties"
Cohesion: 0.13
Nodes (15): maxLength, minLength, type, maxLength, minLength, type, maxLength, minLength (+7 more)

### Community 62 - "deny"
Cohesion: 0.14
Nodes (13): permissions, deny, $schema, Bash(docker system prune *), Bash(git push --force *), Bash(rm -rf / *), Read(./.env), Read(./.env.development) (+5 more)

### Community 63 - "test-plan.schema.json"
Cohesion: 0.14
Nodes (13): additionalProperties, anyOf, $comment, $id, project_id, schema_version, required, $schema (+5 more)

### Community 64 - "plugins"
Cohesion: 0.14
Nodes (10): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema, GatewaysContext, oxc, react (+2 more)

### Community 65 - "experience.py"
Cohesion: 0.08
Nodes (37): _item_document(), Any, The portable MemoryContext document (`contracts/memory-context.schema.json`).  O, to_document(), Retrieve the memory a run should start from.  The pipeline docs/26 asks for, in, Compatibility, _confirmed(), _differs() (+29 more)

### Community 66 - "PostgresFailureClusterRepository"
Cohesion: 0.11
Nodes (9): FailureClusterModel, One deterministic failure cluster for a project (Phase 11).      Identity is `, PostgresFailureClusterRepository, AsyncSession, datetime, Durable triage. Clusters accumulate across runs; hypotheses hang off them., Overwrite the derived fields, never `first_seen_at`.          Status and reaso, Add what is new. Members are never removed: a run that once hit this problem (+1 more)

### Community 67 - "worker.py"
Cohesion: 0.15
Nodes (12): Add the agent runtime. Worker-only: the API never plans or drives a browser., with_agent_runtime(), One workflow per run: the id makes a duplicate start a no-op, not a second run., workflow_id_for(), Client, Temporal adapter for the WorkflowGateway port., TemporalWorkflowGateway, build_worker() (+4 more)

### Community 68 - "test_layer_boundaries.py"
Cohesion: 0.31
Nodes (12): forbidden_imports(), imported_modules(), layer_files(), Path, The dependency rule is a test, not a review habit.      Interfaces/Delivery --, Policy enforcement lives in a wrapper, so the raw adapter must stay contained., A guard that cannot fail proves nothing: plant a violation and expect a catch., test_guard_allows_stdlib_and_own_layer() (+4 more)

### Community 69 - "RuntimeError"
Cohesion: 0.18
Nodes (5): async_sessionmaker, AsyncSession, FailingWorkflowGateway, Start fails after the run was committed — the recoverable case in ADR 0010., RuntimeError

### Community 70 - "Quality"
Cohesion: 0.08
Nodes (23): Provenance, datetime, Quality, Evidence counts and the reliability derived from them.      `reliability` is c, Successes against everything that went wrong, with contradictions counted, Where a candidate came from. Without it, nothing here can be audited., The context in which the knowledge held.      Retrieval hard-filters on these, Validity (+15 more)

### Community 71 - "KnowledgeExperienceCandidate"
Cohesion: 0.06
Nodes (25): GraphIngestion, Protocol, Write one candidate into the projection and return its node id.          Idempot, Bulk write used by rebuild, kept separate so a normal sync cannot accidentally, candidate_id -> node id, for those that made it. Partial success is normal, KnowledgeRepository, CandidateStatus, Store a candidate, folding it into an equivalent one when it already exists. (+17 more)

### Community 72 - "browser-action.schema.json"
Cohesion: 0.18
Nodes (10): additionalProperties, $id, intent, side_effect, type, required, $schema, title (+2 more)

### Community 73 - "properties"
Cohesion: 0.18
Nodes (11): type, type, label, name, role, text, url, type (+3 more)

### Community 74 - "properties"
Cohesion: 0.20
Nodes (11): type, type, properties, null, object, string, maxLength, type (+3 more)

### Community 75 - "validity"
Cohesion: 0.18
Nodes (11): valid_from, valid_to, last_verified_at, valid_from, valid_to, validity, additionalProperties, properties (+3 more)

### Community 76 - "items"
Cohesion: 0.18
Nodes (11): additionalProperties, required, type, description, type, items, maxItems, minItems (+3 more)

### Community 77 - "env.py"
Cohesion: 0.21
Nodes (12): do_run_migrations(), include_name(), Run migrations in 'online' mode., Alembic's own signature, spelled out.      It was loose enough that a type che, Run migrations in 'offline' mode.      This configures the context with just a, In this scenario we need to create an Engine     and associate a connection wit, run_async_migrations(), run_migrations_offline() (+4 more)

### Community 78 - "ModelEndpoint"
Cohesion: 0.07
Nodes (36): build_deep_analyst(), build_model_router(), AsyncClient, Redis, None when no endpoint is configured at all — an honest absence, not a fake model, None when nothing serves DEEP. Callers treat that as "no hypothesis", never as, InferenceBudget, ModelCapability (+28 more)

### Community 79 - "main.ts"
Cohesion: 0.14
Nodes (45): hasErrors(), lintPlan(), readPlanFile(), scaffoldPlan(), failureContext(), unclassified(), usage(), agentInstall() (+37 more)

### Community 80 - "list_run_events.py"
Cohesion: 0.13
Nodes (16): list_run_events(), RunEvent, Read the durable event log of a run.  This is the catch-up path a client uses af, container_from_websocket(), WebSocket, Separate from the HTTP version on purpose.      A `Request | WebSocket` union, WebSocket, Realtime run events over WebSocket.  Connect order matters and is the whole poin (+8 more)

### Community 81 - "contracts.py"
Cohesion: 0.15
Nodes (17): ConsolidateParams, EpisodeOutcome, Serializable payloads exchanged between workflow and activities.  Kept free of, What one firing of a schedule needs to create its run.      No run id: the run, One firing, with the key that makes it exactly one run.      `idempotency_key`, Nothing to carry: the backlog lives in PostgreSQL and names its own work., Result of one episode.      `more_work` is what ends the loop. Phase 05 replac, RunParams (+9 more)

### Community 82 - "vllm/gateway.py"
Cohesion: 0.10
Nodes (27): Bounded resource reservations (browser slots, model slots, accounts).  Every res, capability_for(), Inference task types and capabilities (docs/08).  The domain names *what kind of, TaskType, DeepAnalyst backed by AirLLM.  AirLLM runs a model far larger than the GPU by st, InferenceError, ModelOutputError, ModelUnavailableError (+19 more)

### Community 83 - "type"
Cohesion: 0.20
Nodes (10): items, type, items, type, type, items, type, artifact_refs (+2 more)

### Community 84 - "properties"
Cohesion: 0.20
Nodes (10): type, properties, intent, side_effect, target, type, value, type (+2 more)

### Community 85 - "cli-envelope.schema.json"
Cohesion: 0.20
Nodes (9): additionalProperties, $id, schema_version, oneOf, required, $schema, title, type (+1 more)

### Community 86 - "required"
Cohesion: 0.20
Nodes (10): valid_from, valid_to, validity, additionalProperties, required, type, app_version, origin (+2 more)

### Community 87 - "enum"
Cohesion: 0.20
Nodes (10): enum, acceptance_fact, api_relation, failure_signature, locator_hint, page_state, playbook, role_constraint (+2 more)

### Community 88 - "properties"
Cohesion: 0.12
Nodes (17): properties, minLength, type, minLength, type, description, type, description (+9 more)

### Community 89 - "provenance"
Cohesion: 0.20
Nodes (10): candidate_id, source_run_id, candidate_id, evidence_set_id, provenance, source_run_id, additionalProperties, properties (+2 more)

### Community 90 - "CandidateKind"
Cohesion: 0.13
Nodes (25): consolidate(), ConsolidationInput, ConsolidationOutcome, _from_result(), _origin_of(), datetime, Turn a finished run into knowledge candidates.  Only *verified* outcomes becom, Scheme and host, without the path. The origin is the part that decides whether (+17 more)

### Community 91 - "test_schema_constraints.py"
Cohesion: 0.35
Nodes (12): knowledge_values(), AsyncSession, The durable schema must defend the run invariants, not just the Python layer.  A, The rule the whole learning design rests on, defended below the Python layer., seed(), test_a_model_derived_candidate_cannot_be_trusted_in_the_database(), test_criterion_ids_are_unique_within_a_story(), test_knowledge_must_come_from_somewhere() (+4 more)

### Community 92 - "properties"
Cohesion: 0.22
Nodes (9): minLength, type, type, properties, intent, payload, type, minLength (+1 more)

### Community 93 - "properties"
Cohesion: 0.20
Nodes (10): type, evidence_set_id, source_episode_id, source_run_id, test_plan_version, properties, type, minLength (+2 more)

### Community 94 - "CandidateStatus"
Cohesion: 0.09
Nodes (20): GraphSyncRecord, GraphSyncState, GraphSyncStateRepository, MemoryFeedbackRepository, Protocol, StrEnum, Knowledge repository port.  PostgreSQL owns these rows; the graph is a project, The rebuild backlog: what the graph is missing, oldest first.          This is (+12 more)

### Community 95 - "cli/package.json"
Cohesion: 0.06
Nodes (34): ajv, bin, roveqa, dependencies, ajv, devDependencies, eslint, @eslint/js (+26 more)

### Community 96 - "NewRunEvent"
Cohesion: 0.21
Nodes (8): NewRunEvent, An event to append. The log assigns its sequence., Durable event journal. Redis Streams are a projection of this, never a source., RunEventModel, _event_to_domain(), PostgresRunEventLog, RunEvent, RunEvent

### Community 97 - "AnalyzeFailuresCommand"
Cohesion: 0.21
Nodes (17): analyze_failures(), AnalyzeFailuresCommand, CountingAnalyst, failure(), Factory, FailureKind, The run-boundary pass: group, ask, store — and survive being interrupted.  Par, Every finished run triggers a pass, so what stops a project with one standing (+9 more)

### Community 98 - "enum"
Cohesion: 0.25
Nodes (8): enum, agent_budget, environment, model, plan, policy, product, unknown

### Community 99 - "recommended_fix_target"
Cohesion: 0.25
Nodes (8): rationale, recommended_fix_target, reference, maxLength, type, additionalProperties, properties, maxLength

### Community 100 - "enum"
Cohesion: 0.25
Nodes (8): status, enum, candidate, invalidated, pending_sync, promoted, rejected, trusted

### Community 101 - "type"
Cohesion: 0.25
Nodes (8): type, null, number, string, additionalProperties, type, metadata, boolean

### Community 102 - "ResourceSemaphore"
Cohesion: 0.10
Nodes (29): Protocol, Slots currently held, excluding lapsed ones., ResourceSemaphore, Resource semaphore contract.  Capacity must hold under concurrency, and a worker, Check-then-add must be atomic: ten racing callers, two slots., A worker that died holding a slot must not shrink the pool forever., test_a_lapsed_slot_is_reclaimed(), test_capacity_is_not_exceeded() (+21 more)

### Community 103 - "properties"
Cohesion: 0.29
Nodes (7): properties, data, request_id, schema_version, minLength, type, const

### Community 104 - "enum"
Cohesion: 0.29
Nodes (7): verdict, enum, type, blocked, cancelled, failed, inconclusive

### Community 105 - "provenance"
Cohesion: 0.29
Nodes (7): evidence_set_id, source_run_id, provenance, additionalProperties, required, type, source_episode_id

### Community 106 - "enum"
Cohesion: 0.29
Nodes (7): default, enum, type, memory_policy, frozen, normal, off

### Community 107 - "enum"
Cohesion: 0.29
Nodes (7): enum, type, mode, exploratory, regression, story, workflow

### Community 108 - "enum"
Cohesion: 0.29
Nodes (7): enum, type, priority, p0, p1, p2, p3

### Community 109 - "select"
Cohesion: 0.15
Nodes (16): Filter, rank and bound. The last gate before memory reaches a prompt.      Sco, select(), candidate(), contract_path(), Any, Draft202012Validator, Path, What memory is allowed to tell a planner, and in what order.  Order is behavio (+8 more)

### Community 110 - "test_schedules_api.py"
Cohesion: 0.10
Nodes (15): InMemoryScheduleGateway, In-memory schedule gateway.  Mirrors the two behaviours the endpoints depend on:, client(), client_for(), gateway(), AsyncClient, The scheduling endpoints over real HTTP.  What matters here is not that a POST, A 201 for a schedule nobody stored is the worst possible answer here. (+7 more)

### Community 112 - "errors.ts"
Cohesion: 0.10
Nodes (23): LintFinding, looksLikeSelector(), PlanDocument, PlanStep, ScaffoldOptions, readExisting(), setup(), SetupInput (+15 more)

### Community 113 - "agent-action.schema.json"
Cohesion: 0.33
Nodes (5): additionalProperties, $id, $schema, title, type

### Community 114 - "enum"
Cohesion: 0.33
Nodes (6): enum, idempotency_key, non_retryable_requires_human, none_read_only, verify_before_retry, idempotency_strategy

### Community 115 - "required"
Cohesion: 0.33
Nodes (6): intent, side_effect, type, required, action_id, idempotency_strategy

### Community 116 - "enum"
Cohesion: 0.33
Nodes (6): enum, idempotency_key, non_retryable_requires_human, none_read_only, verify_before_retry, idempotency_strategy

### Community 117 - "error"
Cohesion: 0.33
Nodes (6): additionalProperties, required, type, error, code, message

### Community 118 - "failure-bundle.schema.json"
Cohesion: 0.33
Nodes (5): additionalProperties, $id, $schema, title, type

### Community 119 - "seed_project_with_default_policy"
Cohesion: 0.17
Nodes (21): datetime, Record what a run discovered about the knowledge it used.  The write and the r, Record one outcome and re-derive the candidate, inside an already-open     tran, record_memory_feedback(), RecordMemoryFeedbackCommand, RecordMemoryFeedbackResult, register_feedback(), enqueue_for_sync() (+13 more)

### Community 120 - "type"
Cohesion: 0.40
Nodes (5): description, type, null, object, actual_outcome

### Community 121 - "side_effect"
Cohesion: 0.40
Nodes (5): if, properties, side_effect, const, type

### Community 122 - "required"
Cohesion: 0.40
Nodes (5): then, required, expected_postconditions, preconditions, verification_strategy

### Community 123 - "items"
Cohesion: 0.40
Nodes (5): items, type, additionalProperties, type, artifacts

### Community 124 - "enum"
Cohesion: 0.33
Nodes (6): enum, compatibility, compatible, exact, incompatible, revalidate

### Community 125 - "TemporalScheduleGateway"
Cohesion: 0.10
Nodes (23): Namespaced so a schedule and a run can never collide in Temporal's id space., schedule_id_for(), Client, Temporal adapter for the ScheduleGateway port.  Temporal is the only store for, Listed from Temporal and filtered here.          Temporal's list is eventually, Rebuild the domain shape from what Temporal stored.          The action's argu, Decode the stored argument back into its dataclass.          `describe()` hand, _spec_cron() (+15 more)

### Community 126 - "verification_strategy"
Cohesion: 0.50
Nodes (4): verification_strategy, description, minLength, type

### Community 127 - "expected_postconditions"
Cohesion: 0.50
Nodes (4): items, type, type, expected_postconditions

### Community 128 - "message"
Cohesion: 0.50
Nodes (4): maxLength, minLength, type, message

### Community 129 - "type"
Cohesion: 0.50
Nodes (4): minimum, type, failed_step_index, integer

### Community 130 - "freshness"
Cohesion: 0.50
Nodes (4): maximum, minimum, type, freshness

### Community 131 - "reliability"
Cohesion: 0.50
Nodes (4): reliability, maximum, minimum, type

### Community 132 - "to_document"
Cohesion: 0.11
Nodes (17): Serialize to the public contract. Absent optionals are omitted, not nulled:, to_document(), compiled(), contract_path(), Draft202012Validator, Path, Plan, Compiling a story into a plan, and the plan surviving a round trip.  Two prope (+9 more)

### Community 133 - "summary"
Cohesion: 0.50
Nodes (4): summary, maxLength, minLength, type

### Community 134 - "description"
Cohesion: 0.50
Nodes (4): maxLength, minLength, type, description

### Community 135 - "environment_id"
Cohesion: 0.50
Nodes (4): maxLength, minLength, type, environment_id

### Community 136 - "name"
Cohesion: 0.50
Nodes (4): maxLength, minLength, type, name

### Community 137 - "run_policy_id"
Cohesion: 0.50
Nodes (4): run_policy_id, maxLength, minLength, type

### Community 138 - "source_story_id"
Cohesion: 0.50
Nodes (4): source_story_id, maxLength, minLength, type

### Community 144 - "TestPlan"
Cohesion: 0.09
Nodes (20): Store a new plan version. Raises AlreadyExistsError if that version exists., Most recently created version. Used to *choose* a version at run creation,, Plan versions compiled from a story, newest first., What the agent is asked to achieve, in one instruction.          Only the action, TestPlan, _budget_to_column(), _metadata_value(), _plan_step_to_column() (+12 more)

### Community 145 - "action_id"
Cohesion: 0.67
Nodes (3): minLength, type, action_id

### Community 146 - "test_client.py"
Cohesion: 0.12
Nodes (25): CircuitBreaker, Circuit breaker for a model endpoint.  When a GPU box is down, thirty-second tim, True when a call may be attempted, half-opening after the cooldown., ask(), build_client(), completion(), Any, Endpoint behaviour: what gets retried, what does not, and what is never coerced. (+17 more)

### Community 147 - "Adaptive QA Learning Graph"
Cohesion: 0.06
Nodes (31): 1. Hard filters, 2. Candidate search, 3. Ranking, 4. Bounded context, 5. Revalidation, Adaptive QA Learning Graph, ExperienceConsolidator, Goal (+23 more)

### Community 151 - "HANDOFF.md"
Cohesion: 0.06
Nodes (31): Acceptance Gates (Phase 07), Acceptance Gates (Phase 08), Acceptance Gates (Phase 09), Acceptance Gates (Phase 10), Acceptance Gates (Phase 11), Acceptance Gates (Phase 12), Acceptance Gates (Phase 13), Architecture Decisions Made (+23 more)

### Community 153 - "from_document"
Cohesion: 0.14
Nodes (24): _enum(), from_document(), _optional_timestamp(), Any, datetime, EnumT, The portable knowledge document (`contracts/knowledge-experience.schema.json`)., Serialize to the public contract.      Optionals inside `provenance` and `vali (+16 more)

### Community 156 - "redact_payload"
Cohesion: 0.11
Nodes (19): _clean_text(), Any, Exception, Redaction before anything is learned.  Memory outlives the run that produced i, Content that must not be learned at all, rather than learned redacted., Clean a payload, or refuse it.      Raises `UnsafeKnowledgeError` when the con, _redact_entry(), redact_payload() (+11 more)

### Community 157 - "routers/memory.py"
Cohesion: 0.13
Nodes (23): GraphMemoryPort, The learned-memory graph projection.  Everything here is about a store that is a, Remove one candidate from the projection.          Used when knowledge is invali, Drop one project's projection, for a rebuild., Whether the store answers. Never raises: this is what `memory status`         re, memory_status(), MemoryStatus, What `memory status` answers.  Written so that it still answers when the graph i (+15 more)

### Community 187 - "commands/run.ts"
Cohesion: 0.11
Nodes (23): cancelRun(), createRun(), CreateRunInput, getProject(), getRun(), listProjects(), parseProject(), parseRunState() (+15 more)

### Community 188 - "derive_verdict"
Cohesion: 0.14
Nodes (14): derive_verdict(), Verdict, Turn criterion results into the run's QA verdict.      Ordering matters and is, met(), not_met(), FailureKind, Verdict derivation: what a run is allowed to conclude, and from what.  The rule, Ordering matters: the finding worth having wins over the noise around it. (+6 more)

### Community 190 - "routers/schedules.py"
Cohesion: 0.16
Nodes (19): Protocol, Register a recurring run. Raises `AlreadyExistsError` on a taken id.          Th, Pause or resume. False when there is no such schedule.          Pausing rather t, ScheduleGateway, create_schedule(), delete_schedule(), list_schedules(), _owned() (+11 more)

### Community 191 - "PageState"
Cohesion: 0.08
Nodes (10): Where the page is and what it offers, as roles and accessible names., _normalize_segment(), PageState, A page reduced to where it is and what it offers.      A state map is kept for, Path with identifier-shaped segments replaced.          `/orders/8821` and `/o, Sorted, deduplicated and bounded — so a signature does not depend on the, The page as a planner can read it: where it is and what it offers.          A, Stable id for a state. Same route and same offers means same id, anywhere. (+2 more)

### Community 193 - "exploration_outcome"
Cohesion: 0.24
Nodes (12): exploration_outcome(), Load one run's map and diff it against the previous exploration.      Raises `No, page(), Factory, Storing a map and comparing it against the last one.  Parametrized over the in, Three explorations: the second compares against the first, the third against the, report(), seed_run() (+4 more)

### Community 194 - "Frontier"
Cohesion: 0.11
Nodes (8): Frontier, FrontierEntry, One thing left to try, and where from., Visited states and what is left to try, with depth.      Deliberately a plain, Rebuild a frontier mid-exploration. `None` starts a fresh one.          `offer, Register a state. True when it had never been seen before.          Its afford, Hand out the next thing to try, permanently removing it from the frontier., TestResumingAnExploration

### Community 195 - "compatibility_of"
Cohesion: 0.23
Nodes (12): compatibility_of(), datetime, Judge one candidate against one run's situation.      Deliberately independent, candidate(), Whether old knowledge applies to the run happening now.  The three-way answer, scope(), test_knowledge_recorded_with_less_context_is_compatible_but_not_exact(), test_knowledge_that_was_never_context_bound_stays_compatible() (+4 more)

### Community 201 - "contradicted_by"
Cohesion: 0.18
Nodes (13): contradicted_by(), _is_contradicted(), Comparing what memory claims against what a run deterministically observed.  Thi, Stored knowledge this run's verified results disprove.      A model-derived resu, candidate(), CandidateStatus, CriterionOutcome, What a verified run is allowed to say about stored memory.  The rule these enfor (+5 more)

### Community 204 - "test_memory_api.py"
Cohesion: 0.16
Nodes (10): app_client(), broken_graph(), no_graph(), AsyncClient, The memory administration endpoints over real HTTP.  What matters here is the, TestRebuild, TestStatus, TestSync (+2 more)

### Community 205 - "Affordance"
Cohesion: 0.14
Nodes (12): _clickable(), Default when no policy is supplied: anything a click could take.      Used by, Affordance, normalize_name(), One thing a page offers to do, named the way a human would name it.      Role, Whether an explorer can take this with no information beyond the page., What identifies this affordance across renders, with the volatile parts gone., explore() (+4 more)

### Community 210 - "apply_feedback"
Cohesion: 0.23
Nodes (11): apply_feedback(), datetime, Fold one verified outcome into a candidate and re-derive its status.      Pure, candidate(), feedback(), What later runs do to knowledge they used.  Consolidation is only half a learn, test_feedback_for_another_candidate_is_refused(), test_feedback_must_name_the_run_that_produced_it() (+3 more)

### Community 213 - "test_temporal_workflow.py"
Cohesion: 0.26
Nodes (19): postgres_unit_of_work_factory(), Client, RunStatus, UnitOfWorkFactory, Worker, queue_run(), Durable run lifecycle against a real Temporal server and a real database.  The, The core durability gate: a worker is replaceable mid-run.      The run is pau (+11 more)

### Community 214 - "test_exploring_graph.py"
Cohesion: 0.19
Nodes (16): browser_clicks_within_depth(), explore(), page(), _path_of(), The agent graph in exploration mode.  The claim being tested is not "it clicks, Sanity check on the fixture rather than on the code under test., `https://app.test/alpha` -> `alpha`, and the root -> the empty string., A page whose links carry their destination, as a real snapshot does. (+8 more)

### Community 215 - "schemas.ts"
Cohesion: 0.12
Nodes (18): artifactSchema, compiledPlanSchema, ContractError, failureContextSchema, findingSchema, memoryStatusSchema, parse(), projectSchema (+10 more)

### Community 217 - "contracts/test_plan.py"
Cohesion: 0.22
Nodes (20): _budget_from(), _enum(), from_document(), _metadata_from(), _optional_int(), _optional_str(), Any, EnumT (+12 more)

### Community 218 - "PlanBudget"
Cohesion: 0.12
Nodes (14): _budget_document(), compile_story(), _describe(), PlanBudget, UserStory, Compile a story into a plan, deterministically.      No model is involved. The s, Carry the story's forbidden outcomes into the plan's own description.      They, Per-plan limits. Narrows the RunPolicy, never widens it. (+6 more)

### Community 221 - "LockHandle"
Cohesion: 0.17
Nodes (10): LockHandle, _millis(), Redis, Redis lock manager with TTL and ownership tokens.  Release and renew compare the, RedisLockManager, _Entry, InMemoryLockManager, In-memory lock manager with real TTL semantics.  Expiry is evaluated on access u (+2 more)

### Community 223 - "page"
Cohesion: 0.18
Nodes (7): ChangedState, compare(), The same route, offering something different., Diff two maps by structure, never by content., page(), TestComparingAgainstABaseline, TestTheSameStateIsRecognisedAgain

### Community 224 - "compilerOptions"
Cohesion: 0.10
Nodes (20): compilerOptions, declaration, exactOptionalPropertyTypes, lib, module, moduleResolution, noImplicitOverride, noUncheckedIndexedAccess (+12 more)

### Community 225 - "test_operational_queries.py"
Cohesion: 0.17
Nodes (18): OperationalQuery, query_named(), Operational questions, answered from durable rows.  Why SQL and not a metrics, postgres_unit_of_work_scope(), Units of work that really commit, with a truncating teardown., factory(), Every operational query, executed against the real schema.  The reason these l, An aggregate over no rows must still return a row.      "No clusters" and "the (+10 more)

### Community 226 - "api.ts"
Cohesion: 0.17
Nodes (14): ApiClient, ApiClientOptions, ApiResponse, backoffMs(), extractDetail(), isRetryableStatus(), readBody(), RequestOptions (+6 more)

### Community 227 - "agent.ts"
Cohesion: 0.16
Nodes (17): installClaudeSkill(), InstallInput, InstallResult, readIfPresent(), requireSupportedAgent(), SKILL_PATH, skillDocument(), SUPPORTED_AGENTS (+9 more)

### Community 228 - "diff.ts"
Cohesion: 0.16
Nodes (16): classify(), CriterionChange, CriterionDelta, CriterionSide, delta(), describePlan(), diffRuns(), loadRunSummary() (+8 more)

### Community 229 - "parse_affordances"
Cohesion: 0.17
Nodes (6): _absolute(), parse_affordances(), Resolve an href against the page, or decline.      `None` for anything that is, Pull role/name pairs out of an ARIA snapshot, deduplicated and bounded.      A, TestParsing, TestResolvingLinkDestinations

### Community 230 - "InferenceMetrics"
Cohesion: 0.13
Nodes (9): AirLLMDeepAnalyst, AsyncClient, One client for the endpoint, so its circuit breaker remembers across calls., Implements `DeepAnalyst` (application port) over the DEEP-capability endpoint., EndpointStats, InferenceMetrics, Counted apart from failures: the endpoint answered, the answer was unusable., AsyncClient (+1 more)

### Community 231 - "test_deep_analyst.py"
Cohesion: 0.19
Nodes (18): build_analyst(), completion(), deep_endpoint(), Request, Response, The deep-analysis adapter, against a server that can be made to misbehave.  Wh, A cause nobody can re-derive is not comparable to the next one (docs/08)., A 10-minute call under a 2-minute lease frees the slot while it is still running (+10 more)

### Community 232 - "commands/memory.ts"
Cohesion: 0.25
Nodes (15): memoryRebuild, memoryStatus, memorySync(), memoryValidate(), MemoryValidation, num(), parseRebuild(), parseStatus() (+7 more)

### Community 233 - "Patterns adopted"
Cohesion: 0.11
Nodes (18): 10. Agent installation, 1. Agent-first CLI, 2. Machine-pure output, 3. Versioned TestPlan files, 4. Atomic FailureBundle, 5. Idempotency and retry ownership, 6. Wait does not mean cancel, 7. Runtime response validation (+10 more)

### Community 234 - "client.ts"
Cohesion: 0.13
Nodes (9): ApiClient, ApiClientOptions, ApiError, HttpMemoryGateway, HttpProjectGateway, toApiError(), toMemoryStatus(), toProject() (+1 more)

### Community 235 - "MemoryMetrics"
Cohesion: 0.15
Nodes (9): MemoryMetrics, What memory is doing, and whether it is worth its cost.  Same shape as the infer, What the counters have to be able to tell an operator.  A run's verdict looks, Summaries and payloads never reach the log line.      They derive from page co, test_a_projection_that_never_catches_up_is_countable(), test_hypotheses_are_counted_separately_from_facts(), test_nothing_derived_from_page_content_is_recorded(), test_what_was_learned_and_what_was_withdrawn_are_both_visible() (+1 more)

### Community 236 - "test_deep_analysis_activity.py"
Cohesion: 0.18
Nodes (14): _heartbeating(), Group this project's recent failures and, if a deep model is configured, ask, Keep an activity visibly alive across a call that takes minutes.      Temporal, AnalyzeFailuresParams, activities(), CountingAnalyst, The deep-analysis activity at the Temporal boundary.  Three things a workflow, The verdict is already durable. A second reading of results that are already (+6 more)

### Community 237 - "test_memory_benchmark.py"
Cohesion: 0.23
Nodes (12): benchmark(), execute_run(), datetime, Factory, Cold versus warm: does memory actually save anything?  The gate this answers (, Persist the run the way a real one would be, then consolidate it., The cold baseline and the warm run, on the same flow., One run of the flow, warm or cold, through the real retrieval path. (+4 more)

### Community 238 - "API and Event Contracts"
Cohesion: 0.11
Nodes (17): API and Event Contracts, Artifacts, CLI envelope, Event envelope, Exploration (Phase 12), Failure triage (Phase 11), Important event types, Memory admin (Phase 09) (+9 more)

### Community 239 - "ports/gateways.ts"
Cohesion: 0.11
Nodes (8): CompiledPlan, DraftStory, MemoryGateway, ProjectGateway, RunEventStream, RunSubscription, StartRunInput, StoryGateway

### Community 240 - "test_database_failure.py"
Cohesion: 0.21
Nodes (14): factory(), FlakyDatabase, Factory, queued_run(), A transient PostgreSQL failure, against a real PostgreSQL.  The gap the recove, They share a transaction on purpose.      A run that moved without leaving its, Sanity on the fixture: a double that never failed would make every assertion, A unit-of-work factory that refuses to connect for the first `failures` calls. (+6 more)

### Community 241 - "bundle.test.ts"
Cohesion: 0.21
Nodes (13): ArtifactFetcher, assertBytesMatch(), assertCoherent(), BundleArtifact, BundleManifest, describe(), materialize(), MaterializeResult (+5 more)

### Community 242 - "flaky.ts"
Cohesion: 0.17
Nodes (14): CriterionStability, FlakyInput, FlakyReport, measureFlakiness(), record(), renderFlaky(), unstableCriteria(), validateCount() (+6 more)

### Community 243 - "Runtime responsibilities"
Cohesion: 0.12
Nodes (16): Architecture, Context diagram, Deployment v1, FastAPI, Filesystem, Graphiti/FalkorDB, LangGraph, Model Router (+8 more)

### Community 244 - "dependencies"
Cohesion: 0.12
Nodes (17): dependencies, @hookform/resolvers, react, react-dom, react-hook-form, react-router, @tanstack/react-query, zod (+9 more)

### Community 245 - "MemoryContextRequest"
Cohesion: 0.38
Nodes (8): MemoryContextRequest, datetime, retrieve_memory_context(), learn(), datetime, Factory, scope(), sighting()

### Community 246 - "envelope.test.ts"
Cohesion: 0.17
Nodes (10): Recorded, envelopeSchema, packageRoot, VALID_PLAN, validateEnvelope, CLI_ENTRY, CliResult, packageRoot (+2 more)

### Community 247 - "routers/exploration.py"
Cohesion: 0.19
Nodes (11): ExplorationOutcome, What one exploration found, and what changed since the last one.  The comparison, MapDelta, Comparing today's map of an application against a baseline.  The failure this ex, ContainerDep, What an exploring run mapped, and what changed since the last one.  Read-only, a, 404 when the run did not explore: a planned run has no map, and answering with, read_exploration() (+3 more)

### Community 248 - "policy"
Cohesion: 0.19
Nodes (6): policy(), Origin allowlist semantics.  Ambiguous matching is how allowlists get bypassed,, No implicit subdomains: evil.app.example.com is a different origin., There is no safe empty allowlist, so there is no default., TestAllowsOrigin, TestPolicyInvariants

### Community 249 - "Combination rules"
Cohesion: 0.13
Nodes (14): Adaptive memory graph, Always-on disciplines, Brainstorming is conditional, Claude Code Skill Routing, CLI/API contracts, Combination rules, Frontend design split, Graphify and the runtime graph (+6 more)

### Community 250 - "test_deep_analysis_real_model.py"
Cohesion: 0.21
Nodes (12): _flag(), _positive_float(), _positive_int(), A misconfigured limit fails at startup, not as strange behaviour under load., analyst(), configured_router(), AsyncClient, Optional system test against a real deep endpoint.  Skipped unless `DEEP_BASE_UR (+4 more)

### Community 251 - "Settings"
Cohesion: 0.20
Nodes (9): Settings, AsyncClient, Local embeddings from a vLLM pooling endpoint.  A separate endpoint from the gen, VLLMEmbeddingGateway, build_embedding_gateway(), build_graph_projection(), AsyncClient, Building the projection from configuration.  Kept apart from the projection it (+1 more)

### Community 252 - "ExplorationProgress"
Cohesion: 0.18
Nodes (6): ExplorationProgress, Clamp to the policy. A policy with no depth limit still gets one here:, Everything the stop decision is allowed to look at., Why exploration should stop now, or None to continue.      Ordered by what a r, stop_reason(), TestTheBudgetCannotExceedThePolicy

### Community 253 - "test_memory_in_the_prompt.py"
Cohesion: 0.30
Nodes (7): candidate(), How recalled memory reaches a model, and what the wording has to protect.  Memor, request(), test_an_expired_item_never_reaches_the_prompt(), test_memory_appears_before_the_page_so_the_page_is_read_last(), TestMemoryCannotSmuggleStructureIntoThePrompt, TestTheLabelsSurviveIntoTheWords

### Community 254 - "TestOneDeterministicDisagreementWithdrawsIt"
Cohesion: 0.35
Nodes (8): consolidate(), finished_run(), datetime, Factory, Memory that a later run can disprove.  The lifecycle end to end, against both, A completed run that checked one criterion deterministically., scope(), TestOneDeterministicDisagreementWithdrawsIt

### Community 255 - "Bounded contexts"
Cohesion: 0.14
Nodes (13): Action safety fields, Agent, Bounded contexts, Browser, Core statuses, Domain Model, Important invariants, Inference (+5 more)

### Community 256 - "runs/run.ts"
Cohesion: 0.18
Nodes (11): canCancel(), CANCELLABLE, isActive(), isTerminal(), Run, RUN_STATUSES, RunStatus, TERMINAL (+3 more)

### Community 257 - "test_evidence_chain.py"
Cohesion: 0.29
Nodes (12): execute(), Any, Path, Evidence, from the live page to the failure bundle.  Phase 07 could say *which, The chain Phase 07 could not complete: capture, index, and reach it again., `evidence_refs` existed and nobody filled it; a failure named nothing showable., It used to be written empty, so recovery would rebuild a browser and go nowhere., run_episode() (+4 more)

### Community 258 - "test_triage_from_a_real_run.py"
Cohesion: 0.31
Nodes (12): execute(), Any, Path, Triage over a real failing run, end to end.  Everything else in this package pro, Stands in for a deep endpoint that is down — the state this system spends most, A member is a pointer, not a copy — so the observation and the evidence refs a, RefusingAnalyst, run_and_triage() (+4 more)

### Community 259 - "Agent-First CLI Design"
Cohesion: 0.15
Nodes (12): Agent-First CLI Design, Agent verification skill, Boundary, Configuration, Failure bundle disk layout, Output contract, Purpose, Request behavior (+4 more)

### Community 260 - "Operations Runbook"
Cohesion: 0.15
Nodes (12): Backup, Consultas operacionales, Drill ejecutado (2026-08-20), Instalar el skill de verificación en un repo ajeno, Instalar la CLI como cliente externo, Levantar el stack en una máquina nueva, Memoria adaptativa, Operations Runbook (+4 more)

### Community 261 - "RunGateway"
Cohesion: 0.15
Nodes (4): RunGateway, prepareRun(), StartRunAttempt, StartRunRequest

### Community 262 - "safe_url"
Cohesion: 0.24
Nodes (9): Turning a URL into something safe to keep.  Applications put credentials in URLs, Scheme, host and path. No query, no fragment, no userinfo.      Query strings an, safe_url(), Which parts of a URL are safe to keep.  The rule this function encodes: a URL to, test_a_reset_link_keeps_nothing_of_its_token(), test_credentials_in_the_authority_are_dropped(), test_it_keeps_where_and_drops_what_rides_along(), test_something_that_is_not_a_url_is_left_alone_when_it_is_harmless() (+1 more)

### Community 263 - "test_exploring_a_real_run.py"
Cohesion: 0.35
Nodes (11): execute(), explore_twice(), Any, Path, queue_run(), An exploring run, end to end: Temporal activity, real Chromium, real PostgreSQL., The same application, unchanged between runs, must produce no findings.      T, test_an_exploring_run_leaves_a_durable_map() (+3 more)

### Community 264 - "test_learning_from_a_real_run.py"
Cohesion: 0.36
Nodes (11): execute(), Any, Path, What a real run actually learns.  Everything else about consolidation is tested, Page text is untrusted data. Whatever is stored must be safe to replay., run_and_learn(), test_a_finished_run_leaves_durable_knowledge(), test_a_first_run_teaches_nothing_the_agent_may_act_on() (+3 more)

### Community 265 - "envelope.ts"
Cohesion: 0.21
Nodes (10): renderError(), run(), emit(), Envelope, EnvelopeError, errorEnvelope(), OutputMode, processWriter (+2 more)

### Community 266 - "include"
Cohesion: 0.17
Nodes (11): compilerOptions, composite, noEmit, rootDir, extends, include, src, test (+3 more)

### Community 267 - "properties"
Cohesion: 0.17
Nodes (12): minLength, type, minLength, type, properties, environment_id, project_id, query_id (+4 more)

### Community 268 - "required"
Cohesion: 0.17
Nodes (12): required, kind, model_derived, observed, provenance, validity, compatibility, freshness (+4 more)

### Community 269 - "Product Spec"
Cohesion: 0.17
Nodes (11): Actores, Casos de uso v1, CLIEnvelope, Contratos públicos v1, FailureBundle, No objetivos iniciales, Principios, Problema (+3 more)

### Community 270 - "frontend/tsconfig.test.json"
Cohesion: 0.17
Nodes (11): compilerOptions, tsBuildInfoFile, types, extends, include, node, src, test (+3 more)

### Community 271 - "Phase 08 — Agent-First CLI and Verification Contracts"
Cohesion: 0.17
Nodes (11): Architectural decision, Contracts, FailureBundle invariants, Gates, Objective, Phase 08 — Agent-First CLI and Verification Contracts, Plan-authoring rules, Required commands v1 (+3 more)

### Community 272 - "Durability and Recovery"
Cohesion: 0.18
Nodes (10): Browser recovery, Checkpoint deserialization allowlist, Checkpoint model reconciliation, Context compaction, Durability and Recovery, Knowledge graph outage/rebuild, Retry ownership, Safe checkpoint (+2 more)

### Community 273 - "Inference Layer"
Cohesion: 0.18
Nodes (10): Deep endpoint (Phase 11), Deterministic-before-semantic triage, Evidence boundary, Graphiti inference boundary, Inference Layer, Límites y fallos, Model policy, Port (+2 more)

### Community 274 - "Knowledge Graph"
Cohesion: 0.18
Nodes (10): Core nodes, Core relationships, Decision, Feedback and refinement, Knowledge Graph, Local-first integration, Recovery, Retrieval policy (+2 more)

### Community 275 - "Claude Code Operating Procedure"
Cohesion: 0.18
Nodes (10): Architecture and implementation skills, Claude Code Operating Procedure, Context control, End of phase, Frontend design skills, Process skills, Review and release skills, Session start (+2 more)

### Community 276 - "run-page.test.tsx"
Cohesion: 0.29
Nodes (6): makeEvent(), makeRun(), NotFound, gatewaysWith(), renderRun(), withReport()

### Community 277 - "TestUserStory"
Cohesion: 0.29
Nodes (4): AcceptanceCriterion, criterion(), Entity invariants for Project and UserStory., TestUserStory

### Community 278 - "TestWhatItDeclinedToTake"
Cohesion: 0.42
Nodes (4): is_takeable(), Whether this run may take this affordance at all.      Asked *before* the afford, Counted, not attempted, and reported either way.      "Mapped 12 states, left, TestWhatItDeclinedToTake

### Community 279 - "Claude Code Project Instructions"
Cohesion: 0.20
Nodes (9): Architecture invariants, Claude Code Project Instructions, Default technology choices, Documentation discipline, Forbidden shortcuts, Mandatory skill routing, Mandatory workflow, Mission (+1 more)

### Community 280 - "Data and Artifacts"
Cohesion: 0.20
Nodes (9): Artifact tree, Bounded reads, Data and Artifacts, Data retention, FailureBundle, File-input safety, Important identities, Knowledge projection (+1 more)

### Community 281 - "Testing Strategy"
Cohesion: 0.20
Nodes (9): Adaptive memory tests, Agent-plan quality scenarios, Browser fixture application, CLI/API contract scenarios, Definition of a regression, FailureBundle integrity scenarios, Layers, Mandatory recovery scenarios (+1 more)

### Community 282 - "ADR 0008 — Adaptive QA Learning Graph with Graphiti + FalkorDB"
Cohesion: 0.20
Nodes (9): ADR 0008 — Adaptive QA Learning Graph with Graphiti + FalkorDB, Consequences, Context, Costs / risks, Decision, Implementation notes (Phase 09), Positive, Rejected alternatives (+1 more)

### Community 285 - "Agentic Web QA — Claude Code Build Kit"
Cohesion: 0.20
Nodes (9): Adaptive learning graph (Phase 09), Agentic Web QA — Claude Code Build Kit, Claude Code codebase intelligence, Cómo usar este kit con Claude Code, Evaluación de TestSprite CLI, Orden de lectura para humanos, Principio de trabajo, Resultado esperado (+1 more)

### Community 286 - "Session Handoff"
Cohesion: 0.20
Nodes (9): Current phase, Decisions made, Files changed, Known issues / risks, Last stable state, Next exact action, Plan activo, Session Handoff (+1 more)

### Community 287 - "Interface System"
Cohesion: 0.20
Nodes (9): Accessibility, Components, Decisions log, Foundations, Interface System, Layout, Operational states, Product character (+1 more)

### Community 288 - "Security Model"
Cohesion: 0.22
Nodes (8): Adaptive memory poisoning controls, Credential handling (normativo), Development secrets, Origin allowlist semantics (normativo), Platform identity model (v1), Required controls, Security Model, Threats specific to browser agents

### Community 289 - "Observability"
Cohesion: 0.22
Nodes (8): Adaptive memory telemetry, Baseline operacional (Phase 13), Correlation identifiers, Logs, Metrics v1, Observability, OpenTelemetry, UI operational health

### Community 290 - "Development-Time Codebase Graph (Graphify)"
Cohesion: 0.22
Nodes (8): Bootstrap, Development-Time Codebase Graph (Graphify), Failure behavior, Purpose, Query-before-scan rule, Refresh policy, Repository outputs, Two-graph model

### Community 291 - "Memory Evaluation — reach the records page"
Cohesion: 0.22
Nodes (8): A. Mechanism — cold baseline vs warm run, B. Real model — cold baseline vs warm run, Decision, Delta, Memory Evaluation — reach the records page, Notes / provenance, Quality, Scope

### Community 292 - "Release Checklist"
Cohesion: 0.22
Nodes (8): Antes de etiquetar, Drills, con evidencia, El demo de release (2026-08-20), Gates automáticos, Lo que este release no promete, Los cinco defectos que encontraron el soak y el demo, Release Checklist, Soak de release (2026-08-20)

### Community 293 - "run-events.ts"
Cohesion: 0.36
Nodes (5): toRunEvent(), originAsWebSocket(), parseEvent(), RunEventStreamOptions, WebSocketRunEventStream

### Community 294 - "Memory Evaluation — <flow>"
Cohesion: 0.22
Nodes (8): Cold baseline, Decision, Delta, Memory Evaluation — <flow>, Notes / provenance, Quality, Scope, Warm run

### Community 295 - "normalize_origin"
Cohesion: 0.29
Nodes (5): normalize_origin(), _origin_of(), Return `scheme://host[:port]`, rejecting anything carrying more than that., Exact origin match against the allowlist., TestNormalizeOrigin

### Community 296 - "API design principles"
Cohesion: 0.25
Nodes (7): API design principles, CLI contracts, Collections and payload bounds, Commands and long-running runs, Errors, Evolution, Resource model

### Community 297 - "Error handling patterns"
Cohesion: 0.25
Nodes (7): Classify first, Error handling patterns, Layering, Observability and UX, Retry discipline, Tests, Wait and cancellation

### Community 298 - "doctor.ts"
Cohesion: 0.36
Nodes (7): checkContracts(), describeHealth(), doctor(), DoctorReport, problemError(), Config, doctorCommand()

### Community 299 - "Agent Runtime"
Cohesion: 0.25
Nodes (7): Agent Runtime, Episodes, Exploration mode (Phase 12), LangGraph state machine, Logical roles, Outcomes de un step, Verification priority

### Community 300 - "Docker Compose Topology"
Cohesion: 0.25
Nodes (7): CLI, Docker Compose Topology, Frontend (Phase 10), Healthchecks, Profiles, Services target, Storage

### Community 301 - "ADR 0009 — Run workflow shape, retry ownership and checkpoint reconciliation"
Cohesion: 0.25
Nodes (7): ADR 0009 — Run workflow shape, retry ownership and checkpoint reconciliation, Checkpoint reconciliation, Consequences, Context, Decision, Retry ownership (single owner per loop), Workflow shape

### Community 302 - "memory-page.test.tsx"
Cohesion: 0.36
Nodes (4): App(), defaultQueryClient(), root, makeMemoryStatus()

### Community 303 - "findings.ts"
Cohesion: 0.25
Nodes (5): Artifact, CriterionOutcome, FailureKind, Finding, RunReport

### Community 304 - "v1.0.0-rc — 2026-08-20"
Cohesion: 0.29
Nodes (6): Changelog, Contratos públicos, Límites conocidos de este candidato, Para empezar, Qué hace, v1.0.0-rc — 2026-08-20

### Community 305 - "Graphify — codebase graph workflow"
Cohesion: 0.29
Nodes (6): Bootstrap, Confidence discipline, Graphify — codebase graph workflow, Query-first orientation, Refresh discipline, Scope boundary

### Community 306 - "PostgreSQL"
Cohesion: 0.29
Nodes (6): Migrations, Operations, PostgreSQL, Queries and indexes, Schema design, Transactions and concurrency

### Community 307 - "Prompt engineering patterns"
Cohesion: 0.29
Nodes (6): Evaluation, Prompt engineering patterns, Prompt injection defense, Prompt structure, Reliability patterns, Start from a contract

### Community 308 - "cli/test/boundaries.test.ts"
Cohesion: 0.29
Nodes (3): FORBIDDEN, packageRoot, sourceRoot

### Community 309 - "contract-examples.test.ts"
Cohesion: 0.33
Nodes (6): contracts, examples, load(), packageRoot, PAIRS, validator()

### Community 310 - "Browser Runtime"
Cohesion: 0.29
Nodes (6): Artifacts, Browser Runtime, Interaction ladder, Page fingerprint, Security, Typed action set v1

### Community 311 - "Redis Contract"
Cohesion: 0.29
Nodes (6): Allowed responsibilities, Forbidden responsibility, Recovery assumption, Redis Contract, Stream retention, Suggested key namespaces

### Community 312 - "scripts"
Cohesion: 0.29
Nodes (7): scripts, build, dev, lint, preview, test, typecheck

### Community 313 - "watch-run.ts"
Cohesion: 0.33
Nodes (4): RunSnapshot, RunWatch, WatchHandlers, watchRun()

### Community 314 - "HttpStoryGateway"
Cohesion: 0.38
Nodes (3): HttpStoryGateway, toStories(), toStory()

### Community 315 - "use-projects-viewmodel.ts"
Cohesion: 0.43
Nodes (6): isNotFound(), messageFor(), ProjectsViewModel, ProjectViewModel, useProjectsViewModel(), useProjectViewModel()

### Community 316 - "use-run-viewmodel.ts"
Cohesion: 0.33
Nodes (6): CommandName, messageFor(), RunViewModel, TaggedError, TaggedSnapshot, useRunViewModel()

### Community 318 - "Phase 06 — vLLM + Model Router"
Cohesion: 0.29
Nodes (6): Future boundary, Gates, Objective, Phase 06 — vLLM + Model Router, Required skills, Tasks

### Community 319 - "Phase 09 — Adaptive QA Learning Graph (Graphiti + FalkorDB)"
Cohesion: 0.29
Nodes (6): Gates, Objective, Phase 09 — Adaptive QA Learning Graph (Graphiti + FalkorDB), Required reading, Required skills, Tasks

### Community 320 - "demo.sh"
Cohesion: 0.43
Nodes (4): plan_file(), run_and_wait(), say(), demo.sh script

### Community 321 - "Interface design"
Cohesion: 0.33
Nodes (5): Architecture constraint, Decide explicitly, Interface design, Persistent design memory, Product rules

### Community 322 - "Ponytail — minimal safe engineering"
Cohesion: 0.33
Nodes (5): Decision ladder, Output discipline, Ponytail — minimal safe engineering, Project-specific guardrails, Review behavior

### Community 323 - "Systematic debugging"
Cohesion: 0.33
Nodes (5): Phase 1 — Reproduce and collect evidence, Phase 2 — Trace the cause, Phase 3 — Test one hypothesis, Phase 4 — Fix and prevent regression, Systematic debugging

### Community 324 - "Backend Clean Architecture"
Cohesion: 0.33
Nodes (5): Backend Clean Architecture, Dependency rule, Mapping discipline, Ports worth defining early, Proposed package

### Community 325 - "Frontend — Clean Architecture + MVVM"
Cohesion: 0.33
Nodes (5): Direction, Example RunViewModel surface, Frontend — Clean Architecture + MVVM, Proposed tree, State ownership

### Community 326 - "ADR 0010 — Transaction ownership: commands own a UnitOfWork, queries take repositories"
Cohesion: 0.33
Nodes (5): ADR 0010 — Transaction ownership: commands own a UnitOfWork, queries take repositories, Consequences, Context, Decision, Orden obligatorio para side effects externos

### Community 327 - "Performance Profile"
Cohesion: 0.33
Nodes (5): El estado que carga un checkpoint, Lo que sigue sin medirse, Los pasos dentro de un episodio, Performance Profile, Qué ocupa en disco

### Community 328 - "Recovery Matrix"
Cohesion: 0.33
Nodes (5): Contratos y clientes, Hostilidad, Huecos conocidos, Infraestructura, Recovery Matrix

### Community 329 - "frontend/package.json"
Cohesion: 0.33
Nodes (5): name, packageManager, private, type, version

### Community 330 - "timeline.ts"
Cohesion: 0.33
Nodes (3): EMPTY_TIMELINE, RunEvent, Timeline

### Community 332 - "Phase 01 — Domain + PostgreSQL Foundation"
Cohesion: 0.33
Nodes (5): Gates, Objective, Phase 01 — Domain + PostgreSQL Foundation, Required skills, Tasks

### Community 333 - "Phase 02 — Run API + Temporal Lifecycle"
Cohesion: 0.33
Nodes (5): Gates, Objective, Phase 02 — Run API + Temporal Lifecycle, Required skills, Tasks

### Community 334 - "Phase 04 — Browser Gateway"
Cohesion: 0.33
Nodes (5): Gates, Objective, Phase 04 — Browser Gateway, Required skills, Tasks

### Community 335 - "Phase 07 — User Story QA Workflow"
Cohesion: 0.33
Nodes (5): Gates, Objective, Phase 07 — User Story QA Workflow, Required skills, Tasks

### Community 336 - "Phase 10 — React MVVM Control UI"
Cohesion: 0.33
Nodes (5): Gates, Objective, Phase 10 — React MVVM Control UI, Required skills, Tasks

### Community 337 - "Phase 11 — AirLLM Deep Analysis"
Cohesion: 0.33
Nodes (5): Gates, Objective, Phase 11 — AirLLM Deep Analysis, Required skills, Tasks

### Community 338 - "Phase 13 — Chaos, Security and Observability Hardening"
Cohesion: 0.33
Nodes (5): Gates, Objective, Phase 13 — Chaos, Security and Observability Hardening, Required skills, Tasks

### Community 339 - "Phase 14 — Release Candidate"
Cohesion: 0.33
Nodes (5): Gates, Objective, Phase 14 — Release Candidate, Required skills, Tasks

### Community 341 - "[Decision title]"
Cohesion: 0.33
Nodes (5): Alternatives considered, Consequences, Context, Decision, [Decision title]

### Community 342 - "content_version"
Cohesion: 0.50
Nodes (5): content_version(), Any, Hash the document without its identity fields.      Identity is excluded so th, Parse with stand-in identity so hashing sees a validated, normalized plan., _with_placeholder_identity()

### Community 343 - "Frontend design"
Cohesion: 0.40
Nodes (4): Frontend design, Project-specific emphasis, Quality bar, Workflow

### Community 344 - "Vercel React best practices"
Cohesion: 0.40
Nodes (4): Priority order, Rules, Vercel React best practices, Verification

### Community 345 - "roveqa CLI"
Cohesion: 0.40
Nodes (4): Commands, Configuration, Contract, roveqa CLI

### Community 346 - "ci-adapter.test.ts"
Cohesion: 0.40
Nodes (3): adapter, examples, packageRoot

### Community 347 - "items"
Cohesion: 0.50
Nodes (5): additionalProperties, items, maxItems, type, items

### Community 348 - "MCP Strategy"
Cohesion: 0.40
Nodes (4): Claude Code development environment, MCP Strategy, Rule, Runtime product

### Community 349 - "Clean Architecture + MVVM"
Cohesion: 0.40
Nodes (4): Clean Architecture + MVVM, Consequences, Context, Decision

### Community 350 - "Temporal + LangGraph persistence"
Cohesion: 0.40
Nodes (4): Consequences, Context, Decision, Temporal + LangGraph persistence

### Community 351 - "Redis is ephemeral coordination"
Cohesion: 0.40
Nodes (4): Consequences, Context, Decision, Redis is ephemeral coordination

### Community 352 - "Playwright direct first, MCP adapter optional"
Cohesion: 0.40
Nodes (4): Consequences, Context, Decision, Playwright direct first, MCP adapter optional

### Community 353 - "Filesystem artifacts first"
Cohesion: 0.40
Nodes (4): Consequences, Context, Decision, Filesystem artifacts first

### Community 354 - "Fast and deep inference split"
Cohesion: 0.40
Nodes (4): Consequences, Context, Decision, Fast and deep inference split

### Community 355 - "Agent-first CLI contracts, not TestSprite runtime dependency"
Cohesion: 0.40
Nodes (4): Agent-first CLI contracts, not TestSprite runtime dependency, Consequences, Context, Decision

### Community 357 - "story.ts"
Cohesion: 0.50
Nodes (4): AcceptanceCriterion, isFullyModelJudged(), unverifiable(), UserStory

### Community 358 - "stories-page.tsx"
Cohesion: 0.40
Nodes (3): EMPTY_CRITERION, FormValues, schema

### Community 359 - "Phase 00 — Repository Bootstrap"
Cohesion: 0.40
Nodes (4): Gates, Objective, Phase 00 — Repository Bootstrap, Tasks

### Community 360 - "Phase 03 — Redis Coordination + Realtime"
Cohesion: 0.40
Nodes (4): Gates, Objective, Phase 03 — Redis Coordination + Realtime, Tasks

### Community 361 - "Phase 05 — LangGraph Agent Core"
Cohesion: 0.40
Nodes (4): Gates, Objective, Phase 05 — LangGraph Agent Core, Tasks

### Community 362 - "Phase 12 — Autonomous Exploration + Scheduling"
Cohesion: 0.40
Nodes (4): Gates, Objective, Phase 12 — Autonomous Exploration + Scheduling, Tasks

### Community 363 - "reset_test_schema.py"
Cohesion: 0.67
Nodes (3): main(), Drop and recreate the test database's schema.  The suite's database is disposabl, reset()

### Community 364 - ".__aexit__"
Cohesion: 0.50
Nodes (3): BaseException, TracebackType, Roll back unless commit() already ran.

### Community 365 - "Brainstorming"
Cohesion: 0.50
Nodes (3): Brainstorming, Do not overuse, Workflow

### Community 366 - "Changelog generator"
Cohesion: 0.50
Nodes (3): Changelog generator, Rules, Workflow

### Community 367 - "bundle-contracts.mjs"
Cohesion: 0.50
Nodes (3): destination, packageRoot, source

### Community 368 - "Third-Party Agent Tooling"
Cohesion: 0.50
Nodes (3): Graphify, Ponytail, Third-Party Agent Tooling

### Community 369 - "Official References"
Cohesion: 0.50
Nodes (3): Adaptive memory graph references verified 2026-08-18, Official References, TestSprite CLI design reference

### Community 370 - "React + TypeScript + Vite"
Cohesion: 0.50
Nodes (3): Expanding the Oxlint configuration, React Compiler, React + TypeScript + Vite

### Community 371 - "use-memory-viewmodel.ts"
Cohesion: 0.67
Nodes (3): MemoryViewModel, messageFor(), useMemoryViewModel()

### Community 372 - "use-run-report-viewmodel.ts"
Cohesion: 0.67
Nodes (3): messageFor(), RunReportViewModel, useRunReportViewModel()

### Community 373 - "findings-list.tsx"
Cohesion: 0.67
Nodes (3): FindingsList(), OUTCOME_LABEL, toneFor()

### Community 377 - "Continue RoveQA with Opus 5"
Cohesion: 0.50
Nodes (3): Contexto crítico que no debes redescubrir, Continue RoveQA with Opus 5, Pasos obligatorios, en orden

## Knowledge Gaps
- **1292 isolated node(s):** `$schema`, `Read(./.env)`, `Read(./.env.local)`, `Read(./.env.development)`, `Read(./.env.production)` (+1287 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **57 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RunPolicy` connect `RunPolicy` to `BrowserAction`, `NotFoundError`, `InvalidEntityError`, `run_policy.py`, `RunActivities`, `TestPlan`, `test_policy_resolution.py`, `CriterionOutcome`, `postgres/repositories.py`, `langgraph/graph.py`, `TestWhatItDeclinedToTake`, `ScriptedModelGateway`, `ActionTarget`, `CriterionResult`, `ClusterHypothesis`, `Container`, `Repositories`, `normalize_origin`, `container.py`, `AlreadyExistsError`, `FailureKind`, `projects.py`, `test_gateway.py`, `routers/schedules.py`, `Frontier`, `PostgresFailureClusterRepository`, `Quality`, `Affordance`, `ModelEndpoint`, `CandidateStatus`, `page`, `NewRunEvent`, `seed_project_with_default_policy`, `policy`, `ExplorationProgress`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `KnowledgeExperienceCandidate` connect `KnowledgeExperienceCandidate` to `InvalidEntityError`, `TestPlan`, `CriterionOutcome`, `postgres/repositories.py`, `from_document`, `routers/memory.py`, `CriterionResult`, `ClusterHypothesis`, `Container`, `GraphitiMemoryProjection`, `sync_pending`, `AlreadyExistsError`, `unit_of_work_factory`, `experience.py`, `PostgresFailureClusterRepository`, `compatibility_of`, `Quality`, `contradicted_by`, `ModelEndpoint`, `apply_feedback`, `CandidateKind`, `CandidateStatus`, `NewRunEvent`, `select`, `MemoryContextRequest`, `seed_project_with_default_policy`, `test_memory_in_the_prompt.py`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `Container` connect `Container` to `FilesystemArtifactRepository`, `NotFoundError`, `test_exploring_a_real_run.py`, `AsyncClient`, `RunPolicy`, `UnitOfWork`, `RunActivities`, `PlanningRequest`, `langgraph/graph.py`, `test_realtime.py`, `routers/memory.py`, `CriterionResult`, `ClusterHypothesis`, `conftest.py`, `container.py`, `test_api_contract.py`, `routers/schedules.py`, `worker.py`, `test_memory_api.py`, `ModelEndpoint`, `list_run_events.py`, `test_temporal_workflow.py`, `MemoryMetrics`, `test_deep_analysis_activity.py`, `test_schedules_api.py`, `test_database_failure.py`, `routers/exploration.py`, `Settings`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 98 inferred relationships involving `KnowledgeExperienceCandidate` (e.g. with `ConsolidateExperienceCommand` and `ConsolidateExperienceResult`) actually correct?**
  _`KnowledgeExperienceCandidate` has 98 INFERRED edges - model-reasoned connections that need verification._
- **Are the 113 inferred relationships involving `RunPolicy` (e.g. with `CreateRunPolicyCommand` and `EpisodeRequest`) actually correct?**
  _`RunPolicy` has 113 INFERRED edges - model-reasoned connections that need verification._
- **Are the 114 inferred relationships involving `Run` (e.g. with `StartRunCommand` and `StartRunResult`) actually correct?**
  _`Run` has 114 INFERRED edges - model-reasoned connections that need verification._
- **Are the 88 inferred relationships involving `CriterionResult` (e.g. with `ConsolidateExperienceCommand` and `ConsolidateExperienceResult`) actually correct?**
  _`CriterionResult` has 88 INFERRED edges - model-reasoned connections that need verification._