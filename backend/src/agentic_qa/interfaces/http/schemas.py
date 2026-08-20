"""Transport DTOs.

Separate from domain entities on purpose (docs/03): a schema change here must never
be able to reshape the domain, and response models are validated at runtime so a
malformed 2xx fails loudly instead of becoming a fake success.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agentic_qa.application.ports.events import RunEvent
from agentic_qa.application.ports.schedules import RunSchedule
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.qa.user_story import UserStory
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=240)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    name: str
    default_run_policy_id: str | None = None
    """Whether this project can start a run at all.

    A run resolves its policy from the project when none is named (docs/12), so a
    project without one cannot run. Exposing it lets a client say so before someone
    tries, instead of surfacing the precondition as a validation error at the end.
    """

    @classmethod
    def from_domain(cls, project: Project) -> "ProjectResponse":
        return cls(
            project_id=project.project_id,
            name=project.name,
            default_run_policy_id=project.default_run_policy_id,
        )


class CreateRunPolicyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed_origins: list[str] = Field(min_length=1)
    """RFC 6454 origins; there is no safe empty allowlist, so at least one is required."""

    max_duration_seconds: int = Field(ge=1, le=172_800)
    max_actions: int = Field(ge=1, le=10_000)
    max_model_calls: int = Field(ge=0, le=10_000)
    destructive_actions: bool = False
    allow_file_uploads: bool = False
    upload_path_allowlist: list[str] = Field(default_factory=list)
    allow_downloads: bool = False
    max_depth: int | None = Field(default=None, ge=0)
    synthetic_data_allowed: bool = True
    set_as_project_default: bool = False


class RunPolicyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str
    project_id: str
    allowed_origins: list[str]
    max_duration_seconds: int
    max_actions: int
    max_model_calls: int
    destructive_actions: bool
    allow_file_uploads: bool
    upload_path_allowlist: list[str]
    allow_downloads: bool
    max_depth: int | None
    synthetic_data_allowed: bool

    @classmethod
    def from_domain(cls, policy: RunPolicy) -> "RunPolicyResponse":
        return cls(
            policy_id=policy.policy_id,
            project_id=policy.project_id,
            allowed_origins=list(policy.allowed_origins),
            max_duration_seconds=policy.max_duration_seconds,
            max_actions=policy.max_actions,
            max_model_calls=policy.max_model_calls,
            destructive_actions=policy.destructive_actions,
            allow_file_uploads=policy.allow_file_uploads,
            upload_path_allowlist=list(policy.upload_path_allowlist),
            allow_downloads=policy.allow_downloads,
            max_depth=policy.max_depth,
            synthetic_data_allowed=policy.synthetic_data_allowed,
        )


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=200)
    environment_id: str | None = Field(default=None, min_length=1, max_length=200)
    run_policy_id: str | None = Field(default=None, min_length=1, max_length=200)
    plan_id: str | None = Field(default=None, min_length=1, max_length=200)
    plan_version: str | None = Field(default=None, min_length=1, max_length=100)
    """Without a version the latest is resolved once, at creation, and pinned onto
    the run: what a run is judged by must not change while it runs."""

    explore: bool = False
    """Whether this run explores instead of following a plan.

    Explicit, not inferred. A plan-less run has always meant "work towards this goal
    with the planner", and quietly turning that into a deterministic crawl would remove
    a capability nobody asked to lose. Exploring is a different job — no model, a
    frontier, a state map — so it is a different request.
    """


class RunEventResponse(BaseModel):
    """Matches the envelope in docs/12 and contracts/run-event.schema.json."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    run_id: str
    sequence: int
    type: str
    occurred_at: datetime
    payload: dict[str, Any]
    request_id: str | None

    @classmethod
    def from_domain(cls, event: RunEvent) -> "RunEventResponse":
        return cls(
            event_id=event.event_id,
            run_id=event.run_id,
            sequence=event.sequence,
            type=event.type,
            occurred_at=event.occurred_at,
            payload=event.payload,
            request_id=event.request_id,
        )


class RunEventPageResponse(BaseModel):
    """`next_after` is the cursor to resume from; empty events means fully caught up."""

    model_config = ConfigDict(extra="forbid")

    events: list[RunEventResponse]
    next_after: int


