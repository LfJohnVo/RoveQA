"""The memory administration endpoints over real HTTP.

What matters here is the behaviour when things are broken, because that is when an
operator reaches for these: every one of them has to keep answering while the graph is
down, and `rebuild` has to refuse honestly when there is no projection at all rather
than return 200 for work it did not do.
"""

from collections.abc import AsyncIterator

import httpx
import pytest

from agentic_qa.application.ports.graph import GRAPH_SCHEMA_VERSION
from agentic_qa.bootstrap.container import Container
from agentic_qa.interfaces.http.app import create_app
from tests.fakes.graph import InMemoryGraphMemory, UnavailableGraph
from tests.fakes.repositories import InMemoryStore
from tests.fakes.unit_of_work import InMemoryUnitOfWork


def app_client(container: Container) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=create_app(container), raise_app_exceptions=True)
    return httpx.AsyncClient(transport=transport, base_url="http://api")


@pytest.fixture
async def working_graph() -> AsyncIterator[httpx.AsyncClient]:
    store = InMemoryStore()
    container = Container(
        unit_of_work=lambda: InMemoryUnitOfWork(store), graph=InMemoryGraphMemory()
    )
    async with app_client(container) as client:
        yield client


@pytest.fixture
async def broken_graph() -> AsyncIterator[httpx.AsyncClient]:
    store = InMemoryStore()
    container = Container(unit_of_work=lambda: InMemoryUnitOfWork(store), graph=UnavailableGraph())
    async with app_client(container) as client:
        yield client


@pytest.fixture
async def no_graph() -> AsyncIterator[httpx.AsyncClient]:
    store = InMemoryStore()
    container = Container(unit_of_work=lambda: InMemoryUnitOfWork(store))
    async with app_client(container) as client:
        yield client


SCOPE = {"environment_id": "staging"}
MEMORY = "/api/v1/projects/proj-1/memory"


class TestStatus:
    async def test_it_reports_what_the_server_writes(
        self, working_graph: httpx.AsyncClient
    ) -> None:
        response = await working_graph.get(f"{MEMORY}/status", params=SCOPE)

        assert response.status_code == 200
        body = response.json()
        assert body["graph_available"] is True
        assert body["graph_schema_version"] == GRAPH_SCHEMA_VERSION
        assert body["durable_candidates"] == 0

    async def test_it_still_answers_while_the_graph_is_down(
        self, broken_graph: httpx.AsyncClient
    ) -> None:
        # A status command that fails because the thing it monitors failed is useless
        # exactly when it is needed.
        response = await broken_graph.get(f"{MEMORY}/status", params=SCOPE)

        assert response.status_code == 200
        assert response.json()["graph_available"] is False

    async def test_it_answers_when_there_is_no_projection_at_all(
        self, no_graph: httpx.AsyncClient
    ) -> None:
        response = await no_graph.get(f"{MEMORY}/status", params=SCOPE)

        assert response.status_code == 200
        assert response.json()["graph_available"] is False

    async def test_the_project_is_part_of_the_path(self, working_graph: httpx.AsyncClient) -> None:
        # Memory is scoped. There is no route that omits the project, so a rebuild
        # cannot default to "everything" and reach the wrong one.
        response = await working_graph.get("/api/v1/memory/status")
        assert response.status_code == 404


class TestValidate:
    async def test_a_healthy_projection_reports_no_problems(
        self, working_graph: httpx.AsyncClient
    ) -> None:
        response = await working_graph.post(f"{MEMORY}/validate", params=SCOPE)

        assert response.status_code == 200
        body = response.json()
        assert body["healthy"] is True
        assert body["problems"] == []

    async def test_it_names_the_problem_rather_than_counting_it(
        self, broken_graph: httpx.AsyncClient
    ) -> None:
        response = await broken_graph.post(f"{MEMORY}/validate", params=SCOPE)

        assert response.status_code == 200
        body = response.json()
        assert body["healthy"] is False
        assert "graph store unreachable" in body["problems"]

    async def test_it_does_not_repair_what_it_found(self, broken_graph: httpx.AsyncClient) -> None:
        # An operator deciding whether to rebuild needs to see the damage. A validate
        # that silently repaired would answer "healthy" every time.
        first = await broken_graph.post(f"{MEMORY}/validate", params=SCOPE)
        second = await broken_graph.post(f"{MEMORY}/validate", params=SCOPE)

        assert first.json()["problems"] == second.json()["problems"]


class TestRebuild:
    async def test_it_reports_what_it_projected(self, working_graph: httpx.AsyncClient) -> None:
        response = await working_graph.post(f"{MEMORY}/rebuild", params=SCOPE)

        assert response.status_code == 200
        body = response.json()
        assert body["graph_available"] is True
        assert body["materialized"] == 0

    async def test_a_graph_that_is_down_is_reported_not_raised(
        self, broken_graph: httpx.AsyncClient
    ) -> None:
        # The durable side is fine and the backlog kept the work; failing the request
        # would tell an operator something worse happened than did.
        response = await broken_graph.post(f"{MEMORY}/rebuild", params=SCOPE)

        assert response.status_code == 200
        assert response.json()["graph_available"] is False

    async def test_no_projection_configured_refuses_rather_than_succeeding(
        self, no_graph: httpx.AsyncClient
    ) -> None:
        # An operator who asked for a rebuild and got 200 would believe the projection
        # exists.
        response = await no_graph.post(f"{MEMORY}/rebuild", params=SCOPE)

        assert response.status_code == 503
        assert "no learned-memory projection" in response.text


class TestSync:
    async def test_it_drains_the_backlog_without_rebuilding(
        self, working_graph: httpx.AsyncClient
    ) -> None:
        response = await working_graph.post(f"{MEMORY}/sync", params=SCOPE)

        assert response.status_code == 200
        assert response.json()["failed"] == 0

    async def test_it_refuses_without_a_projection(self, no_graph: httpx.AsyncClient) -> None:
        response = await no_graph.post(f"{MEMORY}/sync", params=SCOPE)
        assert response.status_code == 503
