"""Cold versus warm: does memory actually save anything?

The gate this answers (`plans/phase-09-knowledge-memory.md`) is deliberately harsh:
memory has to reduce planner calls or exploratory browser actions by at least 20% on a
stable flow *without* changing a correct verdict. If it cannot, the phase documents the
bottleneck rather than claiming the optimisation works.

Measured through the real pipeline — durable consolidation, real retrieval, the real
prompt-facing `MemoryContext` — with a planner double that reacts to memory the way a
competent planner would. That boundary is the honest one: this proves the plumbing
delivers usable memory and that acting on it is cheaper. Whether a particular language
model draws the same conclusion is a question for the real endpoint, and the report
says which of the two produced its numbers.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from agentic_qa.application.commands.consolidate_experience import (
    ConsolidateExperienceCommand,
    consolidate_experience,
)
from agentic_qa.application.ports.models import PlanningRequest
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.application.queries.memory_context import (
    MemoryContextRequest,
    retrieve_memory_context,
)
from agentic_qa.domain.knowledge.compatibility import MemoryScope
from agentic_qa.domain.knowledge.memory_context import MemoryItem
from agentic_qa.domain.projects.environment import Environment
from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult
from agentic_qa.domain.runs.recovery import (
    BrowserRecoveryData,
    RecoveryPoint,
    RecoveryTrigger,
)
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict
from tests.conftest import seed_project_with_default_policy
from tests.fakes.memory_aware_agent import MemoryAwarePlanner

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)

ORIGIN = "https://app.test"
GOAL_URL = f"{ORIGIN}/records/new"
DECOYS = (f"{ORIGIN}/dashboard", f"{ORIGIN}/settings", f"{ORIGIN}/reports")

MIN_REDUCTION = 0.20
"""The gate's threshold. Stated here so a regression fails the suite rather than
quietly eroding the number the phase was signed off on."""

Factory = Callable[[], UnitOfWork]


@dataclass
class RunMetrics:
    planner_calls: int
    browser_actions: int
    memory_items: int
    followed_memory: bool
    reached_goal: bool

    @property
    def is_correct(self) -> bool:
        return self.reached_goal


def reduction(cold: int, warm: int) -> float:
    return 0.0 if cold == 0 else (cold - warm) / cold


async def execute_run(
    factory: Factory,
    project_id: str,
    run_id: str,
    *,
    at: datetime,
    warm: bool,
) -> RunMetrics:
    """One run of the flow, warm or cold, through the real retrieval path."""
    scope = MemoryScope(
        project_id=project_id, environment_id="staging", origin=ORIGIN, app_version="2.1.0"
    )
    memory: tuple[MemoryItem, ...] = ()
    if warm:
        context = await retrieve_memory_context(
            factory(), MemoryContextRequest(scope=scope), now=at
        )
        memory = context.items

    planner = MemoryAwarePlanner(goal_url=GOAL_URL, decoys=DECOYS)
    while True:
        decision = await planner.next_action(
            PlanningRequest(
                goal="create a record",
                observation=planner.visited[-1] if planner.visited else "about:blank",
                memory=memory,
            )
        )
        if decision.action is None:
            break

    await record_finished_run(factory, project_id, run_id, at=at)
    return RunMetrics(
        planner_calls=planner.calls,
        browser_actions=len(planner.visited),
        memory_items=len(memory),
        followed_memory=planner.followed_memory,
        reached_goal=GOAL_URL in planner.visited,
    )


async def record_finished_run(
    factory: Factory, project_id: str, run_id: str, *, at: datetime
) -> None:
    """Persist the run the way a real one would be, then consolidate it."""
    async with factory() as uow:
        if await uow.environments.get("staging") is None:
            await uow.environments.add(
                Environment(environment_id="staging", project_id=project_id, name="Staging")
            )
        await uow.runs.add(
            Run(
                run_id=run_id,
                project_id=project_id,
                status=RunStatus.COMPLETED,
                verdict=Verdict.PASSED,
                environment_id="staging",
            )
        )
        await uow.criterion_results.record(
            run_id,
            [
                CriterionResult(
                    criterion_id="ac-create-record",
                    outcome=CriterionOutcome.MET,
                    observation="the new-record form is present",
                    model_derived=False,
                )
            ],
        )
        await uow.recovery_points.add(
            RecoveryPoint(
                recovery_point_id=f"rp-{run_id}",
                run_id=run_id,
                episode_index=0,
                trigger=RecoveryTrigger.EPISODE_CLOSED,
                graph_checkpoint_id=f"ck-{run_id}",
                browser=BrowserRecoveryData(url=GOAL_URL),
                created_at=at,
            )
        )
        await uow.commit()

    await consolidate_experience(
        factory(), ConsolidateExperienceCommand(run_id=run_id, app_version="2.1.0"), now=at
    )


async def benchmark(factory: Factory) -> tuple[RunMetrics, RunMetrics]:
    """The cold baseline and the warm run, on the same flow."""
    project_id = await seed_project_with_default_policy(factory, name=f"Bench-{uuid4().hex[:6]}")

    cold = await execute_run(factory, project_id, "run-cold", at=NOW, warm=False)
    # A second run so the route earns promotion: one sighting is a coincidence, and
    # nothing unpromoted is ever offered to a planner.
    await execute_run(factory, project_id, "run-second", at=NOW + timedelta(hours=1), warm=False)
    warm = await execute_run(
        factory, project_id, "run-warm", at=NOW + timedelta(hours=2), warm=True
    )
    return cold, warm


class TestMemoryPaysForItself:
    async def test_a_warm_run_makes_fewer_planner_calls(
        self, unit_of_work_factory: Factory
    ) -> None:
        cold, warm = await benchmark(unit_of_work_factory)

        assert warm.memory_items > 0, "the warm run was not warm; retrieval returned nothing"
        assert warm.followed_memory, "memory was offered and the planner did not use it"
        assert reduction(cold.planner_calls, warm.planner_calls) >= MIN_REDUCTION, (
            f"planner calls {cold.planner_calls} -> {warm.planner_calls}, "
            f"below the {MIN_REDUCTION:.0%} the phase gate requires"
        )

    async def test_a_warm_run_explores_less(self, unit_of_work_factory: Factory) -> None:
        cold, warm = await benchmark(unit_of_work_factory)

        assert reduction(cold.browser_actions, warm.browser_actions) >= MIN_REDUCTION, (
            f"browser actions {cold.browser_actions} -> {warm.browser_actions}, "
            f"below the {MIN_REDUCTION:.0%} the phase gate requires"
        )

    async def test_the_saving_does_not_come_from_getting_it_wrong(
        self, unit_of_work_factory: Factory
    ) -> None:
        # The failure mode a speed number hides: a warm run that is faster because it
        # stopped checking. Both runs must still reach the goal.
        cold, warm = await benchmark(unit_of_work_factory)

        assert cold.is_correct
        assert warm.is_correct

    async def test_a_first_run_is_never_warm(self, unit_of_work_factory: Factory) -> None:
        # The baseline has to be a real baseline. If retrieval returned something on
        # the first run, every reduction measured afterwards would be meaningless.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        first = await execute_run(unit_of_work_factory, project_id, "run-first", at=NOW, warm=True)
        assert first.memory_items == 0
        assert not first.followed_memory


class TestMemoryIsNotFollowedBlindly:
    async def test_knowledge_from_another_version_is_checked_rather_than_followed(
        self, unit_of_work_factory: Factory
    ) -> None:
        # `revalidate` has to cost something, or the benchmark would be flattering
        # memory nobody has confirmed in this context.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        for index, run_id in enumerate(("run-1", "run-2")):
            await execute_run(
                unit_of_work_factory,
                project_id,
                run_id,
                at=NOW + timedelta(hours=index),
                warm=False,
            )

        moved_on = MemoryScope(
            project_id=project_id,
            environment_id="staging",
            origin=ORIGIN,
            app_version="3.0.0",
        )
        context = await retrieve_memory_context(
            unit_of_work_factory(),
            MemoryContextRequest(scope=moved_on),
            now=NOW + timedelta(hours=3),
        )
        planner = MemoryAwarePlanner(goal_url=GOAL_URL, decoys=DECOYS)
        while True:
            decision = await planner.next_action(
                PlanningRequest(
                    goal="create a record", observation="about:blank", memory=context.items
                )
            )
            if decision.action is None:
                break

        assert context.items, "the app version changed; memory should still be offered"
        assert planner.revalidated
        assert not planner.followed_memory
