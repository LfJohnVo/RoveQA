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


@dataclass
class TransitionParams:
    run_id: str
    target_status: str
    verdict: str | None = None


@dataclass
class EpisodeParams:
    run_id: str
    episode_index: int
    goal: str = "explore the target application"
    """Fallback for a run with no plan (exploratory). A run that names a plan gets its
    objective from that plan version, resolved in the activity — the workflow stays
    free of I/O and its history stays free of a full plan document."""


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
