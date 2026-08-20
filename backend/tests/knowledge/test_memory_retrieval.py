"""Retrieving memory from durable storage, against both implementations.

The query is what stands between stored knowledge and a planner's prompt, so these
tests are mostly about what it refuses to return.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.application.queries.memory_context import (
    MemoryContextRequest,
    retrieve_memory_context,
)
from agentic_qa.domain.knowledge.compatibility import Compatibility, MemoryScope
from agentic_qa.domain.knowledge.experience import (
    CandidateKind,
    KnowledgeExperienceCandidate,
    Provenance,
    Quality,
    Validity,
)
from tests.conftest import seed_project_with_default_policy

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)

Factory = Callable[[], UnitOfWork]


def sighting(
    project_id: str,
    *,
    run_id: str,
    summary: str = "reach checkout from the cart page",
    observed: bool = True,
    environment_id: str = "staging",
    app_version: str | None = "2.1.0",
    at: datetime = NOW,
) -> KnowledgeExperienceCandidate:
    return KnowledgeExperienceCandidate(
        candidate_id=f"cand-{uuid4()}",
        project_id=project_id,
        environment_id=environment_id,
        kind=CandidateKind.PLAYBOOK,
        observed=observed,
        model_derived=not observed,
        created_at=at,
        provenance=Provenance(source_run_id=run_id, evidence_set_id=f"ev-{run_id}"),
        validity=Validity(
            valid_from=at,
            origin="https://app.test",
            role="admin",
            app_version=app_version,
        ),
        payload={"summary": summary},
        quality=Quality(support_count=1, success_count=1, last_verified_at=at),
    )


def scope(project_id: str, **overrides: object) -> MemoryScope:
    fields: dict[str, object] = {
        "project_id": project_id,
        "environment_id": "staging",
        "origin": "https://app.test",
        "role": "admin",
        "app_version": "2.1.0",
    }
    fields.update(overrides)
    return MemoryScope(**fields)  # type: ignore[arg-type]


async def learn(factory: Factory, candidate: KnowledgeExperienceCandidate) -> None:
    async with factory() as uow:
        await uow.knowledge.merge(candidate)
        await uow.commit()


class TestAFirstRunFindsNothing:
    async def test_an_empty_project_is_cold(self, unit_of_work_factory: Factory) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)

        context = await retrieve_memory_context(
            unit_of_work_factory(), MemoryContextRequest(scope=scope(project_id)), now=NOW
        )

        assert context.is_cold
        # A cold run still gets a well-formed answer scoped to where it is looking.
        assert context.project_id == project_id
        assert context.environment_id == "staging"

    async def test_one_run_alone_does_not_make_memory(self, unit_of_work_factory: Factory) -> None:
        # Promotion needs a second independent run; until then the observation is
        # history, and history offered to a planner reads as advice.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await learn(unit_of_work_factory, sighting(project_id, run_id="run-1"))

        context = await retrieve_memory_context(
            unit_of_work_factory(), MemoryContextRequest(scope=scope(project_id)), now=NOW
        )
        assert context.is_cold


class TestASecondAgreeingRunMakesTheNextOneWarm:
    async def test_agreed_knowledge_is_offered_with_its_provenance(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await learn(unit_of_work_factory, sighting(project_id, run_id="run-1"))
        await learn(
            unit_of_work_factory,
            sighting(project_id, run_id="run-2", at=NOW + timedelta(hours=1)),
        )

        context = await retrieve_memory_context(
            unit_of_work_factory(),
            MemoryContextRequest(scope=scope(project_id)),
            now=NOW + timedelta(hours=2),
        )

        assert not context.is_cold
        item = context.items[0]
        assert item.summary == "reach checkout from the cart page"
        # Traceable back to the run that first observed it, and labelled as observed.
        assert item.source_run_id == "run-1"
        assert item.observed
        assert not item.model_derived

    async def test_a_new_app_version_makes_it_revalidate_rather_than_disappear(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await learn(unit_of_work_factory, sighting(project_id, run_id="run-1"))
        await learn(unit_of_work_factory, sighting(project_id, run_id="run-2"))

        context = await retrieve_memory_context(
            unit_of_work_factory(),
            MemoryContextRequest(scope=scope(project_id, app_version="3.0.0")),
            now=NOW,
        )

        assert not context.is_cold
        assert context.items[0].compatibility is Compatibility.REVALIDATE
        assert context.items[0].requires_revalidation


class TestNoRunEverSeesAnotherProjectsMemory:
    async def test_another_projects_knowledge_is_not_returned(
        self, unit_of_work_factory: Factory
    ) -> None:
        mine = await seed_project_with_default_policy(unit_of_work_factory, name="Mine")
        theirs = await seed_project_with_default_policy(unit_of_work_factory, name="Theirs")
        for run_id in ("run-1", "run-2"):
            await learn(unit_of_work_factory, sighting(theirs, run_id=run_id))

        context = await retrieve_memory_context(
            unit_of_work_factory(), MemoryContextRequest(scope=scope(mine)), now=NOW
        )
        assert context.is_cold

    async def test_another_environments_knowledge_is_not_returned(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        for run_id in ("run-1", "run-2"):
            await learn(
                unit_of_work_factory,
                sighting(project_id, run_id=run_id, environment_id="production"),
            )

        context = await retrieve_memory_context(
            unit_of_work_factory(), MemoryContextRequest(scope=scope(project_id)), now=NOW
        )
        assert context.is_cold


class TestTheContextStaysBounded:
    async def test_only_the_requested_number_of_items_comes_back(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        for index in range(6):
            summary = f"route {index} leads to the records page"
            for run_id in ("run-1", "run-2"):
                await learn(
                    unit_of_work_factory,
                    sighting(project_id, run_id=run_id, summary=summary),
                )

        context = await retrieve_memory_context(
            unit_of_work_factory(), MemoryContextRequest(scope=scope(project_id), limit=2), now=NOW
        )
        assert len(context.items) == 2
