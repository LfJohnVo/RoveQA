"""Serializable payloads exchanged between workflow and activities.

Kept free of domain entities: what crosses the Temporal boundary is stored in the
event history for the life of the workflow, so it must stay small and stable.
"""

from dataclasses import dataclass

TASK_QUEUE = "agentic-qa"
WORKFLOW_ID_PREFIX = "run"


def workflow_id_for(run_id: str) -> str:
    """One workflow per run: the id makes a duplicate start a no-op, not a second run."""
    return f"{WORKFLOW_ID_PREFIX}:{run_id}"


@dataclass
class RunParams:
    run_id: str
    project_id: str
    start_episode: int = 0
    """Carried in the single argument so continue-as-new keeps one stable payload.

    A second workflow argument would make the converter fall back to raw JSON.
    """

    explore: bool = False
    """Whether this run explores instead of following a plan.

    Explicit, not inferred. A plan-less run has always meant "work towards this goal
    with the planner", and quietly turning that into a deterministic crawl would remove
    a capability nobody asked to lose. Exploring is a different job — no model, a
    frontier, a state map — so it is a different request.
    """


@dataclass
class TransitionParams:
    run_id: str
    target_status: str
    verdict: str | None = None


@dataclass
class ConsolidateParams:
    run_id: str
    """Only the id crosses the boundary. The activity reads the run, its results and
    its evidence from PostgreSQL, so the workflow history does not carry a copy of
    everything the run learned."""


@dataclass
class AnalyzeFailuresParams:
    run_id: str
    """The run boundary that triggered the pass. Only the id crosses: the activity reads
    the project's recent failures from PostgreSQL, and a payload listing them would be a
    copy in workflow history that goes stale the moment another run finishes."""


@dataclass
class SyncGraphParams:
    """Nothing to carry: the backlog lives in PostgreSQL and names its own work.

    A payload listing candidates would go stale between being written into workflow
    history and being executed, and the queue is already the authority on what is
    missing."""


@dataclass
class EpisodeParams:
    run_id: str
    episode_index: int
    goal: str = "explore the target application"
    """Fallback for a run with no plan. A run that names a plan gets its objective from
    that plan version, resolved in the activity — the workflow stays free of I/O and its
    history stays free of a full plan document."""

    explore: bool = False
    """Whether this run explores instead of following a plan.

    Explicit, not inferred. A plan-less run has always meant "work towards this goal
    with the planner", and quietly turning that into a deterministic crawl would remove
    a capability nobody asked to lose. Exploring is a different job — no model, a
    frontier, a state map — so it is a different request.
    """


@dataclass
class EpisodeOutcome:
    """Result of one episode.

    `more_work` is what ends the loop. Phase 05 replaces the activity body with the
    LangGraph execution; the workflow shape stays exactly as ADR 0009 fixed it.
    """

    more_work: bool

    verdict: str | None = None
    """QA verdict derived from the criterion results, or None for a run with no
    plan. Only the value crosses the boundary: the results themselves are durable in
    PostgreSQL, and copying them into workflow history would grow it per episode."""


SCHEDULE_ID_PREFIX = "sched"


def schedule_id_for(schedule_id: str) -> str:
    """Namespaced so a schedule and a run can never collide in Temporal's id space."""
    return f"{SCHEDULE_ID_PREFIX}:{schedule_id}"


@dataclass
class ScheduledRunParams:
    """What one firing of a schedule needs to create its run.

    No run id: the run does not exist yet. It is created by the first activity of
    `ScheduledRunWorkflow`, keyed by the firing's own workflow id, so a retried firing
    finds the run it already made instead of starting a second regression.
    """

    schedule_id: str
    project_id: str
    cron: str = ""
    """The literal the caller wrote.

    Carried here because Temporal does not hand it back: it normalises a cron string
    into a structured calendar spec, so `describe()` returns something that fires at
    the same times but is not the text anybody typed. Showing a user a rewritten
    version of their own schedule is a small lie that makes them doubt the rest.
    """

    plan_id: str | None = None
    plan_version: str | None = None
    """None means "resolve the latest at each firing" — the right default for a nightly
    suite, and a deliberate choice rather than a pin nobody set."""

    environment_id: str | None = None
    run_policy_id: str | None = None


@dataclass
class StartScheduledRunParams:
    """One firing, with the key that makes it exactly one run.

    `idempotency_key` is the firing's own workflow id. Temporal derives that from the
    schedule and the scheduled time, so it is stable across retries and replays of this
    firing and different for the next one — which is precisely the identity a run
    creation needs (docs/12).
    """

    idempotency_key: str
    schedule: ScheduledRunParams