class RunAcceptedResponse(BaseModel):
    """A lifecycle command was accepted; the durable status changes when it applies."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    accepted: str


class RunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    project_id: str
    status: RunStatus
    verdict: Verdict | None
    run_policy_id: str | None
    environment_id: str | None
    plan_id: str | None = None
    plan_version: str | None = None

    @classmethod
    def from_domain(cls, run: Run) -> "RunResponse":
        return cls(
            run_id=run.run_id,
            project_id=run.project_id,
            status=run.status,
            verdict=run.verdict,
            run_policy_id=run.run_policy_id,
            environment_id=run.environment_id,
            plan_id=run.plan_id,
            plan_version=run.plan_version,
        )


class AcceptanceCriterionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion_id: str = Field(min_length=1, max_length=200)
    """Authored, not generated: plans, results and findings all reference it."""

    description: str = Field(min_length=1, max_length=4000)
    verification_hint: str | None = Field(default=None, min_length=1, max_length=1000)
    """A literal the page must contain. Its presence is what makes a criterion
    verifiable deterministically instead of by a model's opinion."""


class CreateStoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: str = Field(min_length=1, max_length=500)
    goal: str = Field(min_length=1, max_length=1000)
    acceptance_criteria: list[AcceptanceCriterionPayload] = Field(min_length=1, max_length=100)
    preconditions: list[str] = Field(default_factory=list, max_length=50)
    forbidden_outcomes: list[str] = Field(default_factory=list, max_length=50)


class StoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    story_id: str
    project_id: str
    actor: str
    goal: str
    acceptance_criteria: list[AcceptanceCriterionPayload]

    @classmethod
    def from_domain(cls, story: UserStory) -> "StoryResponse":
        return cls(
            story_id=story.story_id,
            project_id=story.project_id,
            actor=story.actor,
            goal=story.goal,
            acceptance_criteria=[
                AcceptanceCriterionPayload(
                    criterion_id=criterion.criterion_id,
                    description=criterion.description,
                    verification_hint=criterion.verification_hint,
                )
                for criterion in story.acceptance_criteria
            ],
        )


class CompilePlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_policy_id: str | None = Field(default=None, min_length=1, max_length=200)
    environment_id: str | None = Field(default=None, min_length=1, max_length=200)
    plan_id: str | None = Field(default=None, min_length=1, max_length=200)
    """Supply an existing plan's id to publish a new version of it."""

    max_actions: int | None = Field(default=None, ge=1, le=10_000)
    max_duration_seconds: int | None = Field(default=None, ge=1, le=172_800)
    max_model_calls: int | None = Field(default=None, ge=0, le=10_000)


class ImportPlanRequest(BaseModel):
    """A portable plan document submitted directly, as the CLI does."""

    model_config = ConfigDict(extra="forbid")

    plan: dict[str, Any] = Field()
    plan_id: str | None = Field(default=None, min_length=1, max_length=200)
    """Absent means a new plan identity is minted. Identity is never derived from the
    content, or two unrelated plans with the same steps would merge into one."""

    plan_version: str | None = Field(default=None, min_length=1, max_length=100)
    """Absent means the content hash, which is what makes re-submitting the same
    document idempotent (docs/12)."""


class MemoryStatusResponse(BaseModel):
    """What `roveqa memory status` prints.

    Durable and projected counts are separate fields because they answer different
    questions: how much this project has learned, and how much of it the graph
    currently holds. One number could not say that the graph is empty but the
    knowledge is safe.
    """

    project_id: str
    environment_id: str
    graph_available: bool
    graph_schema_version: str
    durable_candidates: int
    actionable_candidates: int
    sync_pending: int
    sync_failed: int
    by_status: dict[str, int]


class MemoryValidateResponse(BaseModel):
    project_id: str
    environment_id: str
    healthy: bool
    problems: list[str]
    """Empty when healthy. Named rather than counted so an operator can act on them
    without reading logs."""

    status: MemoryStatusResponse


