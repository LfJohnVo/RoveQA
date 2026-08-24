"""The scheduling endpoints over real HTTP.

What matters here is not that a POST returns 201. It is that a schedule cannot be
created for a project that does not exist, cannot be paused or deleted from a project
that does not own it, and that a process with no Temporal connection says so instead of
returning a 201 for a schedule nobody stored — which would be believed until the night
it did not run.
"""

from collections.abc import AsyncIterator

import httpx
import pytest

from agentic_qa.application.ports.schedules import RunSchedule
from agentic_qa.bootstrap.container import Container
from agentic_qa.domain.projects.project import Project
from tests.fakes.repositories import InMemoryStore
from tests.fakes.schedules import InMemoryScheduleGateway
from tests.fakes.unit_of_work import InMemoryUnitOfWork
from tests.http.test_api_contract import asgi_client, authorise_for

SCHEDULES = "/api/v1/projects/proj-1/schedules"
NIGHTLY = {"schedule_id": "nightly", "cron": "0 2 * * *", "plan_id": "plan-1"}


def client_for(container: Container) -> httpx.AsyncClient:
    """The shared helper, so the client carries its container and can mint a token."""
    return asgi_client(container)


@pytest.fixture
async def store() -> InMemoryStore:
    store = InMemoryStore()
    async with InMemoryUnitOfWork(store) as uow:
        await uow.projects.add(Project(project_id="proj-1", name="Checkout"))
        await uow.projects.add(Project(project_id="proj-2", name="Other"))
        await uow.commit()
    return store


@pytest.fixture
def gateway() -> InMemoryScheduleGateway:
    return InMemoryScheduleGateway()


@pytest.fixture
async def client(
    store: InMemoryStore, gateway: InMemoryScheduleGateway
) -> AsyncIterator[httpx.AsyncClient]:
    container = Container(unit_of_work=lambda: InMemoryUnitOfWork(store), schedules=gateway)
    async with client_for(container) as client:
        # Authenticated like any real caller. That every route refuses *without* a
        # token is proved exhaustively in `test_every_route_is_guarded.py`; these
        # suites are about what the endpoints do once you are through the door.
        await authorise_for(client, "proj-1")
        yield client


class TestCreating:
    async def test_a_schedule_is_created_and_echoed_back(self, client: httpx.AsyncClient) -> None:
        response = await client.post(SCHEDULES, json=NIGHTLY)

        assert response.status_code == 201
        body = response.json()
        assert body["schedule_id"] == "nightly"
        assert body["project_id"] == "proj-1"
        assert body["cron"] == "0 2 * * *"
        assert body["paused"] is False

    async def test_creating_the_same_schedule_twice_is_a_conflict(
        self, client: httpx.AsyncClient
    ) -> None:
        # Not a second nightly regression. The id is the caller's, so a retried create
        # after a lost response finds its own schedule rather than making another.
        await client.post(SCHEDULES, json=NIGHTLY)

        assert (await client.post(SCHEDULES, json=NIGHTLY)).status_code == 409

    async def test_a_cron_nobody_can_act_on_is_refused(self, client: httpx.AsyncClient) -> None:
        # Refused now, not at the first firing: a schedule that silently never runs is
        # indistinguishable from one that works until someone checks weeks later.
        response = await client.post(SCHEDULES, json={**NIGHTLY, "cron": "nightly please"})

        assert response.status_code == 422

    async def test_an_unknown_project_cannot_be_scheduled(self, client: httpx.AsyncClient) -> None:
        # A token covers one project, so a path naming another is refused before the
        # handler runs. `403` rather than the old `404` — and the stronger answer: the
        # caller learns nothing about whether `ghost` exists.
        assert (
            await client.post("/api/v1/projects/ghost/schedules", json=NIGHTLY)
        ).status_code == 403


