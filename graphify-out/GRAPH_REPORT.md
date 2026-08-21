# Graph Report - roveqa  (2026-08-21)

## Corpus Check
- 559 files · ~273,154 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 6648 nodes · 17001 edges · 469 communities (408 shown, 61 thin omitted)
- Extraction: 79% EXTRACTED · 21% INFERRED · 0% AMBIGUOUS · INFERRED: 3546 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `902882aa`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- RunPolicy
- FilesystemArtifactRepository
- application/errors.py
- properties
- devDependencies
- InMemoryResourceSemaphore
- LockHandle
- memory-context.schema.json
- AsyncClient
- InvalidEntityError
- http/schemas.py
- properties
- properties
- ports/unit_of_work.py
- UnitOfWork
- RunActivities
- PlanningRequest
- test_policy_resolution.py
- RecoveryPoint
- RecordingBrowserGateway
- postgres/repositories.py
- postgres_test_dsn
- langgraph/graph.py
- test_realtime.py
- ScriptedModelGateway
- null
- compilerOptions
- BrowserSession
- triage
- InMemoryProjectRepository
- PostgresUnitOfWork
- FailureCluster
- InMemoryUnitOfWork
- null
- properties
- RunEvent
- properties
- prepared_container
- Run
- RunStatus
- properties
- compilerOptions
- NotFoundError
- redis/streams.py
- required
- request_context.py
- properties
- properties
- projection.py
- sync_pending
- CriterionResult
- test_budget_and_classification.py
- root_cause_hypothesis
- budget
- enum
- required
- projects.py
- consolidate_experience
- test_gateway.py
- BrowserAction
- enum
- properties
- deny
- test-plan.schema.json
- projects-page.tsx
- GraphitiMemoryProjection
- RecordingWorkflowGateway
- build_worker
- test_layer_boundaries.py
- FailingWorkflowGateway
- Quality
- KnowledgeExperienceCandidate
- browser-action.schema.json
- properties
- properties
- validity
- items
- env.py
- ModelCapability
- main.ts
- list_events
- activities.py
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
- GraphSyncRecord
- cli/package.json
- fakes/unit_of_work.py
- analyze_failures.py
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
- config.ts
- agent-action.schema.json
- enum
- required
- enum
- error
- failure-bundle.schema.json
- unit_of_work_factory
- type
- side_effect
- required
- items
- enum
- RunSchedule
- verification_strategy
- expected_postconditions
- message
- type
- freshness
- reliability
- mappers.py
- summary
- Container
- environment_id
- clustering.py
- run_policy_id
- run_for
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
- InMemoryGraphMemory
- seed_project_with_default_policy
- PageState
- signal_from
- CriterionOutcome
- test_memory_api.py
- DeepAnalysisService
- apply_feedback
- test_temporal_workflow.py
- errors.ts
- schemas.ts
- test_graphiti_projection.py
- ClusterHypothesis
- run_story
- agentic-qa
- StateMap
- compilerOptions
- test_operational_queries.py
- api.ts
- agent.ts
- diff.ts
- parse_affordances
- VLLMModelGateway
- test_deep_analyst.py
- commands/memory.ts
- Patterns adopted
- client.ts
- MemoryMetrics
- InMemoryStore
- record_finished_run
- API and Event Contracts
- ports/gateways.ts
- test_database_failure.py
- bundle.test.ts
- flaky.ts
- Runtime responsibilities
- dependencies
- MemoryContextRequest
- envelope.test.ts
- test_memory_benchmark_real_model.py
- policy
- Combination rules
- FailureKind
- container.py
- PostgresKnowledgeRepository
- Guía de uso
- finished_run
- Bounded contexts
- runs/run.ts
- test_evidence_chain.py
- test_triage_from_a_real_run.py
- Agent-First CLI Design
- Operations Runbook
- start-run.ts
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
- fakes.ts
- UserStory
- StoredCluster
- Claude Code Project Instructions
- Data and Artifacts
- Testing Strategy
- ADR 0008 — Adaptive QA Learning Graph with Graphiti + FalkorDB
- HttpRunGateway
- FakeRunGateway
- JudgementRequest
- Session Handoff
- Interface System
- Security Model
- Observability
- Development-Time Codebase Graph (Graphify)
- Memory Evaluation — reach the records page
- Release Checklist
- run-events.ts
- Memory Evaluation — <flow>
- test_migrations_from_empty.py
- API design principles
- Error handling patterns
- plan_of
- Agent Runtime
- Docker Compose Topology
- ADR 0009 — Run workflow shape, retry ownership and checkpoint reconciliation
- stories-page.test.tsx
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
- parse
- use-projects-viewmodel.ts
- use-run-viewmodel.ts
- .analyze
- Phase 06 — vLLM + Model Router
- Phase 09 — Adaptive QA Learning Graph (Graphiti + FalkorDB)
- demo.sh
- Interface design
- Ponytail — minimal safe engineering
- Systematic debugging
- Backend Clean Architecture
- Frontend — Clean Architecture + MVVM
- ADR 0010 — Transaction ownership: commands own a UnitOfWork, queries take repositories
- README.md
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
- toProject
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
- RoveQA
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
- memory-page.test.tsx
- projects-page.test.tsx
- routers/artifacts.py
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
- jsdom
- @testing-library/react
- @testing-library/user-event
- typescript-eslint
- vite
- vitest
- project.ts
- frontend/test/boundaries.test.ts
- plans/README.md
- CONTINUE_SESSION.md
- PHASE_REVIEW.md
- START_HERE.md
- .oxlintrc.json
- client
- step_id
- to_psycopg_dsn
- TestClosedActionSet
- TestTheSystemPromptSaysHowFarToTrustMemory
- plan_id
- project_id
- read_contracts
- valid_from
- @types/react
- @types/react-dom

## God Nodes (most connected - your core abstractions)
1. `RunPolicy` - 189 edges
2. `KnowledgeExperienceCandidate` - 172 edges
3. `Run` - 157 edges
4. `CriterionResult` - 153 edges
5. `NotFoundError` - 142 edges
6. `BrowserAction` - 141 edges
7. `UnitOfWork` - 138 edges
8. `Project` - 119 edges
9. `Verdict` - 115 edges
10. `InvalidEntityError` - 106 edges

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

## Communities (469 total, 61 thin omitted)

### Community 0 - "RunPolicy"
Cohesion: 0.05
Nodes (73): ActionDeniedError, GuardedBrowserGateway, _is_navigation(), Exception, A browser gateway that cannot execute what the policy forbids.  Enforcement live, Actions that can move the page, and therefore can land somewhere else.      `bac, The run policy forbade an action; it was never executed., ActionTarget (+65 more)

### Community 1 - "FilesystemArtifactRepository"
Cohesion: 0.07
Nodes (33): ArtifactTooLargeError, Exception, The artifact exceeded the configured cap and was not stored., One run, one evidence set. Checked here rather than trusted downstream., _require_single_provenance(), EvidenceContaminationError, EvidenceSet, A manifest was asked to hold artifacts that do not share one provenance. (+25 more)

### Community 2 - "application/errors.py"
Cohesion: 0.06
Nodes (53): ArtifactRepositoryDep, compile_plan(), CompilePlanCommand, _next_version(), Compile a user story into a stored, versioned TestPlan.  Versioning is the point, Monotonic integers as strings. The contract allows any string; sequential     in, content_version(), import_plan() (+45 more)

### Community 3 - "properties"
Cohesion: 0.04
Nodes (48): additionalProperties, default, type, default, type, items, type, default (+40 more)

### Community 4 - "devDependencies"
Cohesion: 0.11
Nodes (19): eslint-plugin-react-hooks, eslint-plugin-react-refresh, devDependencies, eslint, eslint-plugin-react-hooks, eslint-plugin-react-refresh, tailwindcss, @tailwindcss/vite (+11 more)

### Community 5 - "InMemoryResourceSemaphore"
Cohesion: 0.13
Nodes (9): Take a slot, or None when the resource is already at capacity., Extend a held slot. False when the lease already lapsed., Give the slot back. False when this reservation no longer holds one., SlotReservation, _millis(), Redis, Redis resource semaphore.  One sorted set per resource: members are reservation, RedisResourceSemaphore (+1 more)

### Community 6 - "LockHandle"
Cohesion: 0.09
Nodes (25): LockHandle, LockManager, Protocol, Distributed lock port.  Locks are coordination, never truth (docs/09, ADR 0003):, Return a handle, or None when the lock is already held., Extend the lease. False when the token no longer owns the key., Release only if still the owner. False when the token no longer owns it., _millis() (+17 more)

### Community 7 - "memory-context.schema.json"
Cohesion: 0.17
Nodes (11): additionalProperties, $id, environment_id, project_id, schema_version, required, $schema, title (+3 more)

### Community 8 - "AsyncClient"
Cohesion: 0.06
Nodes (35): LogRecord, RequestIdLogFilter, asgi_client(), captured_error_logs(), client(), create_project(), ExplodingUnitOfWork, AsyncClient (+27 more)

### Community 9 - "InvalidEntityError"
Cohesion: 0.03
Nodes (75): AcceptanceCriterion, Episode execution port.  One activity per episode (ADR 0009), and the activity s, Durable state maps.  An exploration's value is comparative. One map says what an, TestPlan repository port.  Plans are immutable per version, so there is no `save, Repository ports consumed by the Application layer.  Protocols only: no ORM, d, Criterion result repository port.  Results are written once per run and read b, Recurring runs.  A schedule is durable state, and it has exactly one owner: Temp, The coherent snapshot a FailureBundle is built from.  "Coherent" is the whole (+67 more)

