# Graph Report - RoveQA  (2026-08-20)

## Corpus Check
- 534 files · ~234,085 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 6291 nodes · 13819 edges · 466 communities (406 shown, 60 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 1626 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d15398f8`
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
- eslint
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

## God Nodes (most connected - your core abstractions)
1. `seed_project_with_default_policy()` - 99 edges
2. `BrowserAction` - 92 edges
3. `UnitOfWork` - 88 edges
4. `KnowledgeExperienceCandidate` - 87 edges
5. `InMemoryStore` - 84 edges
6. `NotFoundError` - 79 edges
7. `unit_of_work_factory()` - 78 edges
8. `InMemoryUnitOfWork` - 75 edges
9. `RunPolicy` - 71 edges
10. `CriterionResult` - 69 edges

## Surprising Connections (you probably didn't know these)
- `test_provenance_without_a_run_is_refused()` --uses--> `Provenance`  [INFERRED]
  backend/tests/knowledge/test_experience.py → backend/src/agentic_qa/domain/knowledge/experience.py
- `prompt_for()` --uses--> `PlanningRequest`  [INFERRED]
  backend/scripts/measure_growth.py → backend/src/agentic_qa/application/ports/models.py
- `RunActivities` --uses--> `AnalyzeFailuresCommand`  [INFERRED]
  backend/src/agentic_qa/infrastructure/workflows/temporal/activities.py → backend/src/agentic_qa/application/commands/analyze_failures.py
- `record()` --uses--> `AnalyzeFailuresCommand`  [INFERRED]
  backend/tests/http/test_triage_api.py → backend/src/agentic_qa/application/commands/analyze_failures.py
- `AnalyzeFailuresResult` --uses--> `StoredCluster`  [INFERRED]
  backend/src/agentic_qa/application/commands/analyze_failures.py → backend/src/agentic_qa/application/ports/triage.py

## Import Cycles
- None detected.

## Communities (466 total, 60 thin omitted)

### Community 0 - "RunPolicy"
Cohesion: 0.05
Nodes (40): BrowserGateway, Protocol, Browser gateway port. Application asks for typed actions and never touches…, Capture the page as it is now. A capability rather than an action outcome: the…, ActionDeniedError, GuardedBrowserGateway, Exception, A browser gateway that cannot execute what the policy forbids. Enforcement… (+32 more)

### Community 1 - "FilesystemArtifactRepository"
Cohesion: 0.06
Nodes (31): ArtifactTooLargeError, Exception, The artifact exceeded the configured cap and was not stored., EvidenceSet, Artifacts captured under one run and one coherent context., PageFingerprint, PageFingerprint v1 (docs/07). A stable identity for "the same kind of page",…, Collapse identifier-looking path segments so /records/42 and /records/43 agree. (+23 more)

### Community 2 - "application/errors.py"
Cohesion: 0.08
Nodes (37): compile_plan(), CompilePlanCommand, _next_version(), Compile a user story into a stored, versioned TestPlan. Versioning is the point…, Monotonic integers as strings. The contract allows any string; sequential…, content_version(), import_plan(), ImportPlanCommand (+29 more)

### Community 3 - "properties"
Cohesion: 0.04
Nodes (48): additionalProperties, default, type, default, type, items, type, default (+40 more)

### Community 4 - "devDependencies"
Cohesion: 0.11
Nodes (19): eslint-plugin-react-refresh, devDependencies, @eslint/js, eslint-plugin-react-refresh, globals, @testing-library/jest-dom, @types/node, @types/react (+11 more)

### Community 5 - "InMemoryResourceSemaphore"
Cohesion: 0.12
Nodes (14): SlotReservation, _millis(), Redis, Redis resource semaphore. One sorted set per resource: members are reservation…, RedisResourceSemaphore, InMemoryResourceSemaphore, In-memory resource semaphore with real lease expiry., analyst() (+6 more)

### Community 6 - "LockHandle"
Cohesion: 0.06
Nodes (37): LockHandle, LockManager, Protocol, Distributed lock port. Locks are coordination, never truth (docs/09, ADR 0003):…, Return a handle, or None when the lock is already held., Extend the lease. False when the token no longer owns the key., Release only if still the owner. False when the token no longer owns it., _millis() (+29 more)

### Community 7 - "memory-context.schema.json"
Cohesion: 0.17
Nodes (11): additionalProperties, $id, environment_id, project_id, schema_version, required, $schema, title (+3 more)

### Community 8 - "AsyncClient"
Cohesion: 0.07
Nodes (33): asgi_client(), captured_error_logs(), client(), create_project(), ExplodingUnitOfWork, AsyncClient, fixture, LogRecord (+25 more)

### Community 9 - "InvalidEntityError"
Cohesion: 0.05
Nodes (54): Consolidate a finished run into durable knowledge. Runs once per run, enforced…, _enum(), EnumT, Repositories for environments and run policies., Recurring runs. A schedule is durable state, and it has exactly one owner:…, Retrieve the memory a run should start from. The pipeline docs/26 asks for, in…, EvidenceContaminationError, Evidence identity and provenance (docs/11). An `EvidenceSet` is a coherent… (+46 more)

### Community 10 - "http/schemas.py"
Cohesion: 0.07
Nodes (45): ExplorationOutcome, What one exploration found, and what changed since the last one. The comparison…, MapDelta, ContainerDep, get, What an exploring run mapped, and what changed since the last one. Read-only,…, 404 when the run did not explore: a planned run has no map, and answering with…, read_exploration() (+37 more)

### Community 11 - "properties"
Cohesion: 0.06
Nodes (36): items, type, type, type, items, type, type, $id (+28 more)

### Community 12 - "properties"
Cohesion: 0.06
Nodes (30): items, type, type, $id, type, payload, run_id, type (+22 more)

### Community 13 - "ports/unit_of_work.py"
Cohesion: 0.04
Nodes (48): Create a project. Commands own their transaction and commit; queries take…, datetime, Record what a run discovered about the knowledge it used. The write and the…, Record one outcome and re-derive the candidate, inside an already-open…, register_feedback(), Start a run, idempotently. Ordering is the durability contract (ADR 0010): the…, StartRunResult, enqueue_for_sync() (+40 more)

### Community 14 - "UnitOfWork"
Cohesion: 0.06
Nodes (17): Protocol, Events with sequence > after, ascending, capped at limit. `after` is the cursor…, RunEventLog, IdempotencyRepository, Protocol, Persist a record. Raises AlreadyExistsError when (scope, key) is taken. A…, EnvironmentRepository, Protocol (+9 more)

### Community 15 - "RunActivities"
Cohesion: 0.09
Nodes (27): BrowserRecoveryData, What it takes to rebuild the browser here. Chromium itself is never serialized., _heartbeating(), defn, Execute one episode of the agent loop. The activity stays thin: it resolves the…, Store what an exploration mapped, or nothing for a planned episode. Not…, Turn a finished run into durable knowledge. Returns how many candidates hold.…, Create the run a schedule firing asks for, and return its id. Deliberately the… (+19 more)

### Community 16 - "PlanningRequest"
Cohesion: 0.07
Nodes (35): PlannedAction, PlanningRequest, Bounded context handed to the planner. It carries the working window and the…, The planner's decision. Three outcomes, deliberately distinguishable: -…, build_cluster_analysis_prompt(), build_judgement_prompt(), build_planning_prompt(), _clip() (+27 more)

### Community 17 - "test_policy_resolution.py"
Cohesion: 0.15
Nodes (24): ApplicationError, IdempotencyConflictError, Exception, An idempotency key was reused for a different logical request. Failing typed is…, Base for failures the Application layer defines for its ports/use cases., _candidates(), PolicyNotResolvedError, Resolve the RunPolicy that governs a run. Normative order (docs/12, docs/13):… (+16 more)

### Community 18 - "RecoveryPoint"
Cohesion: 0.12
Nodes (11): Protocol, Recovery point repository port., The newest safe point, which is where a resume validates against., Newest first, bounded — a long run must not be read unboundedly., RecoveryPointRepository, RecoveryPoint, The domain's safe points (ADR 0009). Named `recovery_points`, not…, RecoveryPointModel (+3 more)

### Community 19 - "RecordingBrowserGateway"
Cohesion: 0.07
Nodes (41): ActionOutcome, What actually happened, kept separate from what was intended., AlwaysFailingBrowser, click(), navigate(), Any, Agent graph behaviour over deterministic doubles. The graph depends on the…, The summary of an unrecoverable episode says it failed, and says why. (+33 more)

### Community 20 - "postgres/repositories.py"
Cohesion: 0.03
Nodes (85): AlreadyExistsError, A repository rejected an insert because the identity is already taken. Adapters…, HypothesisConfidence, StrEnum, IdempotencyRecord, ClusterMember, A pointer into `criterion_results`, not a copy of it. The observation, the…, Environment (+77 more)

### Community 21 - "postgres_test_dsn"
Cohesion: 0.22
Nodes (13): counting_graph(), CountingState, Any, TypedDict, LangGraph's PostgreSQL checkpointer against the real database. The resume path…, The domain stores this id on a RecoveryPoint, so it must be retrievable., The durability claim a worker restart depends on. State is written with one…, Runs are isolated by thread id: one run never resumes into another. (+5 more)

### Community 22 - "langgraph/graph.py"
Cohesion: 0.04
Nodes (71): main(), prompt_for(), Measure what grows, and print it. Run inside the gates container: docker…, run_for(), table_sizes(), test_dsn(), ArtifactIndex, ArtifactRepository (+63 more)

### Community 23 - "test_realtime.py"
Cohesion: 0.10
Nodes (27): create_app(), FastAPI, Build the API. Passing a container lets tests wire their own adapters., BrokenRunEventPublisher, InMemoryRunEventPublisher, InMemoryRunEventSubscription, RunEvent, In-memory run event publisher with the same delivery semantics as Redis. (+19 more)

### Community 24 - "ScriptedModelGateway"
Cohesion: 0.18
Nodes (20): Returns the scripted actions in order, then reports the goal is reached., ScriptedModelGateway, assertion(), PageDouble, PlanStep, The verification pipeline: deterministic first, model last, and the line…, It is recorded as unmet with an unknown cause, which keeps the run inconclusive., Judging the page anyway would report whatever was on screen as the outcome. (+12 more)

### Community 25 - "null"
Cohesion: 0.13
Nodes (24): type, type, null, string, format, type, description, type (+16 more)

### Community 26 - "compilerOptions"
Cohesion: 0.05
Nodes (38): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, exactOptionalPropertyTypes, jsx, lib, module (+30 more)

### Community 27 - "BrowserSession"
Cohesion: 0.03
Nodes (97): AriaRole, Exception, The gateway cannot carry out this action as described. A fact about the…, UnperformableActionError, perform_once(), Verify before retry. The mandatory case from docs/05: the target processed…, Perform an effect at most once, deciding by observation rather than by memory., SideEffectOutcome (+89 more)

### Community 28 - "triage"
Cohesion: 0.18
Nodes (7): Group failures and mark the ones that were only consequences. Deterministic and…, triage(), signal(), TestCascadeIsNotTwelveBugs, TestDuplicatesBecomeOneProblem, TestTriageIsReproducible, TestWhatIsWorthAModel

### Community 29 - "InMemoryProjectRepository"
Cohesion: 0.14
Nodes (7): in_memory_repositories(), InMemoryProjectRepository, InMemoryRunRepository, InMemoryStoryRepository, Project, Run, UserStory

### Community 30 - "PostgresUnitOfWork"
Cohesion: 0.09
Nodes (11): graph_sync_to_domain(), GraphSyncStateModel, Whether a durable candidate has reached the graph projection. Separate from the…, PostgresGraphSyncStateRepository, What the graph projection is missing. Never authoritative about knowledge., PostgresUnitOfWork, async_sessionmaker, AsyncSession (+3 more)

### Community 31 - "FailureCluster"
Cohesion: 0.11
Nodes (14): AnalyzedCluster, DeepAnalyst, Protocol, Deep analysis port: what a large model may be asked about a failure cluster.…, Deterministic evidence and model interpretation, side by side and never merged.…, FailureClusterRepository, datetime, Protocol (+6 more)

### Community 32 - "InMemoryUnitOfWork"
Cohesion: 0.11
Nodes (10): get_project(), Project, Return the project or raise NotFoundError; delivery maps it to its protocol., fixture, uow(), TestGetProject, InMemoryUnitOfWork, BaseException (+2 more)

### Community 33 - "null"
Cohesion: 0.12
Nodes (22): maxLength, type, description, pattern, type, type, null, object (+14 more)

### Community 34 - "properties"
Cohesion: 0.09
Nodes (22): minLength, type, format, type, minLength, type, type, type (+14 more)

### Community 35 - "RunEvent"
Cohesion: 0.10
Nodes (29): Run, Move a run to a new lifecycle state. Every status change goes through the…, transition_run(), NewRunEvent, Durable run event log. This is the source of truth for what happened during a…, An event to append. The log assigns its sequence., Append durably, assigning the next per-run sequence. Called inside the same…, RunEvent (+21 more)

### Community 36 - "properties"
Cohesion: 0.10
Nodes (21): minLength, type, minLength, type, properties, minLength, type, artifact_id (+13 more)

### Community 37 - "prepared_container"
Cohesion: 0.15
Nodes (17): create_engine(), create_session_factory(), async_sessionmaker, AsyncEngine, AsyncSession, Async engine/session factory for PostgreSQL., policy_for(), prepared_container() (+9 more)

### Community 38 - "Run"
Cohesion: 0.08
Nodes (31): Project, StrEnum, Why this point was considered safe. Not every step earns one., RecoveryTrigger, Run, point(), UnitOfWorkFactory, TestRecoveryPoints (+23 more)

### Community 39 - "RunStatus"
Cohesion: 0.16
Nodes (26): TransitionRunCommand, _allowed_targets(), StrEnum, A run lifecycle invariant was violated., RunStatus, RunTransitionError, Verdict, make_run() (+18 more)

### Community 40 - "properties"
Cohesion: 0.10
Nodes (20): minimum, type, minimum, type, contradiction_count, failure_count, quality, reliability (+12 more)

### Community 41 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+11 more)

### Community 42 - "NotFoundError"
Cohesion: 0.10
Nodes (38): Pin the plan version now, or run without a plan (exploratory). Resolving…, _resolve_plan(), start_run(), NotFoundError, A use case required an entity that does not exist., error_response(), Any, get_request_id() (+30 more)

### Community 43 - "redis/streams.py"
Cohesion: 0.17
Nodes (13): _as_text(), _decode(), _encode(), _parse_read_reply(), Redis, RunEvent, Redis Streams fan-out for run events. Streams are bounded (`MAXLEN ~`): they…, Flatten an XREAD reply into (message_id, fields) pairs. (+5 more)

### Community 44 - "required"
Cohesion: 0.11
Nodes (18): additionalProperties, $id, candidate_id, environment_id, kind, model_derived, observed, payload (+10 more)

### Community 45 - "request_context.py"
Cohesion: 0.25
Nodes (7): accept_inbound_request_id(), new_request_id(), LogRecord, Request identity, propagated to responses and logs. `X-Request-Id` is accepted…, Reuse the caller's id when it is sane, otherwise mint one. An unbounded or…, RequestIdLogFilter, set_request_id()

### Community 46 - "properties"
Cohesion: 0.11
Nodes (18): minLength, type, format, type, minLength, type, minLength, type (+10 more)

### Community 47 - "properties"
Cohesion: 0.12
Nodes (17): maxLength, minLength, type, default, type, maxLength, minLength, type (+9 more)

### Community 48 - "projection.py"
Cohesion: 0.10
Nodes (17): EmbeddingGateway, Protocol, Embedding gateway port. A separate port from `ModelGateway` because the two…, Which model produced the vectors. Recorded with the projection: embeddings from…, Vectors in the same order as the inputs. Raises rather than returning short or…, _as_texts(), GraphitiEmbedder, GraphMemoryModelUseError (+9 more)

### Community 49 - "sync_pending"
Cohesion: 0.18
Nodes (15): datetime, UnitOfWorkFactory, Rebuild one project's projection from durable knowledge. The recovery path for…, Committed per entry, not per batch: an interrupted pass must keep the progress…, Drain the backlog once. Safe to call repeatedly and safe to interrupt., rebuild_project(), _record(), sync_pending() (+7 more)

### Community 50 - "CriterionResult"
Cohesion: 0.07
Nodes (19): _invalidate_what_this_run_disproved(), datetime, Withdraw memory this run's deterministic results disprove. The other half of…, A result together with the run it belongs to. `CriterionResult` deliberately…, Store results for a run, replacing any previous answer for the same criteria., Deterministic failures across a project's recent runs, newest run first. Only…, RunCriterionResult, The criterion a report leads with. Deterministic failures come first, because a… (+11 more)

### Community 51 - "test_budget_and_classification.py"
Cohesion: 0.09
Nodes (21): assertion(), EndlessPlanner, policy_for(), Any, PlanStep, Verdict, What a run says when it could not do its job. The taxonomy in `FailureKind` has…, It used to come back inconclusive. The policy stopping a run is a fact about… (+13 more)

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
Cohesion: 0.12
Nodes (24): create_project(), CreateProjectCommand, Project, create_run_policy(), CreateRunPolicyCommand, Create a run policy, optionally making it the project default. Policies are…, list_projects(), post_project() (+16 more)

### Community 57 - "consolidate_experience"
Cohesion: 0.19
Nodes (12): consolidate_experience(), ConsolidateExperienceCommand, ConsolidateExperienceResult, datetime, Factory, A completed run with a verified result, evidence and a safe point., seed_finished_run(), sighting() (+4 more)

### Community 58 - "test_gateway.py"
Cohesion: 0.18
Nodes (20): build_gateway(), completion(), make_policy(), plan_once(), Any, parametrize, The phase gate: invalid model output never reaches the browser. These run the…, The gate itself: drive the real graph and assert the browser stayed idle. (+12 more)

### Community 59 - "BrowserAction"
Cohesion: 0.06
Nodes (69): ActionTarget, BrowserAction, BrowserActionType, IdempotencyStrategy, StrEnum, Semantic locator. Coordinates are deliberately absent from v1., BrowserDecision, ClusterAnalysis (+61 more)

### Community 60 - "enum"
Cohesion: 0.13
Nodes (15): enum, assert_text, assert_url, back, check, click, extract, fill (+7 more)

### Community 61 - "properties"
Cohesion: 0.13
Nodes (15): maxLength, minLength, type, maxLength, minLength, type, properties, name (+7 more)

### Community 62 - "deny"
Cohesion: 0.14
Nodes (13): permissions, deny, $schema, Bash(docker system prune *), Bash(git push --force *), Bash(rm -rf / *), Read(./.env), Read(./.env.development) (+5 more)

### Community 63 - "test-plan.schema.json"
Cohesion: 0.14
Nodes (13): additionalProperties, anyOf, $comment, $id, project_id, schema_version, required, $schema (+5 more)

### Community 64 - "projects-page.tsx"
Cohesion: 0.15
Nodes (8): plugins, GatewaysContext, DEFAULTS, FormValues, schema, oxc, react, typescript

### Community 65 - "GraphitiMemoryProjection"
Cohesion: 0.10
Nodes (15): One line a planner can read. Never the raw payload. Payloads hold captured…, summarize(), _attributes(), GraphitiMemoryProjection, group_id_for(), node_uuid_for(), Any, Drop every environment's projection for one project. (+7 more)

### Community 66 - "RecordingWorkflowGateway"
Cohesion: 0.11
Nodes (18): create_story(), CreateStoryCommand, UserStory, StartRunCommand, Project, The lost-response case: the client never saw the ACK and retries., ADR 0010 ordering: the run is durable before the workflow is started. Losing…, Seed a project with a default policy: a run cannot start without one. (+10 more)

### Community 67 - "build_worker"
Cohesion: 0.67
Nodes (3): build_worker(), Client, Worker

### Community 68 - "test_layer_boundaries.py"
Cohesion: 0.29
Nodes (13): forbidden_imports(), imported_modules(), layer_files(), parametrize, Path, The dependency rule is a test, not a review habit. Interfaces/Delivery ---->…, Policy enforcement lives in a wrapper, so the raw adapter must stay contained.…, A guard that cannot fail proves nothing: plant a violation and expect a catch. (+5 more)

### Community 70 - "Quality"
Cohesion: 0.08
Nodes (19): datetime, Quality, Evidence counts and the reliability derived from them. `reliability` is…, Successes against everything that went wrong, with contradictions counted…, Two sightings of the same fact, added together. Counts add rather than replace:…, The context in which the knowledge held. Retrieval hard-filters on these before…, Validity, candidate() (+11 more)

### Community 71 - "KnowledgeExperienceCandidate"
Cohesion: 0.06
Nodes (20): GraphIngestion, Protocol, Write one candidate into the projection and return its node id. Idempotent by…, Bulk write used by rebuild, kept separate so a normal sync cannot accidentally…, candidate_id -> node id, for those that made it. Partial success is normal and…, KnowledgeRepository, CandidateStatus, Store a candidate, folding it into an equivalent one when it already exists.… (+12 more)

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
Nodes (12): do_run_migrations(), include_name(), Run migrations in 'online' mode., Alembic's own signature, spelled out. It was loose enough that a type checker…, Run migrations in 'offline' mode. This configures the context with just a URL…, In this scenario we need to create an Engine and associate a connection with…, run_async_migrations(), run_migrations_offline() (+4 more)

### Community 78 - "ModelCapability"
Cohesion: 0.11
Nodes (23): ModelCapability, StrEnum, What a task needs, not who provides it., ModelEndpoint, ModelRouter, One OpenAI-compatible server. `max_concurrency` is the real limit of the box…, Semaphore key. Shared by every task routed to this endpoint, which is the…, Chooses the endpoint for a task. First registered wins per capability. (+15 more)

### Community 79 - "main.ts"
Cohesion: 0.12
Nodes (51): hasErrors(), readPlanFile(), failureContext(), unclassified(), usage(), agentInstall(), asString(), CLI_VERSION (+43 more)

### Community 80 - "list_events"
Cohesion: 0.15
Nodes (12): list_run_events(), RunEvent, Read the durable event log of a run. This is the catch-up path a client uses…, websocket, run_events_socket(), list_events(), ge, le (+4 more)

### Community 81 - "activities.py"
Cohesion: 0.10
Nodes (25): Activities: the only place workflow code is allowed to touch the outside world.…, AnalyzeFailuresParams, ConsolidateParams, Serializable payloads exchanged between workflow and activities. Kept free of…, What one firing of a schedule needs to create its run. No run id: the run does…, One workflow per run: the id makes a duplicate start a no-op, not a second run., One firing, with the key that makes it exactly one run. `idempotency_key` is…, Nothing to carry: the backlog lives in PostgreSQL and names its own work. A… (+17 more)

### Community 82 - "vllm/gateway.py"
Cohesion: 0.08
Nodes (32): Bounded resource reservations (browser slots, model slots, accounts). Every…, capability_for(), Inference task types and capabilities (docs/08). The domain names *what kind of…, TaskType, DeepAnalyst backed by AirLLM. AirLLM runs a model far larger than the GPU by…, InferenceError, ModelOutputError, ModelUnavailableError (+24 more)

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
Cohesion: 0.11
Nodes (26): consolidate(), ConsolidationInput, ConsolidationOutcome, _from_result(), _origin_of(), datetime, Turn a finished run into knowledge candidates. Only *verified* outcomes become…, Scheme and host, without the path. The origin is the part that decides whether… (+18 more)

### Community 91 - "test_schema_constraints.py"
Cohesion: 0.35
Nodes (12): knowledge_values(), AsyncSession, The durable schema must defend the run invariants, not just the Python layer.…, The rule the whole learning design rests on, defended below the Python layer.…, seed(), test_a_model_derived_candidate_cannot_be_trusted_in_the_database(), test_criterion_ids_are_unique_within_a_story(), test_knowledge_must_come_from_somewhere() (+4 more)

### Community 92 - "properties"
Cohesion: 0.22
Nodes (9): minLength, type, type, properties, intent, payload, type, minLength (+1 more)

### Community 93 - "properties"
Cohesion: 0.22
Nodes (9): type, evidence_set_id, model_invocation_id, source_episode_id, source_run_id, properties, type, minLength (+1 more)

### Community 94 - "GraphSyncRecord"
Cohesion: 0.13
Nodes (8): GraphSyncRecord, GraphSyncStateRepository, Protocol, The rebuild backlog: what the graph is missing, oldest first. This is what…, What `memory status` reports. A growing pending count is the signal that the…, Whether one durable candidate has reached the graph projection. Deliberately…, Upsert the sync state of one candidate., InMemoryGraphSyncStateRepository

### Community 95 - "cli/package.json"
Cohesion: 0.06
Nodes (34): ajv, bin, roveqa, dependencies, ajv, devDependencies, eslint, @eslint/js (+26 more)

### Community 96 - "fakes/unit_of_work.py"
Cohesion: 0.08
Nodes (8): InMemoryEnvironmentRepository, InMemoryMemoryFeedbackRepository, InMemoryRunEventLog, InMemoryRunPolicyRepository, InMemoryStateMapRepository, RunEvent, Exploration maps, keyed by run like the real table. `previous_run` reads…, In-memory unit of work with real transaction semantics. Snapshot on enter,…

### Community 97 - "analyze_failures.py"
Cohesion: 0.14
Nodes (27): analyze_failures(), AnalyzeFailuresCommand, AnalyzeFailuresResult, _freshness_rule(), datetime, Analyse a finished run's failures: group first, ask a model second, store both.…, Ask about a cluster only when the answer could have changed. This is the…, Reduce stored results to comparable signals, dropping what cannot be grouped.… (+19 more)

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
Cohesion: 0.07
Nodes (32): Protocol, Take a slot, or None when the resource is already at capacity., Extend a held slot. False when the lease already lapsed., Give the slot back. False when this reservation no longer holds one., Slots currently held, excluding lapsed ones., ResourceSemaphore, AsyncClient, Resource semaphore contract. Capacity must hold under concurrency, and a worker… (+24 more)

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
Cohesion: 0.05
Nodes (54): _item_document(), Any, The portable MemoryContext document (`contracts/memory-context.schema.json`).…, to_document(), Compatibility, compatibility_of(), _confirmed(), _differs() (+46 more)

### Community 110 - "test_schedules_api.py"
Cohesion: 0.13
Nodes (13): client(), client_for(), gateway(), AsyncClient, fixture, The scheduling endpoints over real HTTP. What matters here is not that a POST…, A 201 for a schedule nobody stored is the worst possible answer here., store() (+5 more)

### Community 112 - "config.ts"
Cohesion: 0.15
Nodes (18): readExisting(), setup(), SetupInput, SetupResult, asPositiveInt(), asString(), ConfigFlags, DEFAULT_API_URL (+10 more)

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
Cohesion: 0.26
Nodes (12): record_memory_feedback(), RecordMemoryFeedbackCommand, RecordMemoryFeedbackResult, Build fresh units of work over one shared store/database. A factory rather than…, unit_of_work_factory(), CandidateStatus, Factory, A run plus one piece of knowledge a later run could act on. (+4 more)

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
Cohesion: 0.06
Nodes (34): Protocol, A recurring run, described the way the caller asked for it. Carries the plan…, Register a recurring run. Raises `AlreadyExistsError` on a taken id. The id is…, Pause or resume. False when there is no such schedule. Pausing rather than…, RunSchedule, ScheduleGateway, Replace, not append. A retried activity must not leave two answers for one…, Namespaced so a schedule and a run can never collide in Temporal's id space. (+26 more)

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
Cohesion: 0.05
Nodes (69): _budget_document(), _budget_from(), _enum(), from_document(), _metadata_from(), _optional_int(), _optional_str(), Any (+61 more)

### Community 133 - "summary"
Cohesion: 0.50
Nodes (4): summary, maxLength, minLength, type

### Community 134 - "Container"
Cohesion: 0.13
Nodes (18): Protocol, Durable workflow port. Temporal owns the run lifecycle (ADR 0002/0009) but…, Start the durable workflow for an already-persisted run. Naturally idempotent:…, Ask the run to stop at its next safe point. Idempotent., WorkflowGateway, Container, container_from_websocket(), get_artifacts() (+10 more)

### Community 135 - "environment_id"
Cohesion: 0.50
Nodes (4): maxLength, minLength, type, environment_id

### Community 136 - "clustering.py"
Cohesion: 0.12
Nodes (15): _build_cluster(), _cluster_id(), ClusterStatus, StrEnum, Grouping failures, and telling causes apart from consequences. Two jobs, both…, What is worth sending to a model, if anything is. Only independent clusters:…, The first setup failure in each run, if there was one. First rather than worst:…, How much smaller the investigation got. 0.0 when nothing was duplicated. (+7 more)

### Community 137 - "run_policy_id"
Cohesion: 0.50
Nodes (4): run_policy_id, maxLength, minLength, type

### Community 138 - "run_for"
Cohesion: 0.16
Nodes (12): prompt_for(), What grows with a run's work, and what must not grow with its length. A multi-…, Both of these are past the window, and that is the point. A prompt does grow…, Otherwise it would read a partial history as a complete one and conclude it had…, Folding is about context, not about forgetting. The run still knows how far it…, A run that did real work: many episodes, each with many steps., What a checkpoint has to carry. Pickle rather than the real serializer: this…, run_for() (+4 more)

### Community 144 - "TestPlan"
Cohesion: 0.06
Nodes (29): Protocol, TestPlan repository port. Plans are immutable per version, so there is no…, Store a new plan version. Raises AlreadyExistsError if that version exists., Most recently created version. Used to *choose* a version at run creation,…, Plan versions compiled from a story, newest first., TestPlanRepository, CriterionResultRepository, Protocol (+21 more)

### Community 145 - "action_id"
Cohesion: 0.67
Nodes (3): minLength, type, action_id

### Community 146 - "test_client.py"
Cohesion: 0.12
Nodes (27): InferenceBudget, Bounds every call carries. An unbounded model call is an unbounded run., CircuitBreaker, Circuit breaker for a model endpoint. When a GPU box is down, thirty-second…, True when a call may be attempted, half-opening after the cooldown., ask(), build_client(), completion() (+19 more)

### Community 147 - "Adaptive QA Learning Graph"
Cohesion: 0.06
Nodes (31): 1. Hard filters, 2. Candidate search, 3. Ranking, 4. Bounded context, 5. Revalidation, Adaptive QA Learning Graph, ExperienceConsolidator, Goal (+23 more)

### Community 151 - "HANDOFF.md"
Cohesion: 0.06
Nodes (31): Acceptance Gates (Phase 07), Acceptance Gates (Phase 08), Acceptance Gates (Phase 09), Acceptance Gates (Phase 10), Acceptance Gates (Phase 11), Acceptance Gates (Phase 12), Acceptance Gates (Phase 13), Architecture Decisions Made (+23 more)

### Community 153 - "from_document"
Cohesion: 0.14
Nodes (23): from_document(), _optional_timestamp(), Any, datetime, The portable knowledge document (`contracts/knowledge-experience.schema.json`).…, Serialize to the public contract. Optionals inside `provenance` and `validity`…, Parse a document from outside this system. Everything is re-validated by the…, _timestamp() (+15 more)

### Community 156 - "redact_payload"
Cohesion: 0.10
Nodes (20): _clean_text(), Any, Exception, Redaction before anything is learned. Memory outlives the run that produced it,…, Content that must not be learned at all, rather than learned redacted., Clean a payload, or refuse it. Raises `UnsafeKnowledgeError` when the content…, _redact_entry(), redact_payload() (+12 more)

### Community 157 - "routers/memory.py"
Cohesion: 0.11
Nodes (29): GraphMemoryPort, The learned-memory graph projection. Everything here is about a store that is…, Remove one candidate from the projection. Used when knowledge is invalidated or…, Drop one project's projection, for a rebuild., Whether the store answers. Never raises: this is what `memory status` reports,…, memory_status(), MemoryStatus, What `memory status` answers. Written so that it still answers when the graph… (+21 more)

### Community 187 - "commands/run.ts"
Cohesion: 0.09
Nodes (26): cancelRun(), createRun(), CreateRunInput, DEFAULT_WAIT_TIMEOUT_MS, getProject(), getRun(), listProjects(), parseProject() (+18 more)

### Community 188 - "derive_verdict"
Cohesion: 0.20
Nodes (11): derive_verdict(), Verdict, Turn criterion results into the run's QA verdict. Ordering matters and is…, met(), not_met(), FailureKind, parametrize, Ordering matters: the finding worth having wins over the noise around it. (+3 more)

### Community 190 - "routers/schedules.py"
Cohesion: 0.22
Nodes (20): create_schedule(), delete_schedule(), list_schedules(), _owned(), pause(), ContainerDep, get, post (+12 more)

### Community 191 - "InMemoryGraphMemory"
Cohesion: 0.15
Nodes (9): GraphHit, GraphUnavailableError, Exception, The projection could not be reached or written. Typed so callers can tell it…, Candidate ids the projection considers relevant, scoped before searching.…, InMemoryGraphMemory, A projection that behaves like the real one, including being wipeable., A store that is never reachable. Used where the point is that nothing else… (+1 more)

### Community 193 - "seed_project_with_default_policy"
Cohesion: 0.24
Nodes (14): exploration_outcome(), Load one run's map and diff it against the previous exploration. Raises…, Create a project plus the default policy a run needs to start., seed_project_with_default_policy(), page(), Factory, Storing a map and comparing it against the last one. Parametrized over the in-…, Three explorations: the second compares against the first, the third against… (+6 more)

### Community 194 - "PageState"
Cohesion: 0.03
Nodes (59): Where the page is and what it offers, as roles and accessible names. Read-only,…, _clickable(), ExplorationBudget, ExplorationProgress, Frontier, FrontierEntry, StrEnum, The frontier, and the budgets that make an exploration end. An explorer that… (+51 more)

### Community 195 - "signal_from"
Cohesion: 0.15
Nodes (13): normalize(), The structural facts a failure carries before anyone interprets it. Triage…, Strip the parts of an observation that differ between two runs of one problem.…, Reduce one criterion result to a signal, or decline. Returns `None` for…, signal_from(), _split_url(), _status_in(), failure() (+5 more)

### Community 201 - "CriterionOutcome"
Cohesion: 0.18
Nodes (15): contradicted_by(), _is_contradicted(), Comparing what memory claims against what a run deterministically observed.…, Stored knowledge this run's verified results disprove. A model-derived result…, CriterionOutcome, StrEnum, candidate(), CandidateStatus (+7 more)

### Community 204 - "test_memory_api.py"
Cohesion: 0.16
Nodes (11): app_client(), broken_graph(), no_graph(), AsyncClient, fixture, The memory administration endpoints over real HTTP. What matters here is the…, TestRebuild, TestStatus (+3 more)

### Community 205 - "DeepAnalysisService"
Cohesion: 0.20
Nodes (9): DeepAnalysisService, Decides which clusters are worth a large model, and asks about those only.…, FailureKind, What a large model is allowed to change about a failure cluster: nothing. Two…, Answers every cluster, and remembers exactly what it was shown., RecordingAnalyst, signal(), TestARunReportsWithoutADeepModel (+1 more)

### Community 210 - "apply_feedback"
Cohesion: 0.22
Nodes (13): apply_feedback(), FeedbackKind, datetime, StrEnum, Fold one verified outcome into a candidate and re-derive its status. Pure and…, candidate(), feedback(), What later runs do to knowledge they used. Consolidation is only half a… (+5 more)

### Community 213 - "test_temporal_workflow.py"
Cohesion: 0.17
Nodes (22): Client, TemporalWorkflowGateway, postgres_unit_of_work_factory(), Client, fixture, RunStatus, UnitOfWorkFactory, Worker (+14 more)

### Community 214 - "errors.ts"
Cohesion: 0.17
Nodes (12): LintFinding, lintPlan(), looksLikeSelector(), MAX_PLAN_BYTES, PlanDocument, PlanStep, ScaffoldOptions, scaffoldPlan() (+4 more)

### Community 215 - "schemas.ts"
Cohesion: 0.14
Nodes (12): artifactSchema, compiledPlanSchema, ContractError, failureContextSchema, findingSchema, memoryStatusSchema, projectSchema, reportSchema (+4 more)

### Community 217 - "test_graphiti_projection.py"
Cohesion: 0.18
Nodes (17): execute(), falkordb_test_url(), projection(), Any, The projection against a real FalkorDB. The in-memory double proves the sync…, The guard against acquiring a hosted dependency by omission. Graphiti's…, A projection over a disposable graph, torn down whatever the test did., test_a_candidate_is_written_and_found_again() (+9 more)

### Community 218 - "ClusterHypothesis"
Cohesion: 0.18
Nodes (8): ClusterAnalysisRequest, ClusterHypothesis, One cluster, reduced to what is worth a large model's time. Built from the…, A model's guess at why a cluster happened, labelled as a guess. `failure` set…, Attach an interpretation to a cluster. False when this pass already did. Cannot…, TestAHypothesisNeverBecomesEvidence, Stands in for a deep endpoint that is down — the state this system spends most…, RefusingAnalyst

### Community 221 - "run_story"
Cohesion: 0.14
Nodes (16): Any, Human-readable report, with the same separation the document makes., Machine-readable report. Every criterion says who decided it., render_markdown(), _status(), to_document(), execute(), Execute the story once against a live target app. (+8 more)

### Community 223 - "StateMap"
Cohesion: 0.09
Nodes (17): Protocol, Durable state maps. An exploration's value is comparative. One map says what an…, Store one exploration's map and what it spent. Idempotent per `(run_id,…, The map one run produced, or None when that run did not explore., The run whose map this one should be compared against. The most recent earlier…, StateMapRepository, ChangedState, compare() (+9 more)

### Community 224 - "compilerOptions"
Cohesion: 0.10
Nodes (20): compilerOptions, declaration, exactOptionalPropertyTypes, lib, module, moduleResolution, noImplicitOverride, noUncheckedIndexedAccess (+12 more)

### Community 225 - "test_operational_queries.py"
Cohesion: 0.17
Nodes (18): OperationalQuery, query_named(), Operational questions, answered from durable rows. Why SQL and not a metrics…, factory(), fixture, parametrize, Every operational query, executed against the real schema. The reason these…, An aggregate over no rows must still return a row. "No clusters" and "the query… (+10 more)

### Community 226 - "api.ts"
Cohesion: 0.15
Nodes (16): ApiClient, ApiClientOptions, ApiResponse, backoffMs(), extractDetail(), isRetryableStatus(), MAX_RESPONSE_BYTES, MAX_RETRY_AFTER_MS (+8 more)

### Community 227 - "agent.ts"
Cohesion: 0.22
Nodes (12): BEGIN_MARKER, END_MARKER, installClaudeSkill(), InstallInput, InstallResult, readIfPresent(), requireSupportedAgent(), SKILL_PATH (+4 more)

### Community 228 - "diff.ts"
Cohesion: 0.16
Nodes (16): classify(), CriterionChange, CriterionDelta, CriterionSide, delta(), describePlan(), diffRuns(), loadRunSummary() (+8 more)

### Community 229 - "parse_affordances"
Cohesion: 0.17
Nodes (6): _absolute(), parse_affordances(), Resolve an href against the page, or decline. `None` for anything that is not…, Pull role/name pairs out of an ARIA snapshot, deduplicated and bounded. A…, TestParsing, TestResolvingLinkDestinations

### Community 230 - "VLLMModelGateway"
Cohesion: 0.11
Nodes (13): ModelInvocation, Provenance for a model-derived conclusion (docs/08 evidence boundary). A…, AirLLMDeepAnalyst, AsyncClient, One client for the endpoint, so its circuit breaker remembers across calls.…, Implements `DeepAnalyst` (application port) over the DEEP-capability endpoint., EndpointStats, InferenceMetrics (+5 more)

### Community 231 - "test_deep_analyst.py"
Cohesion: 0.18
Nodes (19): build_analyst(), completion(), deep_endpoint(), parametrize, Request, Response, The deep-analysis adapter, against a server that can be made to misbehave. What…, A cause nobody can re-derive is not comparable to the next one (docs/08). (+11 more)

### Community 232 - "commands/memory.ts"
Cohesion: 0.23
Nodes (15): memoryRebuild, memoryStatus, memorySync(), memoryValidate(), MemoryValidation, num(), parseRebuild(), parseStatus() (+7 more)

### Community 233 - "Patterns adopted"
Cohesion: 0.11
Nodes (18): 10. Agent installation, 1. Agent-first CLI, 2. Machine-pure output, 3. Versioned TestPlan files, 4. Atomic FailureBundle, 5. Idempotency and retry ownership, 6. Wait does not mean cancel, 7. Runtime response validation (+10 more)

### Community 234 - "client.ts"
Cohesion: 0.18
Nodes (6): ApiClient, ApiClientOptions, ApiError, HttpMemoryGateway, toApiError(), toMemoryStatus()

### Community 235 - "MemoryMetrics"
Cohesion: 0.15
Nodes (9): MemoryMetrics, What memory is doing, and whether it is worth its cost. Same shape as the…, What the counters have to be able to tell an operator. A run's verdict looks…, Summaries and payloads never reach the log line. They derive from page content,…, test_a_projection_that_never_catches_up_is_countable(), test_hypotheses_are_counted_separately_from_facts(), test_nothing_derived_from_page_content_is_recorded(), test_what_was_learned_and_what_was_withdrawn_are_both_visible() (+1 more)

### Community 236 - "InMemoryStore"
Cohesion: 0.11
Nodes (29): fixture, store(), uow(), workflows(), InMemoryStore, client(), failure(), AsyncClient (+21 more)

### Community 237 - "record_finished_run"
Cohesion: 0.23
Nodes (11): benchmark(), execute_run(), datetime, Factory, Persist the run the way a real one would be, then consolidate it., The cold baseline and the warm run, on the same flow., One run of the flow, warm or cold, through the real retrieval path., record_finished_run() (+3 more)

### Community 238 - "API and Event Contracts"
Cohesion: 0.11
Nodes (17): API and Event Contracts, Artifacts, CLI envelope, Event envelope, Exploration (Phase 12), Failure triage (Phase 11), Important event types, Memory admin (Phase 09) (+9 more)

### Community 239 - "ports/gateways.ts"
Cohesion: 0.07
Nodes (10): CompiledPlan, DraftStory, MemoryGateway, NewProjectInput, ProjectGateway, RunEventStream, RunGateway, RunSubscription (+2 more)

### Community 240 - "test_database_failure.py"
Cohesion: 0.19
Nodes (15): factory(), FlakyDatabase, Factory, fixture, queued_run(), A transient PostgreSQL failure, against a real PostgreSQL. The gap the recovery…, They share a transaction on purpose. A run that moved without leaving its event…, Sanity on the fixture: a double that never failed would make every assertion… (+7 more)

### Community 241 - "bundle.test.ts"
Cohesion: 0.18
Nodes (15): ArtifactFetcher, assertBytesMatch(), assertCoherent(), BundleArtifact, BundleManifest, describe(), MANIFEST_NAME, materialize() (+7 more)

### Community 242 - "flaky.ts"
Cohesion: 0.16
Nodes (14): CriterionStability, FlakyInput, FlakyReport, MAX_REPLAYS, measureFlakiness(), MIN_REPLAYS, record(), renderFlaky() (+6 more)

### Community 243 - "Runtime responsibilities"
Cohesion: 0.12
Nodes (16): Architecture, Context diagram, Deployment v1, FastAPI, Filesystem, Graphiti/FalkorDB, LangGraph, Model Router (+8 more)

### Community 244 - "dependencies"
Cohesion: 0.12
Nodes (17): dependencies, @hookform/resolvers, react, react-dom, react-hook-form, react-router, @tanstack/react-query, zod (+9 more)

### Community 245 - "MemoryContextRequest"
Cohesion: 0.21
Nodes (18): MemoryContextRequest, datetime, retrieve_memory_context(), MemoryScope, The situation the current run is in. `None` means "not known in this run"…, Run, What earlier runs learned about this application, or nothing. Failure is…, TestMemoryIsNotFollowedBlindly (+10 more)

### Community 246 - "envelope.test.ts"
Cohesion: 0.17
Nodes (10): Recorded, envelopeSchema, packageRoot, VALID_PLAN, validateEnvelope, CLI_ENTRY, CliResult, packageRoot (+2 more)

### Community 247 - "test_memory_benchmark_real_model.py"
Cohesion: 0.20
Nodes (14): _checkpointer(), endpoint(), episode_runner(), measure(), Measurement, Any, Cold versus warm against the real model. `test_memory_benchmark.py` measures…, Where the browser actually ended up. Read from the episode's observed URL… (+6 more)

### Community 248 - "policy"
Cohesion: 0.20
Nodes (6): policy(), parametrize, Origin allowlist semantics. Ambiguous matching is how allowlists get bypassed,…, No implicit subdomains: evil.app.example.com is a different origin., TestAllowsOrigin, TestNormalizeOrigin

### Community 249 - "Combination rules"
Cohesion: 0.13
Nodes (14): Adaptive memory graph, Always-on disciplines, Brainstorming is conditional, Claude Code Skill Routing, CLI/API contracts, Combination rules, Frontend design split, Graphify and the runtime graph (+6 more)

### Community 250 - "FailureKind"
Cohesion: 0.28
Nodes (14): _check_deterministically(), _criterion_of(), _judge_semantically(), _labelled(), FailureKind, PlanStep, Evaluate a plan's acceptance criteria against the page the run ended on. The…, Keep the model's words visibly the model's, next to what was actually seen. (+6 more)

### Community 251 - "container.py"
Cohesion: 0.08
Nodes (36): AsyncPostgresSaver, EpisodeRunner, Protocol, build_deep_analyst(), build_episode_runner(), build_model_router(), AsyncClient, Redis (+28 more)

### Community 252 - "PostgresKnowledgeRepository"
Cohesion: 0.18
Nodes (8): knowledge_candidate_to_domain(), knowledge_candidate_to_model(), KnowledgeCandidateModel, Durable knowledge (ADR 0008). FalkorDB holds a projection of this, not the…, PostgresKnowledgeRepository, CandidateStatus, Durable knowledge. The graph is rebuilt from these rows, never the reverse., Read the row for update so two workers learning the same thing at the same time…

### Community 253 - "Guía de uso"
Cohesion: 0.13
Nodes (15): 10. Explorar sin historia, 1. Levantarlo, 2. Tu primer proyecto, 3. Escribir una historia, 4. Lanzar un run y leerlo, 5. Qué significa cada veredicto, 6. La CLI, 7. En CI (+7 more)

### Community 254 - "finished_run"
Cohesion: 0.31
Nodes (9): consolidate(), finished_run(), datetime, Factory, A completed run that checked one criterion deterministically., scope(), TestOneDeterministicDisagreementWithdrawsIt, TestOneRunIsCountedOnce (+1 more)

### Community 255 - "Bounded contexts"
Cohesion: 0.14
Nodes (13): Action safety fields, Agent, Bounded contexts, Browser, Core statuses, Domain Model, Important invariants, Inference (+5 more)

### Community 256 - "runs/run.ts"
Cohesion: 0.15
Nodes (10): CANCELLABLE, isActive(), isTerminal(), Run, RUN_STATUSES, RunStatus, TERMINAL, Verdict (+2 more)

### Community 257 - "test_evidence_chain.py"
Cohesion: 0.26
Nodes (14): execute(), prepared(), Any, Path, Evidence, from the live page to the failure bundle. Phase 07 could say *which*…, The chain Phase 07 could not complete: capture, index, and reach it again., `evidence_refs` existed and nobody filled it; a failure named nothing showable., It used to be written empty, so recovery would rebuild a browser and go nowhere. (+6 more)

### Community 258 - "test_triage_from_a_real_run.py"
Cohesion: 0.38
Nodes (10): execute(), Any, Path, Triage over a real failing run, end to end. Everything else in this package…, A member is a pointer, not a copy — so the observation and the evidence refs a…, run_and_triage(), test_a_real_failure_becomes_a_stored_cluster(), test_the_cluster_points_back_at_the_row_it_came_from() (+2 more)

### Community 259 - "Agent-First CLI Design"
Cohesion: 0.15
Nodes (12): Agent-First CLI Design, Agent verification skill, Boundary, Configuration, Failure bundle disk layout, Output contract, Purpose, Request behavior (+4 more)

### Community 260 - "Operations Runbook"
Cohesion: 0.17
Nodes (12): Backup, Consultas operacionales, Drill ejecutado (2026-08-20), Instalar el skill de verificación en un repo ajeno, Instalar la CLI como cliente externo, Levantar el stack en una máquina nueva, Memoria adaptativa, Operations Runbook (+4 more)

### Community 262 - "safe_url"
Cohesion: 0.22
Nodes (10): Turning a URL into something safe to keep. Applications put credentials in…, Scheme, host and path. No query, no fragment, no userinfo. Query strings and…, safe_url(), parametrize, Which parts of a URL are safe to keep. The rule this function encodes: a URL to…, test_a_reset_link_keeps_nothing_of_its_token(), test_credentials_in_the_authority_are_dropped(), test_it_keeps_where_and_drops_what_rides_along() (+2 more)

### Community 263 - "test_exploring_a_real_run.py"
Cohesion: 0.29
Nodes (13): execute(), explore_twice(), exploring_project(), Any, Path, queue_run(), An exploring run, end to end: Temporal activity, real Chromium, real…, The same application, unchanged between runs, must produce no findings. This is… (+5 more)

### Community 264 - "test_learning_from_a_real_run.py"
Cohesion: 0.36
Nodes (11): execute(), Any, Path, What a real run actually learns. Everything else about consolidation is tested…, Page text is untrusted data. Whatever is stored must be safe to replay., run_and_learn(), test_a_finished_run_leaves_durable_knowledge(), test_a_first_run_teaches_nothing_the_agent_may_act_on() (+3 more)

### Community 265 - "envelope.ts"
Cohesion: 0.15
Nodes (13): checkContracts(), describeHealth(), doctor(), DoctorReport, problemError(), SUPPORTED_PLAN_SCHEMA, Config, Envelope (+5 more)

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
Cohesion: 0.26
Nodes (6): makeEvent(), makeRun(), NotFound, gatewaysWith(), renderRun(), withReport()

### Community 277 - "UserStory"
Cohesion: 0.14
Nodes (13): AcceptanceCriterion, Create a user story for an existing project., AcceptanceCriterion, UserStory, UserStory, story_to_domain(), story_to_model(), UserStoryModel (+5 more)

### Community 278 - "StoredCluster"
Cohesion: 0.22
Nodes (5): A cluster as it comes back out, with whatever was ever guessed about it., StoredCluster, InMemoryFailureClusterRepository, datetime, Accumulating triage, with the same two-write split as the tables. `record`…

### Community 279 - "Claude Code Project Instructions"
Cohesion: 0.22
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

### Community 283 - "HttpRunGateway"
Cohesion: 0.23
Nodes (3): HttpRunGateway, toRun(), toRunEventPage()

### Community 285 - "JudgementRequest"
Cohesion: 0.31
Nodes (5): CriterionJudgement, JudgementRequest, Ask a model whether an acceptance criterion looks satisfied. Last in the…, CountingModel, The real gateway, with the two numbers the benchmark needs. Counting at this…

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
Cohesion: 0.18
Nodes (11): Bootstrap, Development-Time Codebase Graph (Graphify), Dónde está el peso, El grafo de hoy (2026-08-20, commit `916faed`), Failure behavior, La dirección de dependencias, medida, Purpose, Query-before-scan rule (+3 more)

### Community 291 - "Memory Evaluation — reach the records page"
Cohesion: 0.22
Nodes (8): A. Mechanism — cold baseline vs warm run, B. Real model — cold baseline vs warm run, Decision, Delta, Memory Evaluation — reach the records page, Notes / provenance, Quality, Scope

### Community 292 - "Release Checklist"
Cohesion: 0.22
Nodes (8): Antes de etiquetar, Drills, con evidencia, El demo de release (2026-08-20), Gates automáticos, Lo que este release no promete, Los cinco defectos que encontraron el soak y el demo, Release Checklist, Soak de release (2026-08-20)

### Community 293 - "run-events.ts"
Cohesion: 0.27
Nodes (6): toRunEvent(), originAsWebSocket(), parseEvent(), RunEventStreamOptions, WebSocketRunEventStream, WS_PATH

### Community 294 - "Memory Evaluation — <flow>"
Cohesion: 0.22
Nodes (8): Cold baseline, Decision, Delta, Memory Evaluation — <flow>, Notes / provenance, Quality, Scope, Warm run

### Community 295 - "test_migrations_from_empty.py"
Cohesion: 0.27
Nodes (9): psycopg_dsn(), The migration chain must run against a database that has nothing in it. Phase…, No fixture data, no library tables, nothing created by `create_all` first., LangGraph creates its own checkpoint tables through `setup()`. Dropping one…, run_alembic(), test_no_migration_touches_a_table_langgraph_owns(), test_the_whole_chain_applies_to_an_empty_database(), with_database() (+1 more)

### Community 296 - "API design principles"
Cohesion: 0.25
Nodes (7): API design principles, CLI contracts, Collections and payload bounds, Commands and long-running runs, Errors, Evolution, Resource model

### Community 297 - "Error handling patterns"
Cohesion: 0.25
Nodes (7): Classify first, Error handling patterns, Layering, Observability and UX, Retry discipline, Tests, Wait and cancellation

### Community 298 - "plan_of"
Cohesion: 0.25
Nodes (5): plan_of(), Plan, PlanStep, step(), TestPlansAndTextAreBoundedByTheDomain

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
Cohesion: 0.31
Nodes (4): App(), defaultQueryClient(), root, PROJECT

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
Cohesion: 0.25
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
Nodes (3): RunSnapshot, RunWatch, WatchHandlers

### Community 314 - "parse"
Cohesion: 0.24
Nodes (8): HttpStoryGateway, parse(), toArtifact(), toCompiledPlan(), toFinding(), toRunReport(), toStories(), toStory()

### Community 315 - "use-projects-viewmodel.ts"
Cohesion: 0.33
Nodes (8): CreateProjectViewModel, isNotFound(), messageFor(), ProjectsViewModel, ProjectViewModel, useCreateProject(), useProjectsViewModel(), useProjectViewModel()

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

### Community 327 - "README.md"
Cohesion: 0.14
Nodes (8): El estado que carga un checkpoint, Lo que sigue sin medirse, Los pasos dentro de un episodio, Performance Profile, Qué ocupa en disco, Contexto crítico que no debes redescubrir, Continue RoveQA with Opus 5, Pasos obligatorios, en orden

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

### Community 342 - "toProject"
Cohesion: 0.32
Nodes (3): HttpProjectGateway, toProject(), toProjects()

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
Nodes (3): main(), Drop and recreate the test database's schema. The suite's database is…, reset()

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
Cohesion: 0.67
Nodes (3): FindingsList(), OUTCOME_LABEL, toneFor()

### Community 377 - "routers/artifacts.py"
Cohesion: 0.29
Nodes (6): ArtifactRepositoryDep, download_artifact(), get, Response, UnitOfWorkDep, Artifact download. An artifact id is an identifier, never a filesystem path…

### Community 427 - "frontend/test/boundaries.test.ts"
Cohesion: 0.38
Nodes (6): COMPOSITION_ROOT, FORBIDDEN, offendersIn(), relative(), sourceFiles(), SRC

### Community 456 - ".oxlintrc.json"
Cohesion: 0.33
Nodes (5): rules, react/only-export-components, react/rules-of-hooks, $schema, warn

### Community 457 - "client"
Cohesion: 0.40
Nodes (5): client(), AsyncClient, fixture, The ceiling is enforced at the boundary, not trusted to callers. A client…, test_the_api_refuses_an_unbounded_event_page()

### Community 458 - "step_id"
Cohesion: 0.40
Nodes (5): step_id, maxLength, minLength, pattern, type

### Community 459 - "to_psycopg_dsn"
Cohesion: 0.50
Nodes (4): Translate `postgresql+asyncpg://...` into the plain URL psycopg expects., to_psycopg_dsn(), Two drivers, one database: the translation lives in one place., test_the_sqlalchemy_dsn_is_translated_for_psycopg()

### Community 462 - "plan_id"
Cohesion: 0.50
Nodes (4): maxLength, minLength, type, plan_id

### Community 463 - "project_id"
Cohesion: 0.50
Nodes (4): maxLength, minLength, type, project_id

### Community 464 - "read_contracts"
Cohesion: 0.67
Nodes (3): get, The versions this server reads and writes., read_contracts()

### Community 465 - "valid_from"
Cohesion: 0.67
Nodes (3): valid_from, format, type

## Knowledge Gaps
- **1327 isolated node(s):** `$schema`, `Read(./.env)`, `Read(./.env.local)`, `Read(./.env.development)`, `Read(./.env.production)` (+1322 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **60 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `InMemoryStore` connect `InMemoryStore` to `RunPolicy`, `AsyncClient`, `InvalidEntityError`, `ports/unit_of_work.py`, `TestPlan`, `test_policy_resolution.py`, `RecoveryPoint`, `postgres/repositories.py`, `UserStory`, `langgraph/graph.py`, `StoredCluster`, `test_realtime.py`, `InMemoryProjectRepository`, `InMemoryUnitOfWork`, `RunEvent`, `Run`, `CriterionResult`, `RecordingWorkflowGateway`, `KnowledgeExperienceCandidate`, `client`, `test_memory_api.py`, `ClusterHypothesis`, `GraphSyncRecord`, `StateMap`, `fakes/unit_of_work.py`, `test_schedules_api.py`, `unit_of_work_factory`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `KnowledgeExperienceCandidate` connect `KnowledgeExperienceCandidate` to `mappers.py`, `InvalidEntityError`, `ports/unit_of_work.py`, `PlanningRequest`, `postgres/repositories.py`, `from_document`, `routers/memory.py`, `projection.py`, `sync_pending`, `CriterionResult`, `consolidate_experience`, `InMemoryGraphMemory`, `GraphitiMemoryProjection`, `Quality`, `CriterionOutcome`, `apply_feedback`, `CandidateKind`, `InMemoryStore`, `select`, `MemoryContextRequest`, `unit_of_work_factory`, `PostgresKnowledgeRepository`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Why does `UnitOfWork` connect `UnitOfWork` to `application/errors.py`, `Container`, `InvalidEntityError`, `http/schemas.py`, `ports/unit_of_work.py`, `RunActivities`, `TestPlan`, `test_policy_resolution.py`, `RecoveryPoint`, `UserStory`, `langgraph/graph.py`, `routers/memory.py`, `FailureCluster`, `RunEvent`, `prepared_container`, `NotFoundError`, `CriterionResult`, `projects.py`, `consolidate_experience`, `seed_project_with_default_policy`, `RecordingWorkflowGateway`, `KnowledgeExperienceCandidate`, `list_events`, `test_temporal_workflow.py`, `GraphSyncRecord`, `StateMap`, `analyze_failures.py`, `test_database_failure.py`, `MemoryContextRequest`, `unit_of_work_factory`, `container.py`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `seed_project_with_default_policy()` (e.g. with `CreateProjectCommand` and `UnitOfWork`) actually correct?**
  _`seed_project_with_default_policy()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `BrowserAction` (e.g. with `BrowserGateway` and `PlannedAction`) actually correct?**
  _`BrowserAction` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 48 inferred relationships involving `UnitOfWork` (e.g. with `analyze_failures()` and `_store_hypotheses()`) actually correct?**
  _`UnitOfWork` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `KnowledgeExperienceCandidate` (e.g. with `ConsolidateExperienceResult` and `_invalidate_what_this_run_disproved()`) actually correct?**
  _`KnowledgeExperienceCandidate` has 28 INFERRED edges - model-reasoned connections that need verification._