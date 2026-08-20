"""Recording outcomes about memory, against both the double and PostgreSQL.

The durability question these answer: after a lost acknowledgement, does one run's
outcome get counted once or twice? Reliability is a count of *independent* outcomes,
so double counting is not a rounding error — it is how one flaky observation talks
itself into being trusted.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from agentic_qa.application.commands.record_memory_feedback import (
    RecordMemoryFeedbackCommand,
    record_memory_feedback,
)
from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.knowledge import GraphSyncRecord, GraphSyncState
from agentic_qa.application.ports.unit_of_work import UnitOfWork
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

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(hours=1)

Factory = Callable[[], UnitOfWork]


async def seed_playbook(
    factory: Factory,
    project_id: str,
    *,
    run_id: str = "run-1",
    status: CandidateStatus = CandidateStatus.PROMOTED,
) -> KnowledgeExperienceCandidate:
    """A run plus one piece of knowledge a later run could act on."""
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
        # Distinct per run: two seeds of the *same* fact would correctly merge into
        # one candidate, which is not what a test about two candidates wants.
        payload={"summary": f"log in through the header form ({run_id})"},
        status=status,
        quality=Quality(support_count=2, success_count=2, last_verified_at=NOW),
    )
    async with factory() as uow:
        await uow.runs.add(
            Run(
                run_id=run_id,
                project_id=project_id,
                status=RunStatus.COMPLETED,
                verdict=Verdict.PASSED,
            )
        )
        stored = await uow.knowledge.merge(candidate)
        await uow.commit()
    return stored


class TestOneOutcomeIsCountedOnce:
    async def test_a_verified_success_moves_reliability(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        candidate = await seed_playbook(unit_of_work_factory, project_id)

        result = await record_memory_feedback(
            unit_of_work_factory(),
            RecordMemoryFeedbackCommand(
                candidate_id=candidate.candidate_id,
                run_id="run-1",
                kind=FeedbackKind.SUCCESS,
                episode_id="ep-0",
            ),
            now=LATER,
        )

        assert result.recorded
        assert result.candidate.quality.success_count == 3
        async with unit_of_work_factory() as uow:
            stored = await uow.knowledge.get(candidate.candidate_id)
        assert stored is not None
        # Committed, not just returned: a reliability number that only exists in a
        # response is a number the next run cannot see.
        assert stored.quality.success_count == 3

    async def test_a_retried_activity_does_not_vote_twice(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        candidate = await seed_playbook(unit_of_work_factory, project_id)
        command = RecordMemoryFeedbackCommand(
            candidate_id=candidate.candidate_id,
            run_id="run-1",
            kind=FeedbackKind.SUCCESS,
            episode_id="ep-0",
        )

        first = await record_memory_feedback(unit_of_work_factory(), command, now=LATER)
        replay = await record_memory_feedback(
            unit_of_work_factory(), command, now=LATER + timedelta(minutes=5)
        )

        assert first.recorded
        assert not replay.recorded
        assert replay.candidate.quality.success_count == first.candidate.quality.success_count

    async def test_two_episodes_are_two_outcomes(self, unit_of_work_factory: Factory) -> None:
        # The counterpart: deduplication must not be so eager that genuine reuse
        # stops counting.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        candidate = await seed_playbook(unit_of_work_factory, project_id)

        for episode in ("ep-0", "ep-1"):
            await record_memory_feedback(
                unit_of_work_factory(),
                RecordMemoryFeedbackCommand(
                    candidate_id=candidate.candidate_id,
                    run_id="run-1",
                    kind=FeedbackKind.SUCCESS,
                    episode_id=episode,
                ),
                now=LATER,
            )

        async with unit_of_work_factory() as uow:
            stored = await uow.knowledge.get(candidate.candidate_id)
            trail = await uow.memory_feedback.list_for_candidate(candidate.candidate_id)
        assert stored is not None
        assert stored.quality.success_count == 4
        assert len(trail) == 2


class TestTheEvidenceTrailSurvives:
    async def test_a_contradiction_invalidates_and_stays_auditable(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        candidate = await seed_playbook(unit_of_work_factory, project_id)

        result = await record_memory_feedback(
            unit_of_work_factory(),
            RecordMemoryFeedbackCommand(
                candidate_id=candidate.candidate_id,
                run_id="run-1",
                kind=FeedbackKind.CONTRADICTION,
                detail="the header form no longer exists",
            ),
            now=LATER,
        )

        assert result.candidate.status is CandidateStatus.INVALIDATED
        async with unit_of_work_factory() as uow:
            trail = await uow.memory_feedback.list_for_candidate(candidate.candidate_id)
        # Why something stopped being true is worth as much as the fact was.
        assert [item.kind for item in trail] == [FeedbackKind.CONTRADICTION]
        assert trail[0].detail == "the header form no longer exists"

    async def test_a_model_conclusion_is_stored_without_moving_the_numbers(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        candidate = await seed_playbook(unit_of_work_factory, project_id)

        result = await record_memory_feedback(
            unit_of_work_factory(),
            RecordMemoryFeedbackCommand(
                candidate_id=candidate.candidate_id,
                run_id="run-1",
                kind=FeedbackKind.CONTRADICTION,
                observed=False,
            ),
            now=LATER,
        )

        assert result.recorded
        assert result.candidate.status is CandidateStatus.PROMOTED
        assert result.candidate.quality.contradiction_count == 0
        async with unit_of_work_factory() as uow:
            trail = await uow.memory_feedback.list_for_candidate(candidate.candidate_id)
        # Visible to a human — a model repeatedly doubting a fact is worth seeing —
        # but not counted.
        assert len(trail) == 1
        assert trail[0].observed is False

    async def test_feedback_about_unknown_knowledge_fails_typed(
        self, unit_of_work_factory: Factory
    ) -> None:
        await seed_project_with_default_policy(unit_of_work_factory)
        with pytest.raises(NotFoundError):
            await record_memory_feedback(
                unit_of_work_factory(),
                RecordMemoryFeedbackCommand(
                    candidate_id="cand-nope", run_id="run-1", kind=FeedbackKind.SUCCESS
                ),
                now=LATER,
            )


class TestGraphSyncIsSeparateFromBelief:
    async def test_a_failed_graph_write_leaves_the_knowledge_untouched(
        self, unit_of_work_factory: Factory
    ) -> None:
        # The graph being down says nothing about whether the knowledge is true.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        candidate = await seed_playbook(unit_of_work_factory, project_id)

        async with unit_of_work_factory() as uow:
            await uow.graph_sync.mark(
                GraphSyncRecord(
                    candidate_id=candidate.candidate_id,
                    state=GraphSyncState.FAILED,
                    attempts=3,
                    last_error="FalkorDB unreachable",
                )
            )
            await uow.commit()

        async with unit_of_work_factory() as uow:
            stored = await uow.knowledge.get(candidate.candidate_id)
        assert stored is not None
        assert stored.status is CandidateStatus.PROMOTED

    async def test_the_backlog_names_what_the_graph_is_missing(
        self, unit_of_work_factory: Factory
    ) -> None:
        # This is what makes losing FalkorDB survivable: the projection is rebuilt
        # from PostgreSQL rather than by re-running anybody's tests.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        pending = await seed_playbook(unit_of_work_factory, project_id, run_id="run-1")
        synced = await seed_playbook(unit_of_work_factory, project_id, run_id="run-2")

        async with unit_of_work_factory() as uow:
            await uow.graph_sync.mark(GraphSyncRecord(candidate_id=pending.candidate_id))
            await uow.graph_sync.mark(
                GraphSyncRecord(
                    candidate_id=synced.candidate_id,
                    state=GraphSyncState.SYNCED,
                    graph_node_id="node-1",
                    graph_schema_version="v1",
                    synced_at=LATER,
                )
            )
            await uow.commit()

        async with unit_of_work_factory() as uow:
            backlog = await uow.graph_sync.list_pending()
            counts = await uow.graph_sync.count_by_state()
        assert [record.candidate_id for record in backlog] == [pending.candidate_id]
        assert counts[GraphSyncState.PENDING] == 1
        assert counts[GraphSyncState.SYNCED] == 1

    async def test_a_failed_write_stays_in_the_backlog(self, unit_of_work_factory: Factory) -> None:
        # A write that errored is still missing from the graph; leaving it out would
        # make a rebuild quietly incomplete.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        candidate = await seed_playbook(unit_of_work_factory, project_id)

        async with unit_of_work_factory() as uow:
            await uow.graph_sync.mark(
                GraphSyncRecord(candidate_id=candidate.candidate_id, state=GraphSyncState.FAILED)
            )
            await uow.commit()

        async with unit_of_work_factory() as uow:
            backlog = await uow.graph_sync.list_pending()
        assert [record.candidate_id for record in backlog] == [candidate.candidate_id]

    async def test_marking_the_same_candidate_twice_updates_rather_than_duplicates(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        candidate = await seed_playbook(unit_of_work_factory, project_id)

        async with unit_of_work_factory() as uow:
            await uow.graph_sync.mark(GraphSyncRecord(candidate_id=candidate.candidate_id))
            await uow.graph_sync.mark(
                GraphSyncRecord(
                    candidate_id=candidate.candidate_id,
                    state=GraphSyncState.SYNCED,
                    graph_node_id="node-1",
                    synced_at=LATER,
                )
            )
            await uow.commit()

        async with unit_of_work_factory() as uow:
            record = await uow.graph_sync.get(candidate.candidate_id)
            counts = await uow.graph_sync.count_by_state()
        assert record is not None
        assert record.state is GraphSyncState.SYNCED
        assert counts[GraphSyncState.SYNCED] == 1
        assert counts[GraphSyncState.PENDING] == 0
