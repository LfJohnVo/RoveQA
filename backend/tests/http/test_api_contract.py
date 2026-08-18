"""HTTP contract: status codes, error envelope, request id and idempotency."""

import logging
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest

from agentic_qa.bootstrap.container import Container
from agentic_qa.interfaces.http.app import create_app
from agentic_qa.interfaces.http.request_context import (
    REQUEST_ID_HEADER,
    RequestIdLogFilter,
)
from tests.fakes.repositories import InMemoryStore
from tests.fakes.unit_of_work import InMemoryUnitOfWork


def asgi_client(container: Container, *, raise_app_exceptions: bool = True) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(
        app=create_app(container), raise_app_exceptions=raise_app_exceptions
    )
    return httpx.AsyncClient(transport=transport, base_url="http://api")


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    """Drive the real app over ASGI with in-memory adapters.

    The container seam keeps this a true HTTP contract test — routing, validation,
    error handlers and middleware all run — without needing a database.
    """
    store = InMemoryStore()
    async with asgi_client(Container(unit_of_work=lambda: InMemoryUnitOfWork(store))) as client:
        yield client


async def create_project(client: httpx.AsyncClient, name: str = "Checkout") -> str:
    response = await client.post("/api/v1/projects", json={"name": name})
    assert response.status_code == 201
    project_id: str = response.json()["project_id"]
    return project_id


@pytest.fixture
def captured_error_logs() -> Iterator[list[logging.LogRecord]]:
    """Capture records from the handler that logs unexpected failures."""
    records: list[logging.LogRecord] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = Capture()
    handler.addFilter(RequestIdLogFilter())
    logger = logging.getLogger("agentic_qa.interfaces.http.errors")
    logger.addHandler(handler)
    try:
        yield records
    finally:
        logger.removeHandler(handler)


class TestRequestId:
    async def test_generated_when_absent_and_echoed(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/health")
        assert response.headers[REQUEST_ID_HEADER]

    async def test_caller_supplied_id_is_reused(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/health", headers={REQUEST_ID_HEADER: "req-abc"})
        assert response.headers[REQUEST_ID_HEADER] == "req-abc"

    async def test_absurd_inbound_id_is_replaced(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/health", headers={REQUEST_ID_HEADER: "x" * 5000})
        assert response.headers[REQUEST_ID_HEADER] != "x" * 5000

    async def test_error_bodies_carry_the_request_id(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/v1/runs/ghost", headers={REQUEST_ID_HEADER: "req-err"})
        assert response.status_code == 404
        assert response.json()["request_id"] == "req-err"
        assert response.headers[REQUEST_ID_HEADER] == "req-err"


class TestCreateRun:
    async def test_creates_a_run_for_an_existing_project(self, client: httpx.AsyncClient) -> None:
        project_id = await create_project(client)

        response = await client.post(
            "/api/v1/runs",
            json={"project_id": project_id},
            headers={"Idempotency-Key": "k-1"},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["project_id"] == project_id
        assert body["status"] == "created"
        assert body["verdict"] is None

    async def test_repeated_request_replays_with_200(self, client: httpx.AsyncClient) -> None:
        project_id = await create_project(client)
        payload = {"project_id": project_id}
        headers = {"Idempotency-Key": "k-replay"}

        first = await client.post("/api/v1/runs", json=payload, headers=headers)
        second = await client.post("/api/v1/runs", json=payload, headers=headers)

        assert first.status_code == 201
        assert second.status_code == 200
        assert second.json()["run_id"] == first.json()["run_id"]

    async def test_key_reuse_with_a_different_body_is_a_conflict(
        self, client: httpx.AsyncClient
    ) -> None:
        first_project = await create_project(client, "First")
        second_project = await create_project(client, "Second")
        headers = {"Idempotency-Key": "k-shared"}

        await client.post("/api/v1/runs", json={"project_id": first_project}, headers=headers)
        response = await client.post(
            "/api/v1/runs", json={"project_id": second_project}, headers=headers
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CONFLICT"

    async def test_missing_idempotency_key_is_rejected(self, client: httpx.AsyncClient) -> None:
        project_id = await create_project(client)

        response = await client.post("/api/v1/runs", json={"project_id": project_id})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    async def test_unknown_project_is_not_found(self, client: httpx.AsyncClient) -> None:
        response = await client.post(
            "/api/v1/runs",
            json={"project_id": "ghost"},
            headers={"Idempotency-Key": "k-ghost"},
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"

    async def test_unknown_fields_are_rejected(self, client: httpx.AsyncClient) -> None:
        project_id = await create_project(client)

        response = await client.post(
            "/api/v1/runs",
            json={"project_id": project_id, "surprise": 1},
            headers={"Idempotency-Key": "k-extra"},
        )

        assert response.status_code == 422


class TestProjects:
    async def test_blank_name_fails_validation(self, client: httpx.AsyncClient) -> None:
        response = await client.post("/api/v1/projects", json={"name": ""})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    async def test_get_unknown_project(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/v1/projects/ghost")
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "NOT_FOUND"
        assert "message" in body["error"]

    async def test_round_trip(self, client: httpx.AsyncClient) -> None:
        project_id = await create_project(client, "Checkout")
        response = await client.get(f"/api/v1/projects/{project_id}")
        assert response.status_code == 200
        assert response.json() == {"project_id": project_id, "name": "Checkout"}


class ExplodingUnitOfWork(InMemoryUnitOfWork):
    async def __aenter__(self) -> "ExplodingUnitOfWork":
        raise RuntimeError("secret detail: dsn=postgres://user:pw@host/db")


class TestUnexpectedFailures:
    async def test_internal_errors_are_generic_and_correlatable(
        self, captured_error_logs: list[logging.LogRecord]
    ) -> None:
        """No traceback or internal detail reaches the caller, but the id ties them.

        This also proves request-id propagation end to end: the id the client sees is
        the id on the server log record.
        """
        container = Container(unit_of_work=ExplodingUnitOfWork)
        async with asgi_client(container, raise_app_exceptions=False) as client:
            response = await client.get(
                "/api/v1/projects/anything", headers={REQUEST_ID_HEADER: "req-boom"}
            )

        assert response.status_code == 500
        body = response.json()
        assert body["error"]["code"] == "INTERNAL_ERROR"
        assert "secret detail" not in response.text
        assert body["request_id"] == "req-boom"

        assert [record.request_id for record in captured_error_logs] == ["req-boom"]  # type: ignore[attr-defined]
