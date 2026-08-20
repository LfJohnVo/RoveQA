"""Keeping the projection in step, and surviving it being gone.

The properties worth defending here are all about the graph *not* working. A run must
keep its correctness, the backlog must keep the work, and a wiped FalkorDB must be
rebuildable from PostgreSQL without re-running a single test.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from agentic_qa.application.commands.record_memory_feedback import (
    RecordMemoryFeedbackCommand,
    record_memory_feedback,
)
from agentic_qa.application.commands.sync_knowledge_graph import (
    MAX_SYNC_ATTEMPTS,
    rebuild_project,
    sync_pending,
)
from agentic_qa.application.ports.knowledge import GraphSyncState
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.application.queries.memory_status import memory_status
from agentic_qa.domain.knowledge.experience import (
    CandidateKind,
    CandidateStatus,
    KnowledgeExperienceCandidate,
    Provenance,
    Quality,
    Validity,
)
from agentic_qa.domain.knowledge.feedback import FeedbackKind
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict
from tests.conftest import seed_project_with_default_policy
from tests.fakes.graph import InMemoryGraphMemory, UnavailableGraph

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)

Factory = Callable[[], UnitOfWork]


async def promoted_knowledge(
    factory: Factory,
    project_id: str,
    *,
    summary: str = "the records page is reachable from the header nav",
    run_id: str = "run-1",
) -> KnowledgeExperienceCandidate:
    """Knowledge two runs already agreed on, queued for the projection."""
    candidate = KnowledgeExperienceCandidate(
        candidate_id=f"cand-{uuid4()}",
        project_id=project_id,
        environment_id="staging",
        kind=CandidateKind.PLAYBOOK,
        observed=True,
        model_derived=False,
        created_at=NOW,
        provenance=Provenance(source_run_id=run_id),
        validity=Validity(valid_from=NOW),
        payload={"summary": summary},
        status=CandidateStatus.PROMOTED,
        quality=Quality(support_count=2, success_count=2, last_verified_at=NOW),
    )
    async with factory() as uow:
        if await uow.runs.get(run_id) is None:
            await uow.runs.add(
                Run(
                    run_id=run_id,
                    project_id=project_id,
                    status=RunStatus.COMPLETED,
                    verdict=Verdict.PASSED,
                )
            )
        stored = await uow.knowledge.merge(candidate)
        from agentic_qa.application.commands.sync_knowledge_graph import enqueue_for_sync

        await enqueue_for_sync(uow, stored.candidate_id)
        await uow.commit()
    return stored


class TestTheProjectionFollowsDurableKnowledge:
    async def test_promoted_knowledge_reaches_the_graph(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        candidate = await promoted_knowledge(unit_of_work_factory, project_id)
        graph = InMemoryGraphMemory()

        report = await sync_pending(unit_of_work_factory, graph, now=NOW)

        assert report.materialized == 1
        assert candidate.candidate_id in graph.nodes
        async with unit_of_work_factory() as uow:
            record = await uow.graph_sync.get(candidate.candidate_id)
        assert record is not None
        assert record.state is GraphSyncState.SYNCED
        assert record.graph_node_id == f"node:{candidate.candidate_id}"

    async def test_syncing_twice_updates_one_node(self, unit_of_work_factory: Factory) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await promoted_knowledge(unit_of_work_factory, project_id)
        graph = InMemoryGraphMemory()

        await sync_pending(unit_of_work_factory, graph, now=NOW)
        second = await sync_pending(unit_of_work_factory, graph, now=NOW)

        # Nothing left to do, and the graph did not grow.
        assert second.materialized == 0
        assert len(graph.nodes) == 1

    async def test_withdrawn_knowledge_is_removed_from_the_graph(
        self, unit_of_work_factory: Factory
    ) -> None:
        # Leaving it would let traversal keep surfacing something the durable side
        # has retracted — memory that outlives the evidence against it.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        candidate = await promoted_knowledge(unit_of_work_factory, project_id)
        graph = InMemoryGraphMemory()
        await sync_pending(unit_of_work_factory, graph, now=NOW)
        assert candidate.candidate_id in graph.nodes

        await record_memory_feedback(
            unit_of_work_factory(),
            RecordMemoryFeedbackCommand(
                candidate_id=candidate.candidate_id,
                run_id="run-1",
                kind=FeedbackKind.CONTRADICTION,
            ),
            now=NOW + timedelta(hours=1),
        )
        report = await sync_pending(unit_of_work_factory, graph, now=NOW + timedelta(hours=1))

        assert report.forgotten == 1
        assert candidate.candidate_id not in graph.nodes

    async def test_unpromoted_knowledge_is_never_projected(
        self, unit_of_work_factory: Factory
    ) -> None:
        # The graph holds what a planner may act on. Projecting the rest would fill it
        # with things retrieval has to filter out afterwards.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        candidate = await promoted_knowledge(unit_of_work_factory, project_id)
        async with unit_of_work_factory() as uow:
            stored = await uow.knowledge.get(candidate.candidate_id)
            assert stored is not None
            await uow.knowledge.save(stored.demoted())
            await uow.commit()

        graph = InMemoryGraphMemory()
        report = await sync_pending(unit_of_work_factory, graph, now=NOW)

        assert report.materialized == 0
        assert graph.nodes == {}


class TestAnOutageCostsFreshnessAndNothingElse:
    async def test_the_durable_side_is_untouched(self, unit_of_work_factory: Factory) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        candidate = await promoted_knowledge(unit_of_work_factory, project_id)

        report = await sync_pending(unit_of_work_factory, UnavailableGraph(), now=NOW)

        assert report.unavailable
        async with unit_of_work_factory() as uow:
            stored = await uow.knowledge.get(candidate.candidate_id)
        assert stored is not None
        # Still promoted: the graph being down says nothing about whether the
        # knowledge is true.
        assert stored.status is CandidateStatus.PROMOTED

    async def test_the_work_stays_in_the_backlog(self, unit_of_work_factory: Factory) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        candidate = await promoted_knowledge(unit_of_work_factory, project_id)

        await sync_pending(unit_of_work_factory, UnavailableGraph(), now=NOW)

        async with unit_of_work_factory() as uow:
            backlog = await uow.graph_sync.list_pending()
        assert [record.candidate_id for record in backlog] == [candidate.candidate_id]

    async def test_the_store_coming_back_drains_the_backlog(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        candidate = await promoted_knowledge(unit_of_work_factory, project_id)
        graph = InMemoryGraphMemory(available=False)

        await sync_pending(unit_of_work_factory, graph, now=NOW)
        graph.available = True
        report = await sync_pending(unit_of_work_factory, graph, now=NOW + timedelta(minutes=5))

        assert report.materialized == 1
        assert candidate.candidate_id in graph.nodes

    async def test_an_entry_stops_being_retried_forever(
        self, unit_of_work_factory: Factory
    ) -> None:
        # One poisoned candidate must not become a queue that never drains and a
        # status that never goes green.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await promoted_knowledge(unit_of_work_factory, project_id)
        graph = InMemoryGraphMemory(available=False)

        for _ in range(MAX_SYNC_ATTEMPTS + 2):
            await sync_pending(unit_of_work_factory, graph, now=NOW)

        async with unit_of_work_factory() as uow:
            backlog = await uow.graph_sync.list_pending()
        assert backlog[0].attempts == MAX_SYNC_ATTEMPTS

    async def test_status_still_answers_while_the_graph_is_down(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await promoted_knowledge(unit_of_work_factory, project_id)

        status = await memory_status(
            unit_of_work_factory(),
            UnavailableGraph(),
            project_id=project_id,
            environment_id="staging",
        )

        assert not status.graph_available
        assert status.graph_is_behind
        # And the number that survives losing the graph entirely.
        assert status.actionable_candidates == 1


class TestLosingFalkorDBIsRecoverable:
    async def test_a_wiped_graph_is_rebuilt_from_postgresql(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        first = await promoted_knowledge(unit_of_work_factory, project_id, run_id="run-1")
        second = await promoted_knowledge(
            unit_of_work_factory,
            project_id,
            summary="checkout is reachable from the cart",
            run_id="run-2",
        )
        graph = InMemoryGraphMemory()
        await sync_pending(unit_of_work_factory, graph, now=NOW)
        assert len(graph.nodes) == 2

        graph.nodes.clear()  # FalkorDB is gone.

        report = await rebuild_project(
            unit_of_work_factory,
            graph,
            project_id=project_id,
            environment_id="staging",
            now=NOW + timedelta(days=1),
        )

        assert report.materialized == 2
        assert {first.candidate_id, second.candidate_id} == set(graph.nodes)

    async def test_a_rebuild_does_not_restore_withdrawn_knowledge(
        self, unit_of_work_factory: Factory
    ) -> None:
        # The rebuild reads what PostgreSQL says now, not what the graph used to hold.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        kept = await promoted_knowledge(unit_of_work_factory, project_id, run_id="run-1")
        withdrawn = await promoted_knowledge(
            unit_of_work_factory,
            project_id,
            summary="a route that no longer exists",
            run_id="run-2",
        )
        async with unit_of_work_factory() as uow:
            stored = await uow.knowledge.get(withdrawn.candidate_id)
            assert stored is not None
            await uow.knowledge.save(stored.invalidated())
            await uow.commit()

        graph = InMemoryGraphMemory()
        await rebuild_project(
            unit_of_work_factory,
            graph,
            project_id=project_id,
            environment_id="staging",
            now=NOW,
        )

        assert set(graph.nodes) == {kept.candidate_id}

    async def test_a_rebuild_does_not_reach_another_project(
        self, unit_of_work_factory: Factory
    ) -> None:
        mine = await seed_project_with_default_policy(unit_of_work_factory, name="Mine")
        theirs = await seed_project_with_default_policy(unit_of_work_factory, name="Theirs")
        await promoted_knowledge(unit_of_work_factory, mine, run_id="run-1")
        foreign = await promoted_knowledge(unit_of_work_factory, theirs, run_id="run-2")
        graph = InMemoryGraphMemory()
        await sync_pending(unit_of_work_factory, graph, now=NOW)

        await rebuild_project(
            unit_of_work_factory,
            graph,
            project_id=mine,
            environment_id="staging",
            now=NOW,
        )

        # Rebuilding one project must not clear or duplicate another's projection.
        assert foreign.candidate_id in graph.nodes
