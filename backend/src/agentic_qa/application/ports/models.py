"""Model gateway port.

The agent asks for a decision and receives a *typed* action, never free-form text it
then has to parse into behaviour. A model that wants something outside the closed
browser action set simply cannot express it (docs/07, docs/13).

Phase 05 runs on a deterministic fake so the graph's durability can be tested without
model variance; Phase 06 adds the vLLM adapter behind this same port.
"""

from dataclasses import dataclass, field
from typing import Protocol

from agentic_qa.domain.agent.state import EpisodeSummary, StepRecord
from agentic_qa.domain.browser.actions import BrowserAction


@dataclass(frozen=True)
class PlanningRequest:
    """Bounded context handed to the planner.

    It carries the working window and the episode summaries, never the full history:
    what the planner reads must not grow with the length of the run.
    """

    goal: str
    observation: str
    recent_steps: tuple[StepRecord, ...] = field(default=())
    episode_summaries: tuple[EpisodeSummary, ...] = field(default=())


@dataclass(frozen=True)
class PlannedAction:
    """The planner's decision. `action=None` means the goal needs nothing more."""

    action: BrowserAction | None
    rationale: str = ""
    model_derived: bool = True
    """Always true for planner output: a decision is a hypothesis, not an observation."""


class ModelGateway(Protocol):
    async def next_action(self, request: PlanningRequest) -> PlannedAction: ...