class TestOwnership:
    async def test_listing_shows_only_this_project(self, client: httpx.AsyncClient) -> None:
        await client.post(SCHEDULES, json=NIGHTLY)
        await client.post(
            "/api/v1/projects/proj-2/schedules", json={**NIGHTLY, "schedule_id": "other"}
        )

        body = (await client.get(SCHEDULES)).json()

        assert [item["schedule_id"] for item in body["schedules"]] == ["nightly"]

    async def test_another_project_cannot_pause_this_one(self, client: httpx.AsyncClient) -> None:
        # Schedule ids share one namespace in Temporal, so without the ownership check
        # a caller could pause someone else's nightly regression by guessing its name.
        await client.post(SCHEDULES, json=NIGHTLY)

        response = await client.post("/api/v1/projects/proj-2/schedules/nightly/pause")

        # Refused by the token now, before the handler's ownership check ever runs. Both
        # guards are real and this asserts the outer one; the handler's own check is what
        # protects a caller who legitimately holds tokens for both projects.
        assert response.status_code == 403

    async def test_another_project_cannot_delete_this_one(
        self, client: httpx.AsyncClient, gateway: InMemoryScheduleGateway
    ) -> None:
        await client.post(SCHEDULES, json=NIGHTLY)

        # Refused by the token, and the schedule is still there — which is the half
        # that matters: a refusal that deleted something first would be no refusal.
        assert (await client.delete("/api/v1/projects/proj-2/schedules/nightly")).status_code == 403
        assert await gateway.get("nightly") is not None


class TestPausing:
    async def test_pausing_keeps_the_schedule_and_its_cron(self, client: httpx.AsyncClient) -> None:
        # What a team does during a deploy freeze. Deleting instead loses the cron
        # expression and whoever wrote it.
        await client.post(SCHEDULES, json=NIGHTLY)

        body = (await client.post(f"{SCHEDULES}/nightly/pause")).json()

        assert body["paused"] is True
        assert body["cron"] == "0 2 * * *"

    async def test_resuming_puts_it_back(self, client: httpx.AsyncClient) -> None:
        await client.post(SCHEDULES, json=NIGHTLY)
        await client.post(f"{SCHEDULES}/nightly/pause")

        assert (await client.post(f"{SCHEDULES}/nightly/resume")).json()["paused"] is False

    async def test_pausing_something_that_is_not_there_is_a_404(
        self, client: httpx.AsyncClient
    ) -> None:
        assert (await client.post(f"{SCHEDULES}/ghost/pause")).status_code == 404


class TestDeleting:
    async def test_it_is_gone_afterwards(
        self, client: httpx.AsyncClient, gateway: InMemoryScheduleGateway
    ) -> None:
        await client.post(SCHEDULES, json=NIGHTLY)

        assert (await client.delete(f"{SCHEDULES}/nightly")).status_code == 204
        assert await gateway.get("nightly") is None


async def test_without_temporal_scheduling_reports_itself_unavailable(
    store: InMemoryStore,
) -> None:
    """A 201 for a schedule nobody stored is the worst possible answer here."""
    container = Container(unit_of_work=lambda: InMemoryUnitOfWork(store))

    async with client_for(container) as client:
        await authorise_for(client, "proj-1")
        response = await client.post(SCHEDULES, json=NIGHTLY)

    assert response.status_code == 503
    assert "not connected to Temporal" in response.text


async def test_a_schedule_can_be_created_already_paused(
    client: httpx.AsyncClient, gateway: InMemoryScheduleGateway
) -> None:
    # Writing the schedule before the environment is ready is a normal thing to want.
    await client.post(SCHEDULES, json={**NIGHTLY, "paused": True, "note": "waiting for staging"})

    stored = await gateway.get("nightly")
    assert stored == RunSchedule(
        schedule_id="nightly",
        project_id="proj-1",
        cron="0 2 * * *",
        plan_id="plan-1",
        paused=True,
        note="waiting for staging",
    )