class MemoryRebuildResponse(BaseModel):
    project_id: str
    environment_id: str
    materialized: int
    forgotten: int
    failed: int
    graph_available: bool
    """False when the pass stopped because the store is down. Reported rather than
    raised: the durable side is fine and the backlog kept the work."""


class ClusterMemberResponse(BaseModel):
    """A pointer at one criterion result, not a copy of it."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    criterion_id: str


class ClusterHypothesisResponse(BaseModel):
    """A deep model's reading of a cluster, in its own object.

    Nested rather than flattened onto the cluster so a client cannot render a guess in
    the same shape as an observation. `model_derived` is always true and stays in the
    payload: a consumer that only reads this object still learns what it is holding.
    """

    model_config = ConfigDict(extra="forbid")

    probable_cause: str
    recommended_check: str
    confidence: str
    model_derived: bool
    failure: str | None = None
    """Why no hypothesis was produced. Set when the deep endpoint was down or answered
    unusably, in which case `probable_cause` is empty."""

    model_name: str | None = None
    prompt_version: str | None = None


class FailureClusterResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cluster_id: str
    failure_kind: str
    criterion_id: str
    status: str
    """`independent` or `blocked_downstream`. Only the first counts as a defect: one
    broken environment must not be reported as a dozen bugs."""

    reason: str
    observation: str
    http_status: str | None
    route: str | None
    blocked_by: str | None
    representative_run_id: str
    first_seen_at: datetime
    last_seen_at: datetime
    size: int
    members: list[ClusterMemberResponse]
    hypothesis: ClusterHypothesisResponse | None


class FailureClusterPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    clusters: list[FailureClusterResponse]
    counted_as_defects: int


class CreateScheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule_id: str = Field(min_length=1, max_length=200)
    """The caller's id, never generated. It is what makes creating the same schedule
    twice a conflict instead of a second nightly regression."""

    cron: str = Field(min_length=1, max_length=200)
    plan_id: str | None = Field(default=None, min_length=1, max_length=200)
    plan_version: str | None = Field(default=None, min_length=1, max_length=100)
    """Absent means the latest plan is resolved at each firing — right for "run the
    current suite nightly", wrong for a pinned regression. A choice, not a default
    nobody noticed."""

    environment_id: str | None = Field(default=None, min_length=1, max_length=200)
    run_policy_id: str | None = Field(default=None, min_length=1, max_length=200)
    paused: bool = False
    note: str = Field(default="", max_length=500)


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule_id: str
    project_id: str
    cron: str
    plan_id: str | None
    plan_version: str | None
    environment_id: str | None
    run_policy_id: str | None
    paused: bool
    note: str

    @classmethod
    def from_domain(cls, schedule: RunSchedule) -> "ScheduleResponse":
        return cls(
            schedule_id=schedule.schedule_id,
            project_id=schedule.project_id,
            cron=schedule.cron,
            plan_id=schedule.plan_id,
            plan_version=schedule.plan_version,
            environment_id=schedule.environment_id,
            run_policy_id=schedule.run_policy_id,
            paused=schedule.paused,
            note=schedule.note,
        )


class ScheduleListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    schedules: list[ScheduleResponse]


class ExploredStateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signature: str
    route: str
    url: str
    title: str
    affordances: list[str]
    """The normalised role:name keys the signature was built from. Enough to see what a
    page offers; not the page's text, which belongs in evidence and not in a map."""


class ChangedStateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: str
    gained: list[str]
    lost: list[str]


class ExplorationDeltaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_run_id: str
    new: list[ExploredStateResponse]
    gone: list[ExploredStateResponse]
    changed: list[ChangedStateResponse]
    unreachable_conclusions: bool
    """True when either exploration stopped on a budget, so `gone` may mean "never
    reached" rather than "removed". Reported rather than suppressed: hiding the finding
    and hiding its caveat are both ways of lying about it."""


class ExplorationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    project_id: str
    stop_reason: str
    complete: bool
    actions_taken: int
    states_discovered: int
    max_depth_reached: int
    frontier_remaining: int
    declined: int
    states: list[ExploredStateResponse]
    delta: ExplorationDeltaResponse | None
    """Absent for a project's first exploration. Everything being new is not a finding."""
