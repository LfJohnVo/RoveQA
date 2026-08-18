"""Episode execution port.

One activity per episode (ADR 0009), and the activity stays thin: it asks for an
episode to be executed and records what came back. Whether that execution uses
LangGraph, and which checkpointer or browser it drives, is entirely behind here.
"""

from dataclasses import dataclass
from typing import Protocol

from agentic_qa.domain.projects.run_policy import RunPolicy


@dataclass(frozen=True)
class EpisodeRequest:
    run_id: str
    goal: str
    episode_index: int
    policy: RunPolicy


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


class EpisodeRunner(Protocol):
    async def run_episode(self, request: EpisodeRequest) -> EpisodeResult: ...