### Community 10 - "http/schemas.py"
Cohesion: 0.07
Nodes (85): Append durably, assigning the next per-run sequence.          Called inside the, RunEvent, A recurring run, described the way the caller asked for it.      Carries the pla, RunSchedule, ExplorationOutcome, Project, RunPolicy, UserStory (+77 more)

### Community 11 - "properties"
Cohesion: 0.06
Nodes (36): items, type, type, type, items, type, type, $id (+28 more)

### Community 12 - "properties"
Cohesion: 0.06
Nodes (30): items, type, type, $id, type, payload, run_id, type (+22 more)

### Community 13 - "ports/unit_of_work.py"
Cohesion: 0.13
Nodes (10): ProjectRepository, Project, Protocol, UserStory, Persist a new project. Raises AlreadyExistsError when the id is taken., Newest first, bounded. There is no unbounded listing: a page size is a, Persist changes to an existing project. Raises NotFoundError when gone., Persist a new story. Raises AlreadyExistsError when the id is taken. (+2 more)

### Community 14 - "UnitOfWork"
Cohesion: 0.03
Nodes (54): Analyse a finished run's failures: group first, ask a model second, store both., _store_hypotheses(), consolidate_experience(), ConsolidateExperienceResult, _invalidate_what_this_run_disproved(), datetime, Consolidate a finished run into durable knowledge.  Runs once per run, enforce, Withdraw memory this run's deterministic results disprove.      The other half (+46 more)

### Community 15 - "RunActivities"
Cohesion: 0.10
Nodes (35): ConsolidateExperienceCommand, EpisodeResult, EpisodeRunner, Protocol, The criterion a report leads with. Deterministic failures come first,         b, CriterionOutcome, CriterionResult, BrowserRecoveryData (+27 more)

### Community 16 - "PlanningRequest"
Cohesion: 0.26
Nodes (9): build_planning_prompt(), The user message: goal, bounded history and the delimited observation., candidate(), How recalled memory reaches a model, and what the wording has to protect.  Memor, request(), test_a_cold_run_gets_no_memory_block_at_all(), test_an_expired_item_never_reaches_the_prompt(), test_memory_appears_before_the_page_so_the_page_is_read_last() (+1 more)

### Community 17 - "test_policy_resolution.py"
Cohesion: 0.05
Nodes (34): AriaRole, ActionOutcome, PageProblems, Exception, Protocol, Browser gateway port.  Application asks for typed actions and never touches Play, The gateway cannot carry out this action as described.      A fact about the *at, What actually happened, kept separate from what was intended. (+26 more)

### Community 19 - "RecordingBrowserGateway"
Cohesion: 0.09
Nodes (32): Any, No model gateway exists until Phase 06; the worker must not fake an episode., run_with_compatible_loop(), test_the_activity_runs_the_graph_and_records_a_recovery_point(), test_without_a_configured_runtime_the_activity_says_so_instead_of_pretending(), AlwaysFailingBrowser, click(), navigate() (+24 more)

### Community 20 - "postgres/repositories.py"
Cohesion: 0.03
Nodes (91): artifact_to_domain(), artifact_to_model(), _budget_to_column(), _budget_to_domain(), criterion_result_to_domain(), criterion_result_to_model(), environment_to_domain(), environment_to_model() (+83 more)

### Community 21 - "postgres_test_dsn"
Cohesion: 0.03
Nodes (90): AsyncPostgresSaver, open_checkpointer(), Open a checkpointer and make sure its tables exist.      `setup()` is idempote, Translate `postgresql+asyncpg://...` into the plain URL psycopg expects., to_psycopg_dsn(), counting_graph(), CountingState, Any (+82 more)

### Community 22 - "langgraph/graph.py"
Cohesion: 0.03
Nodes (89): main(), prompt_for(), Measure what grows, and print it.  Run inside the gates container:      dock, run_for(), table_sizes(), test_dsn(), ArtifactRepository, Artifact storage port.  Filesystem today, S3/MinIO later (ADR 0005) — which is (+81 more)

### Community 23 - "test_realtime.py"
Cohesion: 0.10
Nodes (25): create_app(), FastAPI, Build the API. Passing a container lets tests wire their own adapters., BrokenRunEventPublisher, InMemoryRunEventPublisher, InMemoryRunEventSubscription, RunEvent, In-memory run event publisher with the same delivery semantics as Redis. (+17 more)

### Community 24 - "ScriptedModelGateway"
Cohesion: 0.05
Nodes (60): BrowserGateway, Capture the page as it is now.          A capability rather than an action outco, ActionRecord, One thing the agent asked the browser to do, and what came back.      Enough to, CriterionJudgement, JudgementRequest, Ask a model whether an acceptance criterion looks satisfied.      Last in the ve, _check_deterministically() (+52 more)

### Community 25 - "null"
Cohesion: 0.13
Nodes (24): type, type, null, string, format, type, description, type (+16 more)

### Community 26 - "compilerOptions"
Cohesion: 0.05
Nodes (38): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, exactOptionalPropertyTypes, jsx, lib, module (+30 more)

