"""Durable knowledge, against both the in-memory double and PostgreSQL.

The suite is parametrized over both implementations on purpose: the folding rule
decides what a later run acts on, and a double that folded differently from the real
adapter would prove nothing about production.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from agentic_qa.application.commands.consolidate_experience import (
    ConsolidateExperienceCommand,
    consolidate_experience,
)
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.browser.evidence import EvidenceRef
from agentic_qa.domain.knowledge.experience import (
    CandidateKind,
    CandidateStatus,
    KnowledgeExperienceCandidate,
    Provenance,
    Quality,
    Validity,
)
from agentic_qa.domain.projects.environment import Environment
from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult
from agentic_qa.domain.runs.recovery import (
    BrowserRecoveryData,
    RecoveryPoint,
    RecoveryTrigger,
)
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict
from tests.conftest import seed_project_with_default_policy

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)

Factory = Callable[[], UnitOfWork]


def sighting(
    project_id: str,
    *,
    run_id: str,
    environment_id: str = "staging",
    criterion_id: str = "ac-1",
    observed: bool = True,
    at: datetime = NOW,
) -> KnowledgeExperienceCandidate:
    return KnowledgeExperienceCandidate(
        candidate_id=f"cand-{uuid4()}",
        project_id=project_id,
        environment_id=environment_id,
        kind=CandidateKind.ACCEPTANCE_FACT,
        observed=observed,
        model_derived=not observed,
        created_at=at,
        provenance=Provenance(source_run_id=run_id),
        validity=Validity(valid_from=at, origin="https://app.test"),
        payload={"criterion_id": criterion_id, "summary": "checkout reaches confirmation"},
        quality=Quality(support_count=1, success_count=1, last_verified_at=at),
    )


class TestAgreementAccumulates:
    async def test_two_runs_seeing_the_same_thing_make_one_promoted_fact(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)

        async with unit_of_work_factory() as uow:
            first = await uow.knowledge.merge(sighting(project_id, run_id="run-1"))
            await uow.commit()
        async with unit_of_work_factory() as uow:
            second = await uow.knowledge.merge(
                sighting(project_id, run_id="run-2", at=NOW + timedelta(hours=1))
            )
            await uow.commit()

        assert first.status is CandidateStatus.CANDIDATE
        assert second.status is CandidateStatus.PROMOTED
        assert second.quality.support_count == 2
        # One fact, not two rows: otherwise "how many runs agree" is unanswerable.
        assert second.candidate_id == first.candidate_id

        async with unit_of_work_factory() as uow:
            stored = await uow.knowledge.list_for_scope(
                project_id=project_id, environment_id="staging"
            )
        assert len(stored) == 1
        assert stored[0].quality.support_count == 2

    async def test_a_model_hypothesis_is_a_separate_fact_from_the_observation(
        self, unit_of_work_factory: Factory
    ) -> None:
        # Same criterion, same scope, different source. Merging them would let a guess
        # inherit the observation's support.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)

        async with unit_of_work_factory() as uow:
            await uow.knowledge.merge(sighting(project_id, run_id="run-1"))
            await uow.knowledge.merge(sighting(project_id, run_id="run-2", observed=False))
            await uow.commit()

        async with unit_of_work_factory() as uow:
            stored = await uow.knowledge.list_for_scope(
                project_id=project_id, environment_id="staging"
            )
        assert len(stored) == 2
        assert {candidate.model_derived for candidate in stored} == {True, False}
        assert all(candidate.quality.support_count == 1 for candidate in stored)


class TestScopeIsAFilterNotAnAfterthought:
    async def test_another_project_never_appears(self, unit_of_work_factory: Factory) -> None:
        mine = await seed_project_with_default_policy(unit_of_work_factory, name="Mine")
        theirs = await seed_project_with_default_policy(unit_of_work_factory, name="Theirs")

        async with unit_of_work_factory() as uow:
            await uow.knowledge.merge(sighting(mine, run_id="run-1"))
            await uow.knowledge.merge(sighting(theirs, run_id="run-2"))
            await uow.commit()

        async with unit_of_work_factory() as uow:
            visible = await uow.knowledge.list_for_scope(project_id=mine, environment_id="staging")
        assert [candidate.project_id for candidate in visible] == [mine]

    async def test_another_environment_never_appears(self, unit_of_work_factory: Factory) -> None:
        # Staging knowledge is not weaker production knowledge; it is knowledge about
        # a different deployment.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)

        async with unit_of_work_factory() as uow:
            await uow.knowledge.merge(sighting(project_id, run_id="run-1"))
            await uow.knowledge.merge(
                sighting(project_id, run_id="run-2", environment_id="production")
            )
            await uow.commit()

        async with unit_of_work_factory() as uow:
            visible = await uow.knowledge.list_for_scope(
                project_id=project_id, environment_id="production"
            )
        assert [candidate.environment_id for candidate in visible] == ["production"]

    async def test_only_the_requested_statuses_come_back(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)

        async with unit_of_work_factory() as uow:
            await uow.knowledge.merge(sighting(project_id, run_id="run-1"))
            await uow.knowledge.merge(sighting(project_id, run_id="run-2"))
            await uow.knowledge.merge(sighting(project_id, run_id="run-3", criterion_id="ac-2"))
            await uow.commit()

        async with unit_of_work_factory() as uow:
            actionable = await uow.knowledge.list_for_scope(
                project_id=project_id,
                environment_id="staging",
                statuses=[CandidateStatus.PROMOTED, CandidateStatus.TRUSTED],
            )
        assert [candidate.payload["criterion_id"] for candidate in actionable] == ["ac-1"]


class TestNothingIsLearnedOutsideACommit:
    async def test_a_rolled_back_transaction_leaves_no_knowledge(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)

        async with unit_of_work_factory() as uow:
            await uow.knowledge.merge(sighting(project_id, run_id="run-1"))
            # No commit: leaving the block must lose the write.

        async with unit_of_work_factory() as uow:
            stored = await uow.knowledge.list_for_scope(
                project_id=project_id, environment_id="staging"
            )
        assert stored == []


async def seed_finished_run(factory: Factory, project_id: str, run_id: str) -> None:
    """A completed run with a verified result, evidence and a safe point."""
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
                    criterion_id="ac-1",
                    outcome=CriterionOutcome.MET,
                    observation="the confirmation page appeared",
                    model_derived=False,
                )
            ],
        )
        await uow.artifacts.record(
            EvidenceRef(
                artifact_id=f"art-{run_id}",
                run_id=run_id,
                evidence_set_id=f"ev-{run_id}",
                kind="screenshot",
                relative_path=f"{run_id}/shot.png",
                sha256="0" * 64,
                size_bytes=12,
                captured_at=NOW,
            )
        )
        await uow.recovery_points.add(
            RecoveryPoint(
                recovery_point_id=f"rp-{run_id}",
                run_id=run_id,
                episode_index=0,
                trigger=RecoveryTrigger.EPISODE_CLOSED,
                graph_checkpoint_id=f"ck-{run_id}",
                browser=BrowserRecoveryData(url="https://app.test/orders/42"),
                created_at=NOW,
            )
        )
        await uow.commit()


class TestConsolidatingARunHappensOnce:
    async def test_it_learns_from_a_finished_run(self, unit_of_work_factory: Factory) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await seed_finished_run(unit_of_work_factory, project_id, "run-1")

        result = await consolidate_experience(
            unit_of_work_factory(), ConsolidateExperienceCommand(run_id="run-1"), now=NOW
        )

        assert not result.replayed
        kinds = {candidate.kind for candidate in result.candidates}
        assert kinds == {CandidateKind.ACCEPTANCE_FACT, CandidateKind.ROUTE}
        # Provenance came from the durable record, not from anything passed in.
        assert all(c.provenance.evidence_set_id == "ev-run-1" for c in result.candidates)

    async def test_a_retried_activity_does_not_double_the_support(
        self, unit_of_work_factory: Factory
    ) -> None:
        # This is the whole point of the idempotency record. Two supports from one run
        # is how a single flaky observation talks itself into being trusted.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await seed_finished_run(unit_of_work_factory, project_id, "run-1")

        command = ConsolidateExperienceCommand(run_id="run-1")
        await consolidate_experience(unit_of_work_factory(), command, now=NOW)
        replay = await consolidate_experience(
            unit_of_work_factory(), command, now=NOW + timedelta(hours=1)
        )

        assert replay.replayed
        async with unit_of_work_factory() as uow:
            stored = await uow.knowledge.list_for_scope(
                project_id=project_id, environment_id="staging"
            )
        assert stored
        assert all(candidate.quality.support_count == 1 for candidate in stored)
        assert all(candidate.status is CandidateStatus.CANDIDATE for candidate in stored)

    async def test_two_different_runs_do_reinforce_each_other(
        self, unit_of_work_factory: Factory
    ) -> None:
        # The counterpart of the test above: deduplication must not be so eager that
        # genuine agreement stops counting.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await seed_finished_run(unit_of_work_factory, project_id, "run-1")
        await seed_finished_run(unit_of_work_factory, project_id, "run-2")

        await consolidate_experience(
            unit_of_work_factory(), ConsolidateExperienceCommand(run_id="run-1"), now=NOW
        )
        await consolidate_experience(
            unit_of_work_factory(),
            ConsolidateExperienceCommand(run_id="run-2"),
            now=NOW + timedelta(hours=1),
        )

        async with unit_of_work_factory() as uow:
            stored = await uow.knowledge.list_for_scope(
                project_id=project_id, environment_id="staging"
            )
        assert all(candidate.quality.support_count == 2 for candidate in stored)
        assert all(candidate.status is CandidateStatus.PROMOTED for candidate in stored)

    async def test_an_unknown_run_fails_typed(self, unit_of_work_factory: Factory) -> None:
        from agentic_qa.application.errors import NotFoundError

        with pytest.raises(NotFoundError):
            await consolidate_experience(
                unit_of_work_factory(), ConsolidateExperienceCommand(run_id="nope"), now=NOW
            )
