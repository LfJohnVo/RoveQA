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
from agentic_qa.domain.knowledge.memory_context import MemoryItem


@dataclass(frozen=True)
class PlanCriterion:
    """One acceptance criterion, as the planner needs to read it.

    `expected_text` is the literal a deterministic check will look for, and None means
    the criterion will be judged by a model. The difference matters to the planner: it
    can assert the first and must not pretend to assert the second.
    """

    criterion_id: str
    description: str
    expected_text: str | None = None


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
    folded_episodes: int = 0
    """Episodes older than the summary window. Told to the planner as a count, so it
    knows the history it can see is partial rather than complete."""

    allowed_origins: tuple[str, ...] = field(default=())
    """Where this run may go, from its RunPolicy.

    Information, not just a fence. The allowlist is the only place that knows what
    application is under test, and until it reached the prompt the planner had to
    *guess* a URL — which the same allowlist then refused. A planner starting on
    `about:blank` with no origin to aim at cannot take a first step at all."""

    criteria: tuple[PlanCriterion, ...] = field(default=())
    """What the run will be judged by.

    The plan has always carried these, and they reached only the final verification
    node. So the planner was asked to advance a goal without being told what would
    count as reaching it — and, given an assertion-shaped goal, could only guess at the
    literal to assert. It guessed the field as well as the text.
    """

    memory: tuple[MemoryItem, ...] = field(default=())
    """What earlier verified runs learned about this application, already scoped,
    ranked and bounded (docs/26).

    Carried as domain items rather than pre-rendered text so the label on each one —
    observed or model-derived, compatible or needing revalidation — survives all the
    way to whatever builds the prompt. A summary string would arrive as an assertion
    with no way to tell a checked fact from a guess."""


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

    rejected: bool = False
    """The decision arrived and *we* refused it — a click with no target, an assertion
    with nothing to assert.

    Different in kind from an unreachable model or unusable output, and worth telling
    apart: a refusal is something the planner can correct once it is told what was
    wrong, while a dead endpoint will be just as dead on the next call. Flattened into
    one `failure` string, both ended the episode on the spot, so a single malformed
    proposal cost a whole run."""

    def __post_init__(self) -> None:
        if self.failure is not None and self.action is not None:
            raise ValueError("a failed decision cannot also carry an action")


@dataclass(frozen=True)
class ModelInvocation:
    """Provenance for a model-derived conclusion (docs/08 evidence boundary).

    A hypothesis that cannot say which model and which prompt produced it is not
    reproducible and not comparable: an eval that changes a prompt could not tell its
    own results from the previous wording's.
    """

    invocation_id: str
    model: str
    prompt_version: str


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

    invocation: ModelInvocation | None = None
    """Which model and prompt produced this. Absent only when nothing was produced."""

    def __post_init__(self) -> None:
        if self.failure is not None and self.satisfied is not None:
            raise ValueError("a failed judgement cannot also carry a verdict")


class ModelGateway(Protocol):
    async def next_action(self, request: PlanningRequest) -> PlannedAction: ...

    async def judge(self, request: JudgementRequest) -> CriterionJudgement: ...
