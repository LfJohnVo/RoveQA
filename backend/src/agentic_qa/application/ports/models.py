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
    """The planner's decision.

    Three outcomes, deliberately distinguishable:

    - `action` set: do this next.
    - `action=None, failure=None`: the planner says nothing more is needed.
    - `failure` set: no decision could be obtained at all.

    Collapsing the last two is how a dead model server turns into a run that reports
    success. A gateway that could not reach a model, or got output it could not use,
    must say so here rather than return an empty decision (docs/08).
    """

    action: BrowserAction | None
    rationale: str = ""
    model_derived: bool = True
    """Always true for planner output: a decision is a hypothesis, not an observation."""

    failure: str | None = None

    def __post_init__(self) -> None:
        if self.failure is not None and self.action is not None:
            raise ValueError("a failed decision cannot also carry an action")


@dataclass(frozen=True)
class JudgementRequest:
    """Ask a model whether an acceptance criterion looks satisfied.

    Last in the verification order (docs/06), never first: this is only reached when no
    deterministic check could answer.
    """

    criterion: str
    observation: str


@dataclass(frozen=True)
class CriterionJudgement:
    satisfied: bool | None
    """None means the model could not tell. Kept distinct from False: "I don't know" is
    not evidence of a defect."""

    reasoning: str = ""
    model_derived: bool = True
    """Always true. A judgement is a hypothesis and is labelled as one wherever it goes."""

    failure: str | None = None
    """Set when no judgement could be obtained at all, as in `PlannedAction`."""

    def __post_init__(self) -> None:
        if self.failure is not None and self.satisfied is not None:
            raise ValueError("a failed judgement cannot also carry a verdict")


class ModelGateway(Protocol):
    async def next_action(self, request: PlanningRequest) -> PlannedAction: ...

    async def judge(self, request: JudgementRequest) -> CriterionJudgement: ...
