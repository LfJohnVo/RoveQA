"""The deep-analysis activity at the Temporal boundary.

Three things a workflow depends on and no unit test of the command can show: the
activity heartbeats while a call that takes minutes is in flight, a broken store does
not turn a completed run into a failed workflow, and running it twice — which is what
Temporal does after a lost acknowledgement — costs nothing the second time.
"""

import asyncio
from collections.abc import AsyncIterator

import pytest
from temporalio import activity
from temporalio.testing import ActivityEnvironment

from agentic_qa.application.ports.deep_analysis import ClusterAnalysisRequest, ClusterHypothesis
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.bootstrap.container import Container
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult, FailureKind
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict
from agentic_qa.infrastructure.workflows.temporal.activities import RunActivities, _heartbeating
from agentic_qa.infrastructure.workflows.temporal.contracts import AnalyzeFailuresParams
from tests.fakes.repositories import InMemoryStore
from tests.fakes.unit_of_work import InMemoryUnitOfWork

HEARTBEAT_INTERVAL = 0.01
DEADLINE_SECONDS = 5.0


class CountingAnalyst:
    def __init__(self) -> None:
        self.calls = 0

    async def analyze(self, request: ClusterAnalysisRequest) -> ClusterHypothesis:
        self.calls += 1
        return ClusterHypothesis(
            cluster_id=request.cluster_id,
            probable_cause="the payment service rejects the order",
            recommended_check="post one order directly to the payment service",
        )


@pytest.fixture
async def store() -> AsyncIterator[InMemoryStore]:
    store = InMemoryStore()
    async with InMemoryUnitOfWork(store) as uow:
        await uow.projects.add(Project(project_id="proj-1", name="Checkout"))
        await uow.runs.add(
            Run(
                run_id="run-1",
                project_id="proj-1",
                status=RunStatus.COMPLETED,
                verdict=Verdict.FAILED,
            )
        )
        await uow.criterion_results.record(
            "run-1",
            [
                CriterionResult(
                    criterion_id="ac-checkout",
                    outcome=CriterionOutcome.NOT_MET,
                    observation="no confirmation appeared",
                    failure_kind=FailureKind.PRODUCT,
                )
            ],
        )
        await uow.commit()
    yield store


def activities(store: InMemoryStore, analyst: CountingAnalyst | None) -> RunActivities:
    return RunActivities(
        Container(unit_of_work=lambda: InMemoryUnitOfWork(store), deep_analyst=analyst)
    )


async def test_it_records_a_hypothesis_and_says_how_many(store: InMemoryStore) -> None:
    recorded = await ActivityEnvironment().run(
        activities(store, CountingAnalyst()).analyze_failures,
        AnalyzeFailuresParams(run_id="run-1"),
    )

    assert recorded == 1


async def test_a_retry_asks_the_model_nothing_and_records_nothing(store: InMemoryStore) -> None:
    analyst = CountingAnalyst()
    bound = activities(store, analyst)

    first = await ActivityEnvironment().run(
        bound.analyze_failures, AnalyzeFailuresParams(run_id="run-1")
    )
    replay = await ActivityEnvironment().run(
        bound.analyze_failures, AnalyzeFailuresParams(run_id="run-1")
    )

    assert (first, replay) == (1, 0)
    assert analyst.calls == 1


async def test_with_no_deep_analyst_it_still_stores_the_clusters(store: InMemoryStore) -> None:
    recorded = await ActivityEnvironment().run(
        activities(store, None).analyze_failures, AnalyzeFailuresParams(run_id="run-1")
    )

    assert recorded == 0
    async with InMemoryUnitOfWork(store) as uow:
        assert await uow.failure_clusters.list_for_project("proj-1", limit=10)


async def test_a_broken_store_does_not_fail_a_completed_run() -> None:
    """The verdict is already durable. A second reading of results that are already
    written must not be able to turn a finished run into a failed workflow."""

    def broken() -> UnitOfWork:
        raise RuntimeError("the database is down")

    bound = RunActivities(Container(unit_of_work=broken))

    assert (
        await ActivityEnvironment().run(
            bound.analyze_failures, AnalyzeFailuresParams(run_id="run-1")
        )
        == 0
    )


async def test_it_heartbeats_while_the_model_is_thinking() -> None:
    """Without this, Temporal cannot tell a ten-minute answer from a dead worker, and
    the only safe timeout would be one long enough to hide a crash for an hour."""
    beat = asyncio.Event()
    environment = ActivityEnvironment()
    environment.on_heartbeat = lambda *_: beat.set()

    @activity.defn(name="slow_work")
    async def slow_work() -> bool:
        async with _heartbeating(HEARTBEAT_INTERVAL):
            # Waits for the observable condition rather than for a fixed duration, and
            # fails loudly instead of hanging if no heartbeat ever arrives.
            await asyncio.wait_for(beat.wait(), timeout=DEADLINE_SECONDS)
        return beat.is_set()

    assert await environment.run(slow_work) is True


async def test_the_heartbeat_stops_when_the_work_does() -> None:
    # A task left running past its activity would keep heartbeating for work that
    # finished, which is a worse lie than not heartbeating at all.
    before = len(asyncio.all_tasks())

    @activity.defn(name="quick_work")
    async def quick_work() -> None:
        async with _heartbeating(HEARTBEAT_INTERVAL):
            pass

    await ActivityEnvironment().run(quick_work)

    assert len(asyncio.all_tasks()) <= before