### Community 27 - "BrowserSession"
Cohesion: 0.03
Nodes (117): perform_once(), Verify before retry.  The mandatory case from docs/05: the target processed `Cre, Perform an effect at most once, deciding by observation rather than by memory., SideEffectOutcome, BrowserSession, BaseException, Self, TracebackType (+109 more)

### Community 28 - "triage"
Cohesion: 0.15
Nodes (11): Group failures and mark the ones that were only consequences.      Determinist, triage(), failure(), CriterionOutcome, FailureKind, Deterministic failure triage.  Three of the five Phase 11 gates live here, and a, signal(), TestCascadeIsNotTwelveBugs (+3 more)

### Community 29 - "InMemoryProjectRepository"
Cohesion: 0.07
Nodes (20): Where the page is and what it offers, as roles and accessible names.          Re, _clickable(), Default when no policy is supplied: anything a click could take.      Used by, Affordance, normalize_name(), _normalize_segment(), PageState, The action that takes this affordance, named the way the action set names it. (+12 more)

### Community 30 - "PostgresUnitOfWork"
Cohesion: 0.08
Nodes (6): PostgresUnitOfWork, async_sessionmaker, AsyncSession, BaseException, Self, TracebackType

### Community 31 - "FailureCluster"
Cohesion: 0.22
Nodes (5): FailureClusterRepository, datetime, Protocol, Upsert clusters and accumulate their members.          Idempotent by `(project_i, Attach an interpretation to a cluster. False when this pass already did.

### Community 32 - "InMemoryUnitOfWork"
Cohesion: 0.12
Nodes (17): resolve_run_policy(), make_policy(), RunPolicy resolution order (docs/12).  A run without a resolved policy has no or, A misconfigured default is an error, not a reason to use a weaker policy., seed(), test_a_dangling_reference_fails_instead_of_falling_through(), test_a_policy_from_another_project_is_refused(), test_an_environment_of_another_project_is_refused() (+9 more)

### Community 33 - "null"
Cohesion: 0.12
Nodes (22): maxLength, type, description, pattern, type, type, null, object (+14 more)

### Community 34 - "properties"
Cohesion: 0.09
Nodes (22): minLength, type, format, type, minLength, type, type, type (+14 more)

### Community 35 - "RunEvent"
Cohesion: 0.07
Nodes (34): Start a run, idempotently.  Ordering is the durability contract (ADR 0010): th, Pin the plan version now, or run without a plan (exploratory).      Resolving, _resolve_plan(), start_run(), StartRunResult, Run, Move a run to a new lifecycle state.  Every status change goes through the domai, transition_run() (+26 more)

### Community 36 - "properties"
Cohesion: 0.10
Nodes (21): minLength, type, minLength, type, properties, minLength, type, artifact_id (+13 more)

### Community 37 - "prepared_container"
Cohesion: 0.16
Nodes (18): compatibility_of(), _confirmed(), _differs(), _needs_check(), datetime, Both sides known and not equal — a positive mismatch, not a gap., Both sides known and equal — the situation was actually checked, not assumed., Version-like context: a mismatch is not disqualifying, but it is not free. (+10 more)

### Community 38 - "Run"
Cohesion: 0.24
Nodes (9): Repositories, make_story(), Project, UserStory, Repository contract suite.  Every implementation of the ports must satisfy these, seed_project(), TestProjectRepository, TestRunRepository (+1 more)

### Community 39 - "RunStatus"
Cohesion: 0.20
Nodes (16): A run lifecycle invariant was violated., RunTransitionError, make_run(), Run, RunStatus, Run lifecycle invariants (Phase 01 slice 1)., test_any_non_terminal_status_may_fail(), test_cancel_flow_forces_cancelled_verdict() (+8 more)

### Community 40 - "properties"
Cohesion: 0.10
Nodes (20): minimum, type, minimum, type, contradiction_count, failure_count, quality, reliability (+12 more)

### Community 41 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+11 more)

### Community 42 - "NotFoundError"
Cohesion: 0.05
Nodes (55): Run, Persist a new run. Raises AlreadyExistsError when the id is taken., Persist changes to an existing run. Raises NotFoundError when it is gone., RunRepository, CriterionResultRepository, Protocol, Store results for a run, replacing any previous answer for the same criteria., Deterministic failures across a project's recent runs, newest run first. (+47 more)

### Community 43 - "redis/streams.py"
Cohesion: 0.14
Nodes (21): browser_clicks_within_depth(), crawlable_policy(), explore(), explore_with_policy(), page(), _path_of(), The agent graph in exploration mode.  The claim being tested is not "it clicks, Sanity check on the fixture rather than on the code under test. (+13 more)

### Community 44 - "required"
Cohesion: 0.11
Nodes (18): additionalProperties, $id, candidate_id, environment_id, kind, model_derived, observed, payload (+10 more)

### Community 45 - "request_context.py"
Cohesion: 0.15
Nodes (17): _flag(), _optional_positive_int(), _positive_float(), _positive_int(), Runtime configuration read from the environment.  Secrets never live in code or, A misconfigured limit fails at startup, not as strange behaviour under load., None when unset, so the adapter's own default stays the single source of truth., analyst() (+9 more)

### Community 46 - "properties"
Cohesion: 0.11
Nodes (18): minLength, type, format, type, minLength, type, minLength, type (+10 more)

### Community 47 - "properties"
Cohesion: 0.11
Nodes (18): maxLength, minLength, type, default, type, properties, criterion_id, critical (+10 more)

### Community 48 - "projection.py"
Cohesion: 0.12
Nodes (13): EmbeddingGateway, Protocol, Embedding gateway port.  A separate port from `ModelGateway` because the two fai, Which model produced the vectors.          Recorded with the projection: embeddi, Vectors in the same order as the inputs.          Raises rather than returning s, _as_texts(), GraphitiEmbedder, GraphMemoryModelUseError (+5 more)

### Community 49 - "sync_pending"
Cohesion: 0.16
Nodes (12): Create a project plus the default policy a run needs to start., seed_project_with_default_policy(), InMemoryGraphMemory, In-memory doubles for the graph projection.  `InMemoryGraphMemory` is a working, A projection that behaves like the real one, including being wipeable., promoted_knowledge(), Factory, Keeping the projection in step, and surviving it being gone.  The properties wor (+4 more)

### Community 50 - "CriterionResult"
Cohesion: 0.10
Nodes (20): A6 — the planner clicks a link it could navigate to, A7 — a refusal that carries the correction, A8 — a control that already has something in it, Agent findings — Phase 15, And one defect in the harness itself, Before and after, same story, same site, same model, How these were found, Measured again, with three repeats (+12 more)

### Community 51 - "test_budget_and_classification.py"
Cohesion: 0.06
Nodes (36): PlannedAction, The planner's decision.      Three outcomes, deliberately distinguishable:, PlanStep, steps_by_criterion(), FailureKind, StrEnum, Why a criterion is not met — the classification docs/00 asks a report to make., assertion() (+28 more)

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
Cohesion: 0.27
Nodes (8): create_project(), CreateProjectCommand, Project, Create a project.  Commands own their transaction and commit; queries take repos, create_run_policy(), CreateRunPolicyCommand, Create a run policy, optionally making it the project default.  Policies are imm, TestCreateProject

### Community 57 - "consolidate_experience"
Cohesion: 0.15
Nodes (16): Build fresh units of work over one shared store/database.      A factory rathe, unit_of_work_factory(), UnitOfWorkFactory, Unit-of-work contract suite.  Both implementations must give the same transact, A run written next to its project must be atomic with it, not half-committed., test_an_exception_rolls_back_every_write_in_the_block(), test_commit_makes_writes_visible_to_a_later_transaction(), test_leaving_the_block_without_commit_rolls_back() (+8 more)

### Community 58 - "test_gateway.py"
Cohesion: 0.16
Nodes (19): In-memory resource semaphore with real lease expiry., completion(), make_policy(), plan_once(), Any, The phase gate: invalid model output never reaches the browser.  These run the *, The gate itself: drive the real graph and assert the browser stayed idle., The model can propose anything; a read-only run executes none of it. (+11 more)

### Community 59 - "BrowserAction"
Cohesion: 0.09
Nodes (23): BrowserDecision, One step the planner proposes, as a union the server can actually enforce., What a model is allowed to say, and what happens when it says something else.  T, The flag works in the safe direction: a GET that confirms something is a write., `model_derived` is pinned to True: a hypothesis never becomes evidence., What used to live only as prose in the prompt.      The planner answered `{"acti, The drift guard. A member added to the enum or to either requirement set, The closed action set is the control, so `evaluate` fails as an unknown value. (+15 more)

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

### Community 64 - "projects-page.tsx"
Cohesion: 0.13
Nodes (9): root, GatewaysContext, prefersDark(), ThemeViewModel, useTheme(), DEFAULTS, FormValues, schema (+1 more)

### Community 65 - "GraphitiMemoryProjection"
Cohesion: 0.19
Nodes (7): GraphitiMemoryProjection, Create exactly the indices this projection needs. Idempotent., Ensure the indices exist, once per instance.          Lazy rather than done in t, Range indices for the properties we filter on, plus the `Entity` full-text, Implements `GraphMemoryPort` over FalkorDB., The guard against acquiring a hosted dependency by omission.      Graphiti's o, test_the_projection_never_builds_a_hosted_client()

### Community 66 - "RecordingWorkflowGateway"
Cohesion: 0.07
Nodes (33): create_story(), CreateStoryCommand, UserStory, Create a user story for an existing project., StartRunCommand, Durable idempotency records.  A lost response must never cost a second run or, get_project(), Project (+25 more)

### Community 67 - "build_worker"
Cohesion: 0.16
Nodes (10): One workflow per run: the id makes a duplicate start a no-op, not a second run., workflow_id_for(), Client, Temporal adapter for the WorkflowGateway port., TemporalWorkflowGateway, build_worker(), main(), Client (+2 more)

### Community 68 - "test_layer_boundaries.py"
Cohesion: 0.31
Nodes (12): forbidden_imports(), imported_modules(), layer_files(), Path, The dependency rule is a test, not a review habit.      Interfaces/Delivery --, Policy enforcement lives in a wrapper, so the raw adapter must stay contained., A guard that cannot fail proves nothing: plant a violation and expect a catch., test_guard_allows_stdlib_and_own_layer() (+4 more)

### Community 69 - "FailingWorkflowGateway"
Cohesion: 0.10
Nodes (20): ADRs requeridos, Fuera de alcance, Gates de fase, La evidencia que define la fase, Objective, Phase 15 — Agent Reliability, Principio, Slice 0 — Medida antes de tocar nada, y sobre más de un arquetipo (+12 more)

### Community 70 - "Quality"
Cohesion: 0.10
Nodes (15): datetime, Quality, Evidence counts and the reliability derived from them.      `reliability` is c, Successes against everything that went wrong, with contradictions counted, candidate(), What a candidate is allowed to become.  These are the rules that decide what a, The single rule that keeps a guess from turning into something acted upon., test_a_candidate_from_nowhere_is_refused() (+7 more)

### Community 71 - "KnowledgeExperienceCandidate"
Cohesion: 0.06
Nodes (28): KnowledgeRepository, CandidateStatus, Store a candidate, folding it into an equivalent one when it already exists., Candidates for one project and environment, newest first.          Scope is a, Persist a status or quality change on an existing candidate., KnowledgeExperienceCandidate, Two sightings of the same fact, added together.          Counts add rather tha, Identity of the *fact*, so a second run that sees the same thing adds         s (+20 more)

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

### Community 78 - "ModelCapability"
Cohesion: 0.07
Nodes (44): Wiring for the agent runtime: model, browser and checkpointer.  Separate from `c, capability_for(), InferenceBudget, ModelCapability, StrEnum, Inference task types and capabilities (docs/08).  The domain names *what kind of, What a task needs, not who provides it., Bounds every call carries. An unbounded model call is an unbounded run. (+36 more)

### Community 79 - "main.ts"
Cohesion: 0.11
Nodes (55): hasErrors(), lintPlan(), readPlanFile(), scaffoldPlan(), failureContext(), unclassified(), usage(), agentInstall() (+47 more)

### Community 80 - "list_events"
Cohesion: 0.11
Nodes (17): 1. El estado HTTP se descarta, 2. Los errores de consola y las peticiones fallidas se capturan y nadie los lee, ADRs requeridos, De dónde salen estos hallazgos, El problema de fondo: una landing no tiene historia, Fuera de alcance, Gates de fase, Los dos huecos (+9 more)

### Community 81 - "activities.py"
Cohesion: 0.15
Nodes (17): Bring the graph projection up to date. Returns how many nodes it wrote., ConsolidateParams, EpisodeOutcome, EpisodeParams, Serializable payloads exchanged between workflow and activities.  Kept free of, One firing, with the key that makes it exactly one run.      `idempotency_key`, Nothing to carry: the backlog lives in PostgreSQL and names its own work., Result of one episode.      `more_work` is what ends the loop. Phase 05 replac (+9 more)

### Community 82 - "vllm/gateway.py"
Cohesion: 0.11
Nodes (16): InferenceError, ModelUnavailableError, Exception, Base for every failure of the inference layer., The endpoint could not be reached, timed out, was saturated, or is tripped., Any, BaseModel, Response (+8 more)

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
Cohesion: 0.14
Nodes (21): consolidate(), ConsolidationInput, _from_result(), _origin_of(), datetime, Turn a finished run into knowledge candidates.  Only *verified* outcomes becom, Scheme and host, without the path. The origin is the part that decides whether, One criterion's verified outcome, or a reason it taught nothing. (+13 more)

### Community 91 - "test_schema_constraints.py"
Cohesion: 0.35
Nodes (12): knowledge_values(), AsyncSession, The durable schema must defend the run invariants, not just the Python layer.  A, The rule the whole learning design rests on, defended below the Python layer., seed(), test_a_model_derived_candidate_cannot_be_trusted_in_the_database(), test_criterion_ids_are_unique_within_a_story(), test_knowledge_must_come_from_somewhere() (+4 more)

### Community 92 - "properties"
Cohesion: 0.22
Nodes (9): minLength, type, type, properties, intent, payload, type, minLength (+1 more)

### Community 93 - "properties"
Cohesion: 0.22
Nodes (9): type, evidence_set_id, model_invocation_id, source_episode_id, source_run_id, properties, type, minLength (+1 more)

### Community 94 - "GraphSyncRecord"
Cohesion: 0.19
Nodes (10): NavEntry, IconProps, MemoryIcon, MenuIcon, MoonIcon, PlusIcon, ProjectsIcon, RunIcon (+2 more)

### Community 95 - "cli/package.json"
Cohesion: 0.06
Nodes (34): ajv, bin, roveqa, dependencies, ajv, devDependencies, eslint, @eslint/js (+26 more)

### Community 96 - "fakes/unit_of_work.py"
Cohesion: 0.07
Nodes (92): AnalyzeFailuresResult, _freshness_rule(), Ask about a cluster only when the answer could have changed.      This is the, AlreadyExistsError, A repository rejected an insert because the identity is already taken.      Adap, ClusterHypothesis, HypothesisConfidence, StrEnum (+84 more)

### Community 97 - "analyze_failures.py"
Cohesion: 0.20
Nodes (18): analyze_failures(), AnalyzeFailuresCommand, datetime, CountingAnalyst, failure(), Factory, FailureKind, The run-boundary pass: group, ask, store — and survive being interrupted.  Par (+10 more)

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
Nodes (30): Protocol, Bounded resource reservations (browser slots, model slots, accounts).  Every res, Slots currently held, excluding lapsed ones., ResourceSemaphore, Resource semaphore contract.  Capacity must hold under concurrency, and a worker, Check-then-add must be atomic: ten racing callers, two slots., A worker that died holding a slot must not shrink the pool forever., test_a_lapsed_slot_is_reclaimed() (+22 more)

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
Cohesion: 0.12
Nodes (20): _item_document(), Any, The portable MemoryContext document (`contracts/memory-context.schema.json`).  O, to_document(), MemoryContext, No usable memory. The run explores as if it were the first one., Filter, rank and bound. The last gate before memory reaches a prompt.      Sco, select() (+12 more)

### Community 110 - "test_schedules_api.py"
Cohesion: 0.10
Nodes (15): InMemoryScheduleGateway, In-memory schedule gateway.  Mirrors the two behaviours the endpoints depend on:, client(), client_for(), gateway(), AsyncClient, The scheduling endpoints over real HTTP.  What matters here is not that a POST, A 201 for a schedule nobody stored is the worst possible answer here. (+7 more)

### Community 112 - "config.ts"
Cohesion: 0.13
Nodes (18): readExisting(), setup(), SetupInput, SetupResult, asPositiveInt(), asString(), ConfigFlags, describe() (+10 more)

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

### Community 119 - "unit_of_work_factory"
Cohesion: 0.28
Nodes (9): record_memory_feedback(), RecordMemoryFeedbackCommand, CandidateStatus, Factory, A run plus one piece of knowledge a later run could act on., seed_playbook(), TestGraphSyncIsSeparateFromBelief, TestOneOutcomeIsCountedOnce (+1 more)

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

### Community 125 - "RunSchedule"
Cohesion: 0.10
Nodes (25): Namespaced so a schedule and a run can never collide in Temporal's id space., What one firing of a schedule needs to create its run.      No run id: the run, schedule_id_for(), ScheduledRunParams, Client, Temporal adapter for the ScheduleGateway port.  Temporal is the only store for, Listed from Temporal and filtered here.          Temporal's list is eventually, Rebuild the domain shape from what Temporal stored.          The action's argu (+17 more)

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

### Community 132 - "mappers.py"
Cohesion: 0.06
Nodes (50): _budget_document(), _budget_from(), _enum(), from_document(), _metadata_from(), _optional_int(), _optional_str(), Any (+42 more)

### Community 133 - "summary"
Cohesion: 0.50
Nodes (4): summary, maxLength, minLength, type

### Community 134 - "Container"
Cohesion: 0.04
Nodes (61): Protocol, Durable workflow port.  Temporal owns the run lifecycle (ADR 0002/0009) but Ap, Start the durable workflow for an already-persisted run.          Naturally id, Ask the run to stop at its next safe point. Idempotent., WorkflowGateway, list_run_events(), RunEvent, build_container() (+53 more)

### Community 135 - "environment_id"
Cohesion: 0.50
Nodes (4): maxLength, minLength, type, environment_id

### Community 136 - "clustering.py"
Cohesion: 0.09
Nodes (24): Reduce stored results to comparable signals, dropping what cannot be grouped., _signals(), _build_cluster(), _cluster_id(), ClusterStatus, StrEnum, Grouping failures, and telling causes apart from consequences.  Two jobs, both, What is worth sending to a model, if anything is.          Only independent cl (+16 more)

### Community 137 - "run_policy_id"
Cohesion: 0.50
Nodes (4): run_policy_id, maxLength, minLength, type

### Community 138 - "run_for"
Cohesion: 0.21
Nodes (12): Deep analysis port: what a large model may be asked about a failure cluster., build_cluster_analysis_prompt(), build_judgement_prompt(), _clip(), _neutralize(), _neutralize_observation(), Prompt construction for planning decisions.  Two properties this module exists t, One line per item, each carrying the two labels that decide how far to trust it. (+4 more)

### Community 144 - "TestPlan"
Cohesion: 0.20
Nodes (5): Protocol, Store a new plan version. Raises AlreadyExistsError if that version exists., Most recently created version. Used to *choose* a version at run creation,, Plan versions compiled from a story, newest first., TestPlanRepository

### Community 145 - "action_id"
Cohesion: 0.67
Nodes (3): minLength, type, action_id

### Community 146 - "test_client.py"
Cohesion: 0.12
Nodes (27): CircuitBreaker, Circuit breaker for a model endpoint.  When a GPU box is down, thirty-second tim, True when a call may be attempted, half-opening after the cooldown., ModelOutputError, The model answered with something that does not satisfy the contract.      Carri, ask(), build_client(), completion() (+19 more)

### Community 147 - "Adaptive QA Learning Graph"
Cohesion: 0.06
Nodes (31): 1. Hard filters, 2. Candidate search, 3. Ranking, 4. Bounded context, 5. Revalidation, Adaptive QA Learning Graph, ExperienceConsolidator, Goal (+23 more)

### Community 151 - "HANDOFF.md"
Cohesion: 0.06
Nodes (30): Acceptance Gates (Phase 07), Acceptance Gates (Phase 08), Acceptance Gates (Phase 09), Acceptance Gates (Phase 10), Acceptance Gates (Phase 11), Acceptance Gates (Phase 12), Acceptance Gates (Phase 13), Architecture Decisions Made (+22 more)

### Community 153 - "from_document"
Cohesion: 0.14
Nodes (24): _enum(), from_document(), _optional_timestamp(), Any, datetime, EnumT, The portable knowledge document (`contracts/knowledge-experience.schema.json`)., Serialize to the public contract.      Optionals inside `provenance` and `vali (+16 more)

### Community 156 - "redact_payload"
Cohesion: 0.07
Nodes (31): Turning a URL into something safe to keep.  Applications put credentials in URLs, Scheme, host and path. No query, no fragment, no userinfo.      Query strings an, safe_url(), _clean_text(), Any, Exception, Redaction before anything is learned.  Memory outlives the run that produced it,, Clean a string that is *evidence*, keeping it rather than refusing it.      `red (+23 more)

### Community 157 - "routers/memory.py"
Cohesion: 0.08
Nodes (40): _failure(), datetime, UnitOfWorkFactory, Keep the graph projection in step with durable knowledge.  One queue, one dire, Rebuild one project's projection from durable knowledge.      The recovery pat, Committed per entry, not per batch: an interrupted pass must keep the progress, Drain the backlog once. Safe to call repeatedly and safe to interrupt., rebuild_project() (+32 more)

### Community 187 - "commands/run.ts"
Cohesion: 0.10
Nodes (24): cancelRun(), createRun(), CreateRunInput, getProject(), getRun(), listProjects(), parseProject(), parseRunState() (+16 more)

### Community 188 - "derive_verdict"
Cohesion: 0.14
Nodes (14): derive_verdict(), Verdict, Turn criterion results into the run's QA verdict.      Ordering matters and is d, met(), not_met(), FailureKind, Verdict derivation: what a run is allowed to conclude, and from what.  The rule, Ordering matters: the finding worth having wins over the noise around it. (+6 more)

### Community 190 - "routers/schedules.py"
Cohesion: 0.16
Nodes (19): Protocol, Register a recurring run. Raises `AlreadyExistsError` on a taken id.          Th, Pause or resume. False when there is no such schedule.          Pausing rather t, ScheduleGateway, create_schedule(), delete_schedule(), list_schedules(), _owned() (+11 more)

### Community 191 - "InMemoryGraphMemory"
Cohesion: 0.21
Nodes (7): GraphHit, GraphUnavailableError, Exception, The projection could not be reached or written.      Typed so callers can tell i, Drop every environment's projection for one project., A store that is never reachable. Used where the point is that nothing else     b, UnavailableGraph

### Community 193 - "seed_project_with_default_policy"
Cohesion: 0.24
Nodes (12): exploration_outcome(), Load one run's map and diff it against the previous exploration.      Raises `No, page(), Factory, Storing a map and comparing it against the last one.  Parametrized over the in, Three explorations: the second compares against the first, the third against the, report(), seed_run() (+4 more)

### Community 194 - "PageState"
Cohesion: 0.11
Nodes (8): Frontier, FrontierEntry, One thing left to try, and where from., Visited states and what is left to try, with depth.      Deliberately a plain, Rebuild a frontier mid-exploration. `None` starts a fresh one.          `offer, Register a state. True when it had never been seen before.          Its afford, Hand out the next thing to try, permanently removing it from the frontier., TestResumingAnExploration

### Community 195 - "signal_from"
Cohesion: 0.19
Nodes (5): ExplorationBudget, What one exploration may spend.      Never wider than the RunPolicy that gover, Clamp to the policy. A policy with no depth limit still gets one here:, TestTheBudgetCannotExceedThePolicy, TestTheFrontierIsReproducible

### Community 201 - "CriterionOutcome"
Cohesion: 0.18
Nodes (9): The one place graphiti-core is imported.  graphiti-core 0.29 still defines a p, _attributes(), group_id_for(), node_uuid_for(), Any, The FalkorDB projection of durable knowledge (ADR 0008).  Graphiti supplies the, What travels into the graph, and nothing else.      The payload is deliberately, Graphiti's tenancy key: one opaque alphanumeric token.      Graphiti restricts t (+1 more)

### Community 204 - "test_memory_api.py"
Cohesion: 0.16
Nodes (10): app_client(), broken_graph(), no_graph(), AsyncClient, The memory administration endpoints over real HTTP.  What matters here is the, TestRebuild, TestStatus, TestSync (+2 more)

### Community 205 - "DeepAnalysisService"
Cohesion: 0.09
Nodes (21): AnalyzedCluster, ClusterAnalysisRequest, DeepAnalyst, Protocol, Deterministic evidence and model interpretation, side by side and never merged., One cluster, reduced to what is worth a large model's time.      Built from th, DeepAnalysisService, Asking a large model about what triage could not explain.  The order is the po (+13 more)

### Community 210 - "apply_feedback"
Cohesion: 0.21
Nodes (13): apply_feedback(), FeedbackKind, datetime, StrEnum, Fold one verified outcome into a candidate and re-derive its status.      Pure, candidate(), feedback(), What later runs do to knowledge they used.  Consolidation is only half a learn (+5 more)

### Community 213 - "test_temporal_workflow.py"
Cohesion: 0.27
Nodes (18): Client, RunStatus, UnitOfWorkFactory, Worker, queue_run(), Durable run lifecycle against a real Temporal server and a real database.  The, The core durability gate: a worker is replaceable mid-run.      The run is pau, A retried start after a lost acknowledgement finds the same workflow. (+10 more)

### Community 214 - "errors.ts"
Cohesion: 0.17
Nodes (11): A7 — a refusal that carries the correction, A8 — a control that already has something in it, A defect in the harness, not the agent, A sighting reads the same source the check reads, Each element names the action that takes it, For a reviewer, Gates, R5 first, because it is why the rest could be found (+3 more)

### Community 215 - "schemas.ts"
Cohesion: 0.12
Nodes (18): artifactSchema, compiledPlanSchema, ContractError, failureContextSchema, findingSchema, memoryStatusSchema, parse(), projectSchema (+10 more)

### Community 217 - "test_graphiti_projection.py"
Cohesion: 0.22
Nodes (15): execute(), falkordb_test_url(), projection(), Any, The projection against a real FalkorDB.  The in-memory double proves the sync, A projection over a disposable graph, torn down whatever the test did., test_a_candidate_is_written_and_found_again(), test_a_forgotten_candidate_stops_being_found() (+7 more)

### Community 218 - "ClusterHypothesis"
Cohesion: 0.16
Nodes (14): _heartbeating(), Group this project's recent failures and, if a deep model is configured, ask, Keep an activity visibly alive across a call that takes minutes.      Temporal c, AnalyzeFailuresParams, activities(), CountingAnalyst, The deep-analysis activity at the Temporal boundary.  Three things a workflow, The verdict is already durable. A second reading of results that are already (+6 more)

### Community 221 - "run_story"
Cohesion: 0.29
Nodes (8): execute(), Execute the story once against a live target app., Run it twice: a QA verdict that only holds sometimes is not a verdict., A criterion with nothing deterministic to check is a plan problem, not a defect., run_story(), test_a_known_story_passes_reproducibly(), test_an_unverifiable_criterion_ends_inconclusive_instead_of_blaming_the_product(), RunReport

### Community 223 - "StateMap"
Cohesion: 0.15
Nodes (8): ChangedState, compare(), MapDelta, The same route, offering something different., Diff two maps by structure, never by content., page(), TestComparingAgainstABaseline, TestTheSameStateIsRecognisedAgain

### Community 224 - "compilerOptions"
Cohesion: 0.10
Nodes (20): compilerOptions, declaration, exactOptionalPropertyTypes, lib, module, moduleResolution, noImplicitOverride, noUncheckedIndexedAccess (+12 more)

### Community 225 - "test_operational_queries.py"
Cohesion: 0.20
Nodes (16): OperationalQuery, query_named(), Operational questions, answered from durable rows.  Why SQL and not a metrics, factory(), Every operational query, executed against the real schema.  The reason these l, An aggregate over no rows must still return a row.      "No clusters" and "the, Telemetry must not carry what a page said.      An observation or a summary ca, Run one query the way an operator would: a connection, the SQL, the rows. (+8 more)

### Community 226 - "api.ts"
Cohesion: 0.19
Nodes (13): ApiClient, ApiClientOptions, ApiResponse, backoffMs(), extractDetail(), isRetryableStatus(), readBody(), RequestOptions (+5 more)

### Community 227 - "agent.ts"
Cohesion: 0.16
Nodes (17): installClaudeSkill(), InstallInput, InstallResult, readIfPresent(), requireSupportedAgent(), SKILL_PATH, skillDocument(), SUPPORTED_AGENTS (+9 more)

### Community 228 - "diff.ts"
Cohesion: 0.16
Nodes (16): classify(), CriterionChange, CriterionDelta, CriterionSide, delta(), describePlan(), diffRuns(), loadRunSummary() (+8 more)

### Community 229 - "parse_affordances"
Cohesion: 0.05
Nodes (19): _absolute(), parse_affordances(), parse_text_content(), Pull role/name pairs out of an ARIA snapshot, deduplicated and bounded.      A l, Pull what the page *says* out of the same snapshot, deduplicated and bounded., Resolve an href against the page, or decline.      `None` for anything that is n, Strip the quotes Playwright adds around a value that needs them.      The snapsh, unquote_snapshot_value() (+11 more)

### Community 230 - "VLLMModelGateway"
Cohesion: 0.14
Nodes (8): AirLLMDeepAnalyst, AsyncClient, One client for the endpoint, so its circuit breaker remembers across calls., Implements `DeepAnalyst` (application port) over the DEEP-capability endpoint., EndpointStats, InferenceMetrics, Counted apart from failures: the endpoint answered, the answer was unusable., AsyncClient

### Community 231 - "test_deep_analyst.py"
Cohesion: 0.20
Nodes (17): build_analyst(), completion(), Request, Response, The deep-analysis adapter, against a server that can be made to misbehave.  Wh, A cause nobody can re-derive is not comparable to the next one (docs/08)., A 10-minute call under a 2-minute lease frees the slot while it is still running, test_a_call_that_costs_minutes_is_not_retried_blindly() (+9 more)

### Community 232 - "commands/memory.ts"
Cohesion: 0.25
Nodes (15): memoryRebuild, memoryStatus, memorySync(), memoryValidate(), MemoryValidation, num(), parseRebuild(), parseStatus() (+7 more)

### Community 233 - "Patterns adopted"
Cohesion: 0.11
Nodes (18): 10. Agent installation, 1. Agent-first CLI, 2. Machine-pure output, 3. Versioned TestPlan files, 4. Atomic FailureBundle, 5. Idempotency and retry ownership, 6. Wait does not mean cancel, 7. Runtime response validation (+10 more)

### Community 234 - "client.ts"
Cohesion: 0.18
Nodes (6): ApiClient, ApiClientOptions, ApiError, HttpMemoryGateway, toApiError(), toMemoryStatus()

### Community 235 - "MemoryMetrics"
Cohesion: 0.15
Nodes (9): MemoryMetrics, What memory is doing, and whether it is worth its cost.  Same shape as the infer, What the counters have to be able to tell an operator.  A run's verdict looks, Summaries and payloads never reach the log line.      They derive from page co, test_a_projection_that_never_catches_up_is_countable(), test_hypotheses_are_counted_separately_from_facts(), test_nothing_derived_from_page_content_is_recorded(), test_what_was_learned_and_what_was_withdrawn_are_both_visible() (+1 more)

### Community 236 - "InMemoryStore"
Cohesion: 0.08
Nodes (15): store(), uow(), InMemoryStore, store(), client(), failure(), AsyncClient, FailureKind (+7 more)

### Community 237 - "record_finished_run"
Cohesion: 0.17
Nodes (11): MODEL_MAX_CONCURRENCY, model-env.example.sh script, VLLM_BASE_URL, VLLM_ENFORCE_EAGER, VLLM_EXTRA_ARGS, VLLM_GPU_MEMORY_UTILIZATION, VLLM_MAX_MODEL_LEN, VLLM_MAX_NUM_SEQS (+3 more)

### Community 238 - "API and Event Contracts"
Cohesion: 0.11
Nodes (17): API and Event Contracts, Artifacts, CLI envelope, Event envelope, Exploration (Phase 12), Failure triage (Phase 11), Important event types, Memory admin (Phase 09) (+9 more)

### Community 239 - "ports/gateways.ts"
Cohesion: 0.10
Nodes (9): CompiledPlan, DraftStory, MemoryGateway, NewProjectInput, ProjectGateway, RunEventStream, RunSubscription, StartRunInput (+1 more)

### Community 240 - "test_database_failure.py"
Cohesion: 0.18
Nodes (16): postgres_unit_of_work_scope(), Units of work that really commit, with a truncating teardown., factory(), FlakyDatabase, Factory, queued_run(), A transient PostgreSQL failure, against a real PostgreSQL.  The gap the recove, They share a transaction on purpose.      A run that moved without leaving its (+8 more)

### Community 241 - "bundle.test.ts"
Cohesion: 0.08
Nodes (28): ArtifactFetcher, assertBytesMatch(), assertCoherent(), BundleArtifact, BundleManifest, describe(), materialize(), MaterializeResult (+20 more)

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
Cohesion: 0.16
Nodes (17): MemoryContextRequest, datetime, retrieve_memory_context(), Run, What earlier runs learned about this application, or nothing.          Failure i, benchmark(), execute_run(), datetime (+9 more)

### Community 246 - "envelope.test.ts"
Cohesion: 0.17
Nodes (10): Recorded, envelopeSchema, packageRoot, VALID_PLAN, validateEnvelope, CLI_ENTRY, CliResult, packageRoot (+2 more)

### Community 247 - "test_memory_benchmark_real_model.py"
Cohesion: 0.40
Nodes (10): UnitOfWorkFactory, Run event log contract.  Both implementations must number, order and page identi, Events obey the same transaction as the change they describe., seed_run(), test_an_uncommitted_event_is_not_visible(), test_catch_up_returns_only_events_after_the_cursor(), test_payload_and_request_id_survive_the_round_trip(), test_reads_are_bounded_by_limit() (+2 more)

### Community 248 - "policy"
Cohesion: 0.19
Nodes (6): policy(), Origin allowlist semantics.  Ambiguous matching is how allowlists get bypassed,, No implicit subdomains: evil.app.example.com is a different origin., There is no safe empty allowlist, so there is no default., TestAllowsOrigin, TestPolicyInvariants

### Community 249 - "Combination rules"
Cohesion: 0.13
Nodes (14): Adaptive memory graph, Always-on disciplines, Brainstorming is conditional, Claude Code Skill Routing, CLI/API contracts, Combination rules, Frontend design split, Graphify and the runtime graph (+6 more)

### Community 250 - "FailureKind"
Cohesion: 0.42
Nodes (4): is_takeable(), Whether this run may take this affordance at all.      Asked *before* the affo, Counted, not attempted, and reported either way.      "Mapped 12 states, left, TestWhatItDeclinedToTake

### Community 251 - "container.py"
Cohesion: 0.21
Nodes (11): build_deep_analyst(), build_episode_runner(), build_model_router(), AsyncClient, Redis, None when no endpoint is configured at all — an honest absence, not a fake model, None when nothing serves DEEP. Callers treat that as "no hypothesis", never as, Add the agent runtime. Worker-only: the API never plans or drives a browser. (+3 more)

### Community 252 - "PostgresKnowledgeRepository"
Cohesion: 0.20
Nodes (9): 1. What this is trying to be, 2. The four exit gates, 3. Where to start, concretely, 4. Bring it up on a new machine, 5. Lessons that cost real time, 6. Branch and PR state, 7. Blocked on tooling, not on decisions, 8. Reading order for a new session (+1 more)

### Community 253 - "Guía de uso"
Cohesion: 0.13
Nodes (15): 10. Explorar sin historia, 1. Levantarlo, 2. Tu primer proyecto, 3. Escribir una historia, 4. Lanzar un run y leerlo, 5. Qué significa cada veredicto, 6. La CLI, 7. En CI (+7 more)

### Community 254 - "finished_run"
Cohesion: 0.42
Nodes (6): consolidate(), finished_run(), datetime, Factory, A completed run that checked one criterion deterministically., scope()

### Community 255 - "Bounded contexts"
Cohesion: 0.14
Nodes (13): Action safety fields, Agent, Bounded contexts, Browser, Core statuses, Domain Model, Important invariants, Inference (+5 more)

### Community 256 - "runs/run.ts"
Cohesion: 0.18
Nodes (11): canCancel(), CANCELLABLE, isActive(), isTerminal(), Run, RUN_STATUSES, RunStatus, TERMINAL (+3 more)

### Community 257 - "test_evidence_chain.py"
Cohesion: 0.22
Nodes (5): ArtifactIndex, Protocol, Durable index of captured artifacts (docs/11: references in the database)., Index one artifact. Idempotent by artifact id., Resolve an id to its reference. Downloads go through this, so an id is

### Community 258 - "test_triage_from_a_real_run.py"
Cohesion: 0.27
Nodes (12): execute(), Any, Path, Triage over a real failing run, end to end.  Everything else in this package pro, Stands in for a deep endpoint that is down — the state this system spends most, A member is a pointer, not a copy — so the observation and the evidence refs a, RefusingAnalyst, run_and_triage() (+4 more)

### Community 259 - "Agent-First CLI Design"
Cohesion: 0.15
Nodes (12): Agent-First CLI Design, Agent verification skill, Boundary, Configuration, Failure bundle disk layout, Output contract, Purpose, Request behavior (+4 more)

### Community 260 - "Operations Runbook"
Cohesion: 0.17
Nodes (12): Backup, Consultas operacionales, Drill ejecutado (2026-08-20), Instalar el skill de verificación en un repo ajeno, Instalar la CLI como cliente externo, Levantar el stack en una máquina nueva, Memoria adaptativa, Operations Runbook (+4 more)

### Community 261 - "start-run.ts"
Cohesion: 0.15
Nodes (4): RunGateway, prepareRun(), StartRunAttempt, StartRunRequest

### Community 262 - "safe_url"
Cohesion: 0.43
Nodes (7): jfield(), plan_for(), policy(), say(), agent-baseline.sh script, story(), write_after_a_form()

### Community 263 - "test_exploring_a_real_run.py"
Cohesion: 0.38
Nodes (4): ExplorationProgress, Everything the stop decision is allowed to look at., Why exploration should stop now, or None to continue.      Ordered by what a r, stop_reason()

### Community 264 - "test_learning_from_a_real_run.py"
Cohesion: 0.36
Nodes (11): execute(), Any, Path, What a real run actually learns.  Everything else about consolidation is tested, Page text is untrusted data. Whatever is stored must be safe to replay., run_and_learn(), test_a_finished_run_leaves_durable_knowledge(), test_a_first_run_teaches_nothing_the_agent_may_act_on() (+3 more)

### Community 265 - "envelope.ts"
Cohesion: 0.36
Nodes (7): checkContracts(), describeHealth(), doctor(), DoctorReport, problemError(), Config, doctorCommand()

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

### Community 276 - "fakes.ts"
Cohesion: 0.17
Nodes (7): FakeStoryGateway, makeEvent(), makeRun(), NotFound, gatewaysWith(), renderRun(), withReport()

### Community 277 - "UserStory"
Cohesion: 0.33
Nodes (6): Dos hallazgos que no eran de esta fase, Fase 15 cerrada, Lo que cambió, Lo siguiente, con número detrás, Session Handoff, Siguiente

### Community 278 - "StoredCluster"
Cohesion: 0.33
Nodes (5): Decisión estructural, Gates, Objective, Phase 17 — Authenticated Runs, Tasks

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

### Community 285 - "JudgementRequest"
Cohesion: 0.40
Nodes (5): StrEnum, VARCHAR-backed enum: adding a value stays a normal, reviewable migration., _string_enum(), _value_check(), CheckConstraint

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
Cohesion: 0.17
Nodes (11): Bootstrap, Development-Time Codebase Graph (Graphify), Dónde está el peso, El grafo de hoy (2026-08-20, commit `916faed`), Failure behavior, La dirección de dependencias, medida, Purpose, Query-before-scan rule (+3 more)

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

### Community 295 - "test_migrations_from_empty.py"
Cohesion: 0.40
Nodes (4): Consequences, Context, Decision, Navigation and element waits are different scales

### Community 296 - "API design principles"
Cohesion: 0.25
Nodes (7): API design principles, CLI contracts, Collections and payload bounds, Commands and long-running runs, Errors, Evolution, Resource model

### Community 297 - "Error handling patterns"
Cohesion: 0.25
Nodes (7): Classify first, Error handling patterns, Layering, Observability and UX, Retry discipline, Tests, Wait and cancellation

### Community 298 - "plan_of"
Cohesion: 0.40
Nodes (4): Consequences, Context, Decision, The decision schema is a union generated from the domain's own sets

### Community 299 - "Agent Runtime"
Cohesion: 0.25
Nodes (7): Agent Runtime, Episodes, Exploration mode (Phase 12), LangGraph state machine, Logical roles, Outcomes de un step, Verification priority

### Community 300 - "Docker Compose Topology"
Cohesion: 0.25
Nodes (7): CLI, Docker Compose Topology, Frontend (Phase 10), Healthchecks, Profiles, Services target, Storage

### Community 301 - "ADR 0009 — Run workflow shape, retry ownership and checkpoint reconciliation"
Cohesion: 0.25
Nodes (7): ADR 0009 — Run workflow shape, retry ownership and checkpoint reconciliation, Checkpoint reconciliation, Consequences, Context, Decision, Retry ownership (single owner per loop), Workflow shape

### Community 302 - "stories-page.test.tsx"
Cohesion: 0.40
Nodes (4): A deterministic criterion is checked as the run goes, Consequences, Context, Decision

### Community 303 - "findings.ts"
Cohesion: 0.25
Nodes (5): Artifact, CriterionOutcome, FailureKind, Finding, RunReport

### Community 304 - "v1.0.0-rc — 2026-08-20"
Cohesion: 0.17
Nodes (11): Cambios que se notan, Changelog, Contratos, Contratos públicos, Corregido — un diagnóstico, no sólo un defecto, Límites conocidos de este candidato, Para empezar, Pipelines (+3 more)

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

### Community 314 - "parse"
Cohesion: 0.40
Nodes (4): Consequences, Context, Decision, The action type decides what a read-only policy forbids

### Community 315 - "use-projects-viewmodel.ts"
Cohesion: 0.33
Nodes (8): CreateProjectViewModel, isNotFound(), messageFor(), ProjectsViewModel, ProjectViewModel, useCreateProject(), useProjectsViewModel(), useProjectViewModel()

### Community 316 - "use-run-viewmodel.ts"
Cohesion: 0.33
Nodes (6): CommandName, messageFor(), RunViewModel, TaggedError, TaggedSnapshot, useRunViewModel()

### Community 317 - ".analyze"
Cohesion: 0.40
Nodes (4): Consequences, Context, Decision, What the gateway learns from an HTTP response

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

### Community 327 - "README.md"
Cohesion: 0.12
Nodes (12): Consequences, Context, Decision, The frontend adopts Windmill Dashboard, and Tailwind with it, El estado que carga un checkpoint, Lo que sigue sin medirse, Los pasos dentro de un episodio, Performance Profile (+4 more)

### Community 328 - "Recovery Matrix"
Cohesion: 0.33
Nodes (5): Contratos y clientes, Hostilidad, Huecos conocidos, Infraestructura, Recovery Matrix

### Community 329 - "frontend/package.json"
Cohesion: 0.33
Nodes (5): name, packageManager, private, type, version

### Community 330 - "timeline.ts"
Cohesion: 0.33
Nodes (3): EMPTY_TIMELINE, RunEvent, Timeline

### Community 331 - "FakeStoryGateway"
Cohesion: 0.40
Nodes (4): Per-thread replies, Replies to the CodeRabbit review — PR #1, Review log, Top-level comment

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

### Community 342 - "toProject"
Cohesion: 0.19
Nodes (6): HttpProjectGateway, HttpStoryGateway, toProject(), toProjects(), toStories(), toStory()

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

### Community 364 - "RoveQA"
Cohesion: 0.25
Nodes (8): Construido con Claude Code, Cómo está construido, Documentación, En cinco minutos, Qué hace, Qué no hace todavía, RoveQA, Tres maneras de usarlo

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
Cohesion: 0.09
Nodes (11): badgeFor(), FindingsList(), OUTCOME_LABEL, toneFor(), Badge(), BADGE_TONES, BadgeTone, BUTTON_VARIANTS (+3 more)

### Community 375 - "memory-page.test.tsx"
Cohesion: 0.67
Nodes (3): _cancel_library_index_setup(), Stop Graphiti's own index build before it can run.      `FalkorDriver.__init__`, FalkorDriver

### Community 376 - "projects-page.test.tsx"
Cohesion: 0.11
Nodes (7): App(), defaultQueryClient(), FakeMemoryGateway, FakeProjectGateway, FakeRunEventStream, makeMemoryStatus(), PROJECT

### Community 377 - "routers/artifacts.py"
Cohesion: 0.50
Nodes (4): maxLength, minLength, type, description

### Community 392 - "verdict-badge.tsx"
Cohesion: 0.50
Nodes (4): maxLength, minLength, type, name

### Community 415 - "eslint-plugin-react-hooks"
Cohesion: 0.50
Nodes (4): source_story_id, maxLength, minLength, type

### Community 456 - ".oxlintrc.json"
Cohesion: 0.22
Nodes (8): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema, oxc, typescript, warn

### Community 461 - "TestTheSystemPromptSaysHowFarToTrustMemory"
Cohesion: 0.11
Nodes (34): ConsolidationOutcome, Compatibility, MemoryScope, StrEnum, The situation the current run is in.      `None` means "not known in this run", CandidateKind, Provenance, StrEnum (+26 more)

### Community 465 - "valid_from"
Cohesion: 0.67
Nodes (3): valid_from, format, type

## Knowledge Gaps
- **1438 isolated node(s):** `$schema`, `Read(./.env)`, `Read(./.env.local)`, `Read(./.env.development)`, `Read(./.env.production)` (+1433 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **61 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RunPolicy` connect `http/schemas.py` to `RunPolicy`, `application/errors.py`, `Container`, `test_exploring_a_real_run.py`, `InvalidEntityError`, `UnitOfWork`, `RunActivities`, `postgres/repositories.py`, `postgres_test_dsn`, `langgraph/graph.py`, `ScriptedModelGateway`, `BrowserSession`, `InMemoryProjectRepository`, `InMemoryUnitOfWork`, `RunEvent`, `Run`, `redis/streams.py`, `sync_pending`, `test_budget_and_classification.py`, `projects.py`, `consolidate_experience`, `test_gateway.py`, `routers/schedules.py`, `PageState`, `signal_from`, `RecordingWorkflowGateway`, `TestTheSystemPromptSaysHowFarToTrustMemory`, `StateMap`, `fakes/unit_of_work.py`, `InMemoryStore`, `MemoryContextRequest`, `policy`, `FailureKind`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Why does `Container` connect `Container` to `FilesystemArtifactRepository`, `AsyncClient`, `http/schemas.py`, `UnitOfWork`, `RunActivities`, `postgres_test_dsn`, `langgraph/graph.py`, `test_realtime.py`, `ScriptedModelGateway`, `routers/memory.py`, `RunEvent`, `routers/schedules.py`, `RecordingWorkflowGateway`, `test_memory_api.py`, `DeepAnalysisService`, `ModelCapability`, `test_temporal_workflow.py`, `ClusterHypothesis`, `MemoryMetrics`, `InMemoryStore`, `test_schedules_api.py`, `test_database_failure.py`, `container.py`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Why does `CriterionResult` connect `RunActivities` to `RunPolicy`, `clustering.py`, `InvalidEntityError`, `http/schemas.py`, `UnitOfWork`, `postgres/repositories.py`, `langgraph/graph.py`, `ScriptedModelGateway`, `triage`, `NotFoundError`, `consolidate_experience`, `derive_verdict`, `KnowledgeExperienceCandidate`, `TestTheSystemPromptSaysHowFarToTrustMemory`, `DeepAnalysisService`, `CandidateKind`, `ClusterHypothesis`, `fakes/unit_of_work.py`, `test_operational_queries.py`, `analyze_failures.py`, `InMemoryStore`, `finished_run`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Are the 126 inferred relationships involving `RunPolicy` (e.g. with `CreateRunPolicyCommand` and `ActionRecord`) actually correct?**
  _`RunPolicy` has 126 INFERRED edges - model-reasoned connections that need verification._
- **Are the 98 inferred relationships involving `KnowledgeExperienceCandidate` (e.g. with `ConsolidateExperienceCommand` and `ConsolidateExperienceResult`) actually correct?**
  _`KnowledgeExperienceCandidate` has 98 INFERRED edges - model-reasoned connections that need verification._
- **Are the 114 inferred relationships involving `Run` (e.g. with `StartRunCommand` and `StartRunResult`) actually correct?**
  _`Run` has 114 INFERRED edges - model-reasoned connections that need verification._
- **Are the 94 inferred relationships involving `CriterionResult` (e.g. with `ConsolidateExperienceCommand` and `ConsolidateExperienceResult`) actually correct?**
  _`CriterionResult` has 94 INFERRED edges - model-reasoned connections that need verification._