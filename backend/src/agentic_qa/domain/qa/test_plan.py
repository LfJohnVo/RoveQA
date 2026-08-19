"""TestPlan: what a run must verify (QA bounded context).

Mirrors `contracts/test-plan.schema.json`, a **versioned public contract**: plans are
exported, imported and handed to agents, so their shape changes only with a version.

A plan says *what to verify*, not *how to click*. The agent works out the actions at
run time; the plan is the reproducible part, and the link that survives is
`criterion_id -> step`. Without it, a failed run can say "something broke" but not
"this acceptance criterion is not met", which is the only statement a QA report can
actually defend.

Plans are immutable once created. A run records which plan version governed it, so a
finished run can always be read against the rules it actually ran under — editing a
plan in place would rewrite the meaning of runs already finished.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.qa.user_story import UserStory
from agentic_qa.domain.validation import require_identifier, require_text

SCHEMA_VERSION = "roveqa.test-plan.v1"

MAX_PLAN_STEPS = 200
"""Matches the contract. A plan that needs more than this is not a plan."""

MetadataValue = str | int | float | bool | None


class PlanStepType(StrEnum):
    ACTION = "action"
    ASSERTION = "assertion"


class PlanMode(StrEnum):
    STORY = "story"
    WORKFLOW = "workflow"
    REGRESSION = "regression"
    EXPLORATORY = "exploratory"


class PlanPriority(StrEnum):
    P0 = "p0"
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"


class MemoryPolicy(StrEnum):
    NORMAL = "normal"
    FROZEN = "frozen"
    OFF = "off"


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    type: PlanStepType
    description: str
    criterion_id: str | None = None
    """Which acceptance criterion this step serves. Assertions must name one."""

    critical: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", _require_step_id(self.step_id))
        object.__setattr__(
            self,
            "description",
            require_text(self.description, field="description", max_length=4000),
        )
        if self.criterion_id is not None:
            object.__setattr__(
                self, "criterion_id", require_identifier(self.criterion_id, field="criterion_id")
            )
        elif self.type is PlanStepType.ASSERTION:
            # An assertion that traces back to no criterion cannot make a run's result
            # mean anything: it would pass or fail without saying what was promised.
            raise InvalidEntityError(f"assertion step {self.step_id} must name a criterion")


@dataclass(frozen=True)
class PlanBudget:
    """Per-plan limits. Narrows the RunPolicy, never widens it."""

    max_actions: int | None = None
    max_duration_seconds: int | None = None
    max_model_calls: int | None = None

    def __post_init__(self) -> None:
        if all(
            value is None
            for value in (self.max_actions, self.max_duration_seconds, self.max_model_calls)
        ):
            raise InvalidEntityError("a budget must bound at least one thing")
        for name, value, minimum in (
            ("max_actions", self.max_actions, 1),
            ("max_duration_seconds", self.max_duration_seconds, 1),
            ("max_model_calls", self.max_model_calls, 0),
        ):
            if value is not None and value < minimum:
                raise InvalidEntityError(f"{name} must be at least {minimum}")


@dataclass(frozen=True)
class TestPlan:
    plan_id: str
    plan_version: str
    project_id: str
    name: str
    mode: PlanMode
    plan_steps: tuple[PlanStep, ...]
    source_story_id: str | None = None
    environment_id: str | None = None
    run_policy_id: str | None = None
    budget: PlanBudget | None = None
    description: str = ""
    priority: PlanPriority | None = None
    memory_policy: MemoryPolicy = MemoryPolicy.NORMAL
    metadata: tuple[tuple[str, MetadataValue], ...] = field(default=())
    """Pairs rather than a dict so the plan stays hashable and order is stable across
    an export/import round trip. Values keep their JSON type: a plan that came in with
    `"retries": 3` must go back out with `3`, not `"3"`."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", require_identifier(self.plan_id, field="plan_id"))
        object.__setattr__(
            self,
            "plan_version",
            require_text(self.plan_version, field="plan_version", max_length=100),
        )
        object.__setattr__(
            self, "project_id", require_identifier(self.project_id, field="project_id")
        )
        object.__setattr__(self, "name", require_text(self.name, field="name", max_length=240))
        object.__setattr__(self, "plan_steps", tuple(self.plan_steps))

        if not self.plan_steps:
            raise InvalidEntityError("a test plan needs at least one step")
        if len(self.plan_steps) > MAX_PLAN_STEPS:
            raise InvalidEntityError(f"a test plan may not exceed {MAX_PLAN_STEPS} steps")
        _reject_duplicates(step.step_id for step in self.plan_steps)

        if self.run_policy_id is None and self.budget is None:
            # The contract's anyOf. A plan that bounds nothing and names no policy would
            # have to be run under limits invented at execution time.
            raise InvalidEntityError("a test plan needs a run_policy_id or a budget")
        if self.run_policy_id is not None:
            object.__setattr__(
                self, "run_policy_id", require_identifier(self.run_policy_id, field="run_policy_id")
            )
        if self.source_story_id is not None:
            object.__setattr__(
                self,
                "source_story_id",
                require_identifier(self.source_story_id, field="source_story_id"),
            )
        if self.environment_id is not None:
            object.__setattr__(
                self,
                "environment_id",
                require_identifier(self.environment_id, field="environment_id"),
            )

    @property
    def assertions(self) -> tuple[PlanStep, ...]:
        return tuple(step for step in self.plan_steps if step.type is PlanStepType.ASSERTION)

    @property
    def actions(self) -> tuple[PlanStep, ...]:
        return tuple(step for step in self.plan_steps if step.type is PlanStepType.ACTION)

    @property
    def objective(self) -> str:
        """What the agent is asked to achieve, in one instruction.

        Only the action steps: the assertions describe what will be *checked* afterwards
        and handing them to the planner invites it to aim at the check rather than at
        the behaviour — an agent told "the confirmation page shows an order number" can
        navigate to a page showing one without ever placing an order.
        """
        actions = self.actions
        if not actions:  # pragma: no cover - compile_story always emits a goal step
            return self.name
        goal = actions[-1].description
        preconditions = [step.description for step in actions[:-1]]
        if not preconditions:
            return goal
        return f"{goal}. First make sure: " + "; ".join(preconditions) + "."

    @property
    def covered_criteria(self) -> frozenset[str]:
        return frozenset(
            step.criterion_id for step in self.plan_steps if step.criterion_id is not None
        )

    def steps_for(self, criterion_id: str) -> tuple[PlanStep, ...]:
        return tuple(step for step in self.plan_steps if step.criterion_id == criterion_id)


