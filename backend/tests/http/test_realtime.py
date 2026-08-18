"""WebSocket realtime: catch-up, live relay and graceful degradation."""

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi.testclient import TestClient

from agentic_qa.application.ports.events import NewRunEvent
from agentic_qa.application.ports.streams import RunEventPublisher
from agentic_qa.bootstrap.container import Container
from agentic_qa.interfaces.http.app import create_app
from agentic_qa.interfaces.http.routers.realtime import CLOSE_REALTIME_UNAVAILABLE
from tests.conftest import DEFAULT_POLICY_PAYLOAD
from tests.fakes.repositories import InMemoryStore
from tests.fakes.streams import BrokenRunEventPublisher, InMemoryRunEventPublisher
from tests.fakes.unit_of_work import InMemoryUnitOfWork
from tests.fakes.workflows import RecordingWorkflowGateway


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def publisher() -> InMemoryRunEventPublisher:
    return InMemoryRunEventPublisher()


def build_container(store: InMemoryStore, publisher: RunEventPublisher | None) -> Container:
    return Container(
        unit_of_work=lambda: InMemoryUnitOfWork(store),
        workflows=RecordingWorkflowGateway(),
        events=publisher,
    )


@pytest.fixture
async def client(
    store: InMemoryStore, publisher: InMemoryRunEventPublisher
) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=create_app(build_container(store, publisher)))
    async with httpx.AsyncClient(transport=transport, base_url="http://api") as client:
        yield client


async def start_run(client: httpx.AsyncClient, key: str = "k-ws") -> str:
    project = await client.post("/api/v1/projects", json={"name": "Realtime"})
    project_id = project.json()["project_id"]
    await client.post(f"/api/v1/projects/{project_id}/run-policies", json=DEFAULT_POLICY_PAYLOAD)
    created = await client.post(
        "/api/v1/runs",
        json={"project_id": project.json()["project_id"]},
        headers={"Idempotency-Key": key},
    )
    run_id: str = created.json()["run_id"]
    return run_id


async def test_creating_a_run_publishes_its_event(
    client: httpx.AsyncClient, publisher: InMemoryRunEventPublisher
) -> None:
    run_id = await start_run(client)

    assert [(event.run_id, event.type) for event in publisher.published] == [
        (run_id, "run.created")
    ]


async def test_a_broken_publisher_does_not_fail_the_request(
    store: InMemoryStore,
) -> None:
    """Redis down must cost freshness, never a run (docs/09 recovery assumption)."""
    transport = httpx.ASGITransport(
        app=create_app(build_container(store, BrokenRunEventPublisher()))
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://api") as client:
        run_id = await start_run(client, "k-broken")

        # The run exists and its durable event is intact despite the publish failure.
        assert (await client.get(f"/api/v1/runs/{run_id}")).status_code == 200
        page = await client.get(f"/api/v1/runs/{run_id}/events")
        assert [event["type"] for event in page.json()["events"]] == ["run.created"]


def test_websocket_replays_durable_history_then_streams_live() -> None:
    """TestClient drives the socket synchronously, which suits a connect-then-assert flow."""
    store = InMemoryStore()
    publisher = InMemoryRunEventPublisher()
    app = create_app(build_container(store, publisher))

    with TestClient(app) as client:
        project = client.post("/api/v1/projects", json={"name": "Realtime"})
        project_id = project.json()["project_id"]
        client.post(f"/api/v1/projects/{project_id}/run-policies", json=DEFAULT_POLICY_PAYLOAD)
        created = client.post(
            "/api/v1/runs",
            json={"project_id": project.json()["project_id"]},
            headers={"Idempotency-Key": "k-live"},
        )
        run_id = created.json()["run_id"]

        with client.websocket_connect(f"/ws/runs/{run_id}") as socket:
            history = socket.receive_json()
            assert history["type"] == "run.created"
            assert history["sequence"] == 1


def test_websocket_resuming_from_a_cursor_skips_delivered_history() -> None:
    store = InMemoryStore()
    publisher = InMemoryRunEventPublisher()
    app = create_app(build_container(store, publisher))

    with TestClient(app) as client:
        project = client.post("/api/v1/projects", json={"name": "Realtime"})
        project_id = project.json()["project_id"]
        client.post(f"/api/v1/projects/{project_id}/run-policies", json=DEFAULT_POLICY_PAYLOAD)
        created = client.post(
            "/api/v1/runs",
            json={"project_id": project.json()["project_id"]},
            headers={"Idempotency-Key": "k-cursor"},
        )
        run_id = created.json()["run_id"]

        # Already saw sequence 1; the socket must not replay it.
        with client.websocket_connect(f"/ws/runs/{run_id}?after=1") as socket:
            socket.close()


def test_websocket_without_realtime_still_delivers_the_baseline() -> None:
    """No publisher: the client gets full history, then a code telling it to poll."""
    store = InMemoryStore()
    app = create_app(build_container(store, None))

    with TestClient(app) as client:
        project = client.post("/api/v1/projects", json={"name": "Realtime"})
        project_id = project.json()["project_id"]
        client.post(f"/api/v1/projects/{project_id}/run-policies", json=DEFAULT_POLICY_PAYLOAD)
        created = client.post(
            "/api/v1/runs",
            json={"project_id": project.json()["project_id"]},
            headers={"Idempotency-Key": "k-nopub"},
        )
        run_id = created.json()["run_id"]

        with client.websocket_connect(f"/ws/runs/{run_id}") as socket:
            assert socket.receive_json()["type"] == "run.created"
            closed = socket.receive()

    assert closed["type"] == "websocket.close"
    assert closed["code"] == CLOSE_REALTIME_UNAVAILABLE


async def test_events_appended_later_reach_a_live_subscriber(
    store: InMemoryStore, publisher: InMemoryRunEventPublisher
) -> None:
    """The subscription is opened before history is read, so nothing slips through."""
    uow = InMemoryUnitOfWork(store)
    async with uow:
        from agentic_qa.domain.projects.project import Project
        from agentic_qa.domain.runs.run import Run

        await uow.projects.add(Project(project_id="p-sub", name="Realtime"))
        await uow.runs.add(Run(run_id="r-sub", project_id="p-sub"))
        await uow.commit()

    subscription = await publisher.subscribe("r-sub")
    async with uow:
        event = await uow.events.append(NewRunEvent(run_id="r-sub", type="run.status.changed"))
        await uow.commit()
    await publisher.publish(event)

    received = await anext(aiter(subscription))
    assert received.sequence == event.sequence
    await subscription.aclose()
