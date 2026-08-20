"""Memory that a later run can disprove.

The lifecycle end to end, against both implementations: two agreeing runs make a fact
a planner will act on, and one deterministic disagreement withdraws it. Without the
second half, memory only ever grows and the agent keeps acting on things that stopped
being true.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from agentic_qa.application.commands.consolidate_experience import (
    ConsolidateExperienceCommand,
    consolidate_experience,
)
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.application.queries.memory_context import (
    MemoryContextRequest,
    retrieve_memory_context,
)
from agentic_qa.domain.knowledge.compatibility import MemoryScope
from agentic_qa.domain.knowledge.experience import CandidateKind, CandidateStatus
from agentic_qa.domain.knowledge.feedback import FeedbackKind
from agentic_qa.domain.projects.environment import Environment
from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult, FailureKind
from agentic_qa.domain.runs.recovery import (
    BrowserRecoveryData,
    RecoveryPoint,
    RecoveryTrigger,
)
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict
from tests.conftest import seed_project_with_default_policy

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)

Factory = Callable[[], UnitOfWork]


async def finished_run(
    factory: Factory,
    project_id: str,
    run_id: str,
    *,
    met: bool,
    at: datetime,
) -> None:
    """A completed run that checked one criterion deterministically."""
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
                verdict=Verdict.PASSED if met else Verdict.FAILED,
                environment_id="staging",
            )
        )
        await uow.criterion_results.record(
            run_id,
            [
                CriterionResult(
                    criterion_id="ac-checkout",
                    outcome=CriterionOutcome.MET if met else CriterionOutcome.NOT_MET,
                    observation="confirmation shown" if met else "no confirmation",
                    model_derived=False,
                    failure_kind=None if met else FailureKind.PRODUCT,
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
                browser=BrowserRecoveryData(url="https://app.test/checkout"),
                created_at=at,
            )
        )
        await uow.commit()


async def consolidate(factory: Factory, run_id: str, at: datetime) -> object:
    return await consolidate_experience(
        factory(), ConsolidateExperienceCommand(run_id=run_id), now=at
    )


def scope(project_id: str) -> MemoryScope:
    return MemoryScope(project_id=project_id, environment_id="staging", origin="https://app.test")


class TestTwoAgreeingRunsMakeMemoryTheNextRunCanUse:
    async def test_the_third_run_starts_warm(self, unit_of_work_factory: Factory) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await finished_run(unit_of_work_factory, project_id, "run-1", met=True, at=NOW)
        await consolidate(unit_of_work_factory, "run-1", NOW)

        cold = await retrieve_memory_context(
            unit_of_work_factory(), MemoryContextRequest(scope=scope(project_id)), now=NOW
        )
        assert cold.is_cold, "one run is a coincidence, not knowledge"

        await finished_run(
            unit_of_work_factory, project_id, "run-2", met=True, at=NOW + timedelta(hours=1)
        )
        await consolidate(unit_of_work_factory, "run-2", NOW + timedelta(hours=1))

        warm = await retrieve_memory_context(
            unit_of_work_factory(),
            MemoryContextRequest(scope=scope(project_id)),
            now=NOW + timedelta(hours=2),
        )

        assert not warm.is_cold
        kinds = {item.kind for item in warm.items}
        assert CandidateKind.ACCEPTANCE_FACT.value in kinds
        assert all(item.observed for item in warm.items)


class TestOneDeterministicDisagreementWithdrawsIt:
    async def test_a_failing_run_invalidates_the_remembered_fact(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        for index, run_id in enumerate(("run-1", "run-2")):
            at = NOW + timedelta(hours=index)
            await finished_run(unit_of_work_factory, project_id, run_id, met=True, at=at)
            await consolidate(unit_of_work_factory, run_id, at)

        # The application regresses: the same criterion now fails a deterministic check.
        broken_at = NOW + timedelta(hours=5)
        await finished_run(unit_of_work_factory, project_id, "run-3", met=False, at=broken_at)
        result = await consolidate(unit_of_work_factory, "run-3", broken_at)

        withdrawn = result.contradicted  # type: ignore[attr-defined]
        assert [item.kind for item in withdrawn] == [CandidateKind.ACCEPTANCE_FACT]
        assert withdrawn[0].status is CandidateStatus.INVALIDATED

        context = await retrieve_memory_context(
            unit_of_work_factory(), MemoryContextRequest(scope=scope(project_id)), now=broken_at
        )
        offered = {item.kind for item in context.items}
        assert CandidateKind.ACCEPTANCE_FACT.value not in offered

    async def test_why_it_stopped_being_true_stays_on_the_record(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        for index, run_id in enumerate(("run-1", "run-2")):
            at = NOW + timedelta(hours=index)
            await finished_run(unit_of_work_factory, project_id, run_id, met=True, at=at)
            await consolidate(unit_of_work_factory, run_id, at)

        broken_at = NOW + timedelta(hours=5)
        await finished_run(unit_of_work_factory, project_id, "run-3", met=False, at=broken_at)
        result = await consolidate(unit_of_work_factory, "run-3", broken_at)

        candidate_id = result.contradicted[0].candidate_id  # type: ignore[attr-defined]
        async with unit_of_work_factory() as uow:
            trail = await uow.memory_feedback.list_for_candidate(candidate_id)

        assert [item.kind for item in trail] == [FeedbackKind.CONTRADICTION]
        # Auditable: which run disproved it, and that the evidence was deterministic.
        assert trail[0].run_id == "run-3"
        assert trail[0].observed

    async def test_the_regression_itself_becomes_knowledge(
        self, unit_of_work_factory: Factory
    ) -> None:
        # The failure is not just the end of a fact; it is a fact of its own, and two
        # runs seeing it should make it something the agent can anticipate.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        for index, run_id in enumerate(("run-1", "run-2")):
            at = NOW + timedelta(hours=index)
            await finished_run(unit_of_work_factory, project_id, run_id, met=False, at=at)
            await consolidate(unit_of_work_factory, run_id, at)

        context = await retrieve_memory_context(
            unit_of_work_factory(),
            MemoryContextRequest(scope=scope(project_id)),
            now=NOW + timedelta(hours=3),
        )
        assert CandidateKind.FAILURE_SIGNATURE.value in {item.kind for item in context.items}


class TestOneRunIsCountedOnce:
    async def test_consolidating_twice_does_not_contradict_twice(
        self, unit_of_work_factory: Factory
    ) -> None:
        # A retried activity must not sink a candidate's reliability for one fault.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        for index, run_id in enumerate(("run-1", "run-2")):
            at = NOW + timedelta(hours=index)
            await finished_run(unit_of_work_factory, project_id, run_id, met=True, at=at)
            await consolidate(unit_of_work_factory, run_id, at)

        broken_at = NOW + timedelta(hours=5)
        await finished_run(unit_of_work_factory, project_id, "run-3", met=False, at=broken_at)
        first = await consolidate(unit_of_work_factory, "run-3", broken_at)
        replay = await consolidate(unit_of_work_factory, "run-3", broken_at + timedelta(minutes=1))

        assert replay.replayed  # type: ignore[attr-defined]
        candidate_id = first.contradicted[0].candidate_id  # type: ignore[attr-defined]
        async with unit_of_work_factory() as uow:
            stored = await uow.knowledge.get(candidate_id)
            trail = await uow.memory_feedback.list_for_candidate(candidate_id)
        assert stored is not None
        assert stored.quality.contradiction_count == 1
        assert len(trail) == 1