def compile_story(
    story: UserStory,
    *,
    plan_id: str,
    plan_version: str,
    run_policy_id: str | None = None,
    environment_id: str | None = None,
    budget: PlanBudget | None = None,
) -> TestPlan:
    """Compile a story into a plan, deterministically.

    No model is involved. The same story compiles to the same plan every time, which is
    what makes "a known story passes or fails reproducibly" a property of the system
    rather than of the weather. The model's judgement enters later, when the agent
    decides how to satisfy a step — and its conclusions stay labelled as such.

    Every acceptance criterion becomes exactly one assertion step carrying its id, so
    coverage is total by construction rather than by review.
    """
    steps: list[PlanStep] = [
        PlanStep(
            step_id=f"pre-{index + 1}",
            type=PlanStepType.ACTION,
            description=precondition,
        )
        for index, precondition in enumerate(story.preconditions)
    ]
    steps.append(
        PlanStep(
            step_id="goal",
            type=PlanStepType.ACTION,
            description=f"As {story.actor}, {story.goal}",
            critical=True,
        )
    )
    steps.extend(
        PlanStep(
            step_id=f"assert-{criterion.criterion_id}",
            type=PlanStepType.ASSERTION,
            description=criterion.description,
            criterion_id=criterion.criterion_id,
            critical=True,
        )
        for criterion in story.acceptance_criteria
    )

    plan = TestPlan(
        plan_id=plan_id,
        plan_version=plan_version,
        project_id=story.project_id,
        name=story.goal,
        mode=PlanMode.STORY,
        plan_steps=tuple(steps),
        source_story_id=story.story_id,
        environment_id=environment_id,
        run_policy_id=run_policy_id,
        budget=budget,
        description=_describe(story),
    )

    missing = {
        criterion.criterion_id for criterion in story.acceptance_criteria
    } - plan.covered_criteria
    if missing:  # pragma: no cover - defends the invariant above against future edits
        raise InvalidEntityError(f"compiled plan does not cover criteria: {sorted(missing)}")
    return plan


def _describe(story: UserStory) -> str:
    """Carry the story's forbidden outcomes into the plan's own description.

    They are part of what the run must not do, and a plan that dropped them would let a
    later export lose a constraint the story stated.
    """
    if not story.forbidden_outcomes:
        return f"Story {story.story_id}"
    forbidden = "; ".join(story.forbidden_outcomes)
    return f"Story {story.story_id}. Must not: {forbidden}"


def _require_step_id(value: str) -> str:
    step_id = require_text(value, field="step_id", max_length=120)
    if not all(character.isalnum() or character in "._-" for character in step_id):
        # The contract restricts step ids to a safe alphabet; they end up in file names
        # and report anchors.
        raise InvalidEntityError(f"step_id must match [A-Za-z0-9._-]+: {value}")
    return step_id


def _reject_duplicates(step_ids: Iterable[str]) -> None:
    seen: set[str] = set()
    for step_id in step_ids:
        if step_id in seen:
            raise InvalidEntityError(f"duplicate plan step id: {step_id}")
        seen.add(step_id)


def steps_by_criterion(steps: Sequence[PlanStep]) -> dict[str, tuple[PlanStep, ...]]:
    grouped: dict[str, list[PlanStep]] = {}
    for step in steps:
        if step.criterion_id is not None:
            grouped.setdefault(step.criterion_id, []).append(step)
    return {criterion: tuple(items) for criterion, items in grouped.items()}
