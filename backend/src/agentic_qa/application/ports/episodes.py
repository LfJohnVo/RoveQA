"""Episode execution port.

One activity per episode (ADR 0009), and the activity stays thin: it asks for an
episode to be executed and records what came back. Whether that execution uses
LangGraph, and which checkpointer or browser it drives, is entirely behind here.
"""

from dataclasses import dataclass
from typing import Protocol

from agentic_qa.domain.browser.evidence import EvidenceRef
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


class EpisodeRunner(Protocol):
    async def run_episode(self, request: EpisodeRequest) -> EpisodeResult: ...
