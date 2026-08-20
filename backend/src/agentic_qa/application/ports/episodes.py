"""Episode execution port.

One activity per episode (ADR 0009), and the activity stays thin: it asks for an
episode to be executed and records what came back. Whether that execution uses
LangGraph, and which checkpointer or browser it drives, is entirely behind here.
"""

from dataclasses import dataclass
from typing import Protocol

from agentic_qa.domain.browser.evidence import EvidenceRef
from agentic_qa.domain.exploration.comparison import StateMap
from agentic_qa.domain.exploration.frontier import ExplorationBudget, ExplorationReport
from agentic_qa.domain.knowledge.memory_context import MemoryItem
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.qa.test_plan import PlanStep
from agentic_qa.domain.qa.verification import CriterionResult


@dataclass(frozen=True)
class EpisodeRequest:
    run_id: str
    goal: str
    episode_index: int
    policy: RunPolicy
    assertions: tuple[PlanStep, ...] = ()
    """The plan's acceptance criteria, evaluated while the browser still holds the
    page the run finished on."""

    verification_hints: dict[str, str] | None = None
    """criterion_id -> literal the page must contain. Present hints are what make a
    result deterministic instead of a model's opinion."""

    memory: tuple[MemoryItem, ...] = ()
    """What earlier verified runs learned, already scoped, ranked and bounded.

    Retrieved by the activity rather than by the graph: reading durable state is I/O,
    and the graph stays free of it so a replay cannot depend on what the database
    happened to contain at replay time (ADR 0009)."""

    exploration: ExplorationBudget | None = None
    """Present when this episode explores instead of following a plan.

    A budget rather than a flag: the caller states what the episode may spend, so the
    limit is visible at the boundary instead of being derived somewhere inside an
    adapter. Never wider than the run's policy — `ExplorationBudget.under` is how one
    is built."""


@dataclass(frozen=True)
class EpisodeResult:
    more_work: bool
    """Whether another episode should follow."""

    graph_checkpoint_id: str | None = None
    """Where the run can resume; the caller turns it into a durable RecoveryPoint."""

    safe_point: str | None = None
    """Why this moment is safe, when the graph decided it is one."""

    failure_reason: str | None = None
    """Set when the episode ended unresolved. Absence is not proof of success."""

    criterion_results: tuple[CriterionResult, ...] = ()
    """One per plan assertion. Empty for a run with no plan."""

    evidence: tuple[EvidenceRef, ...] = ()
    """Artifacts captured while the browser was still open. The caller indexes them."""

    observed_url: str | None = None
    """Where the episode ended. Recovery needs it: rebuilding a browser without
    knowing where to go lands on a blank page and re-verifies nothing."""

    state_map: StateMap | None = None
    """What an exploring episode mapped. `None` for a planned one.

    Carries its own `complete` flag, because a map that stopped on a budget cannot tell
    "removed" from "never reached" and a comparison against it must say so."""

    exploration_report: ExplorationReport | None = None
    """What it spent and why it stopped. Reported separately from the map: "12 states"
    and "12 states, and it stopped because it ran out of actions" are different
    findings."""


class EpisodeRunner(Protocol):
    async def run_episode(self, request: EpisodeRequest) -> EpisodeResult: ...
