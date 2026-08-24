"""HTTP contract: status codes, error envelope, request id and idempotency."""

import logging
from collections.abc import AsyncIterator, Iterator
from uuid import uuid4

import httpx
import pytest

from agentic_qa.application.commands.issue_token import IssueTokenCommand, issue_token
from agentic_qa.bootstrap.container import Container
from agentic_qa.domain.projects.project import Project
from agentic_qa.interfaces.http.app import create_app
from agentic_qa.interfaces.http.request_context import (
    REQUEST_ID_HEADER,
    RequestIdLogFilter,
)
from tests.conftest import DEFAULT_POLICY_PAYLOAD
from tests.fakes.repositories import InMemoryStore
from tests.fakes.unit_of_work import InMemoryUnitOfWork
from tests.fakes.workflows import RecordingWorkflowGateway


def asgi_client(container: Container, *, raise_app_exceptions: bool = True) -> httpx.AsyncClient:
    """Drive the real app over ASGI, including its authentication.

    The container is carried on the client so `create_project` can mint a token the way
    an operator does — with the admin command, against the database, never over HTTP
    (ADR 0020). Tests therefore go *through* the guard rather than around it, which is
    the only way they keep proving it works.
    """
    transport = httpx.ASGITransport(
        app=create_app(container), raise_app_exceptions=raise_app_exceptions
    )
    client = httpx.AsyncClient(transport=transport, base_url="http://api")
    # A documented attribute rather than a richer fixture object: every existing test
    # keeps its signature, and the alternative was editing forty call sites to thread a
    # unit of work through.
    client.roveqa_container = container  # type: ignore[attr-defined]
    return client


async def authorise_for(client: httpx.AsyncClient, project_id: str) -> str:
    """Mint a token for the project and present it from now on.

    Exactly what an operator does after creating a project: `admin token issue`, then the
    value goes in the CI's secret. Here it goes in the client's header.
    """
    container: Container = client.roveqa_container  # type: ignore[attr-defined]
    async with container.unit_of_work() as uow:
        minted = await issue_token(
            uow, IssueTokenCommand(project_id=project_id, label="tests", issued_by="the suite")
        )
    client.headers["Authorization"] = f"Bearer {minted.secret}"
    return minted.secret


@pytest.fixture
def workflows() -> RecordingWorkflowGateway:
    return RecordingWorkflowGateway()


@pytest.fixture
async def client(workflows: RecordingWorkflowGateway) -> AsyncIterator[httpx.AsyncClient]:
    """Drive the real app over ASGI with in-memory adapters.

    The container seam keeps this a true HTTP contract test — routing, validation,
    error handlers and middleware all run — without needing a database or Temporal.
    """
    store = InMemoryStore()
    container = Container(unit_of_work=lambda: InMemoryUnitOfWork(store), workflows=workflows)
    async with asgi_client(container) as client:
        yield client


async def create_run(client: httpx.AsyncClient, project_id: str) -> str:
    response = await client.post(
        "/api/v1/runs",
        json={"project_id": project_id},
        headers={"Idempotency-Key": f"report-{project_id}"},
    )
    assert response.status_code == 201, response.text
    run_id: str = response.json()["run_id"]
    return run_id


async def create_project(client: httpx.AsyncClient, name: str = "Checkout") -> str:
    """Create a project, give it a token, and give it a default run policy.

    Three steps because that is what it takes in reality. A project needs a policy before
    a run can start, and it needs a token before anything can touch it — and the token
    has to exist before the policy call, because that call is already guarded.

    Creating the project itself is reachable with any valid token and grants nothing on
    its own: using the new project still requires a token only the host can mint. Said
    here because a reader of this helper is entitled to wonder.
    """
    await bootstrap_token(client)
    response = await client.post("/api/v1/projects", json={"name": name})
    assert response.status_code == 201, response.text
    project_id: str = response.json()["project_id"]

    await authorise_for(client, project_id)
    policy = await client.post(
        f"/api/v1/projects/{project_id}/run-policies", json=DEFAULT_POLICY_PAYLOAD
    )
    assert policy.status_code == 201, policy.text
    return project_id


async def create_bare_project(client: httpx.AsyncClient, name: str) -> str:
    """A project and a token for it, and no run policy.

    For tests that want to write their own policy. `create_project` is the same thing
    with the default one, which most tests want and none of them should have to repeat.
    """
    await bootstrap_token(client)
    response = await client.post("/api/v1/projects", json={"name": name})
    assert response.status_code == 201, response.text
    project_id: str = response.json()["project_id"]
    await authorise_for(client, project_id)
    return project_id


async def bootstrap_token(client: httpx.AsyncClient) -> None:
    """A token for *something*, so the create call is authenticated at all.

    The chicken and egg of a per-project credential: creating the first project needs a
    caller the deployment already knows, and there is no project yet to know them by. An
    operator resolves it by creating the first project on the host; a test resolves it by
    seeding one directly, which is the same act through a shorter path.
    """
    if "Authorization" in client.headers:
        return
    container: Container = client.roveqa_container  # type: ignore[attr-defined]
    bootstrap_id = f"bootstrap-{uuid4()}"
    async with container.unit_of_work() as uow:
        await uow.projects.add(Project(project_id=bootstrap_id, name="bootstrap"))
        await uow.commit()
    await authorise_for(client, bootstrap_id)


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
        await bootstrap_token(client)
        response = await client.get("/api/v1/runs/ghost", headers={REQUEST_ID_HEADER: "req-err"})
        # An unknown *run* resolves to no project, so the guard lets it through and the
        # handler answers. Unlike an unknown project, which the token cannot cover.
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
        assert body["status"] == "queued"  # accepted; the worker picks it up
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
        # The project is in the *body* here, not the path, so the guard has nothing to
        # compare and the handler answers. Worth keeping as a 404 for exactly that
        # reason: it is the one shape where an unknown project is still a lookup.
        await bootstrap_token(client)
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


class TestRunLifecycleCommands:
    """The API signals intent; only the workflow's activities write status."""

    async def test_pause_resume_cancel_are_accepted_and_signalled(
        self, client: httpx.AsyncClient, workflows: RecordingWorkflowGateway
    ) -> None:
        project_id = await create_project(client)
        created = await client.post(
            "/api/v1/runs", json={"project_id": project_id}, headers={"Idempotency-Key": "k-lc"}
        )
        run_id = created.json()["run_id"]

        for action in ("pause", "resume", "cancel"):
            response = await client.post(f"/api/v1/runs/{run_id}/{action}")
            assert response.status_code == 202
            assert response.json() == {"run_id": run_id, "accepted": action}

        assert workflows.signals == [
            (run_id, "pause"),
            (run_id, "resume"),
            (run_id, "cancel"),
        ]

    async def test_status_does_not_change_just_because_a_command_was_accepted(
        self, client: httpx.AsyncClient
    ) -> None:
        """Durable status follows the workflow, never the request that asked for it."""
        project_id = await create_project(client)
        created = await client.post(
            "/api/v1/runs", json={"project_id": project_id}, headers={"Idempotency-Key": "k-st"}
        )
        run_id = created.json()["run_id"]

        await client.post(f"/api/v1/runs/{run_id}/cancel")

        after = await client.get(f"/api/v1/runs/{run_id}")
        assert after.json()["status"] == "queued"

    async def test_creating_a_run_returns_before_it_finishes(
        self, client: httpx.AsyncClient
    ) -> None:
        """The request hands the run to the durable engine and returns immediately.

        An API that waited for a terminal state would host an hours-long loop, which
        is exactly what Temporal exists to avoid.
        """
        project_id = await create_project(client)

        created = await client.post(
            "/api/v1/runs", json={"project_id": project_id}, headers={"Idempotency-Key": "k-nb"}
        )

        assert created.status_code == 201
        assert created.json()["status"] == "queued"  # not a terminal state
        assert created.json()["verdict"] is None

    async def test_cancelling_twice_is_idempotent(
        self, client: httpx.AsyncClient, workflows: RecordingWorkflowGateway
    ) -> None:
        project_id = await create_project(client)
        created = await client.post(
            "/api/v1/runs", json={"project_id": project_id}, headers={"Idempotency-Key": "k-cc"}
        )
        run_id = created.json()["run_id"]

        first = await client.post(f"/api/v1/runs/{run_id}/cancel")
        second = await client.post(f"/api/v1/runs/{run_id}/cancel")

        assert first.status_code == second.status_code == 202
        assert workflows.signals.count((run_id, "cancel")) == 2

    async def test_commands_on_an_unknown_run_are_not_found(
        self, client: httpx.AsyncClient, workflows: RecordingWorkflowGateway
    ) -> None:
        await bootstrap_token(client)
        response = await client.post("/api/v1/runs/ghost/cancel")
        assert response.status_code == 404
        assert workflows.signals == []


class TestRunEvents:
    """Durable catch-up: what a client replays after losing its live connection."""

    async def test_creation_and_lifecycle_leave_durable_events(
        self, client: httpx.AsyncClient
    ) -> None:
        project_id = await create_project(client)
        created = await client.post(
            "/api/v1/runs",
            json={"project_id": project_id},
            headers={"Idempotency-Key": "k-ev", REQUEST_ID_HEADER: "req-ev"},
        )
        run_id = created.json()["run_id"]

        page = await client.get(f"/api/v1/runs/{run_id}/events")

        assert page.status_code == 200
        body = page.json()
        assert [event["type"] for event in body["events"]] == ["run.created"]
        assert body["events"][0]["sequence"] == 1
        assert body["events"][0]["request_id"] == "req-ev"
        assert body["next_after"] == 1

    async def test_resuming_from_a_cursor_returns_nothing_when_caught_up(
        self, client: httpx.AsyncClient
    ) -> None:
        project_id = await create_project(client)
        created = await client.post(
            "/api/v1/runs", json={"project_id": project_id}, headers={"Idempotency-Key": "k-ev2"}
        )
        run_id = created.json()["run_id"]

        page = await client.get(f"/api/v1/runs/{run_id}/events", params={"after": 1})

        assert page.json() == {"events": [], "next_after": 1}

    async def test_page_size_is_bounded(self, client: httpx.AsyncClient) -> None:
        project_id = await create_project(client)
        created = await client.post(
            "/api/v1/runs", json={"project_id": project_id}, headers={"Idempotency-Key": "k-ev3"}
        )
        run_id = created.json()["run_id"]

        response = await client.get(f"/api/v1/runs/{run_id}/events", params={"limit": 10_000})

        assert response.status_code == 422  # rejected, never silently unbounded

    async def test_events_of_an_unknown_run_are_not_found(self, client: httpx.AsyncClient) -> None:
        await bootstrap_token(client)
        response = await client.get("/api/v1/runs/ghost/events")
        assert response.status_code == 404


class TestProjects:
    async def test_blank_name_fails_validation(self, client: httpx.AsyncClient) -> None:
        # Authenticated first, so this is validation answering and not the guard.
        await bootstrap_token(client)
        response = await client.post("/api/v1/projects", json={"name": ""})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    async def test_an_unknown_project_is_refused_without_saying_whether_it_exists(
        self, client: httpx.AsyncClient
    ) -> None:
        # `403`, not `404`, and the change is the point. A token covers one project; a
        # path naming another is refused before any lookup, so a caller cannot probe for
        # which project ids exist by reading the status code.
        await bootstrap_token(client)

        response = await client.get("/api/v1/projects/ghost")

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"

    async def test_round_trip(self, client: httpx.AsyncClient) -> None:
        project_id = await create_project(client, "Checkout")
        response = await client.get(f"/api/v1/projects/{project_id}")
        assert response.status_code == 200

        body = response.json()
        assert body["project_id"] == project_id
        assert body["name"] == "Checkout"
        # `create_project` seeds a default policy, so this project can run.
        assert body["default_run_policy_id"] is not None


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
        container = Container(unit_of_work=lambda: ExplodingUnitOfWork())
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


async def test_stories_can_be_listed_and_read_back(client: httpx.AsyncClient) -> None:
    """A story is not write-only.

    Phase 07 could create one and compile it; nothing could read it back, so a UI could
    show a story it had just submitted and nothing else. These are the two reads a
    story editor needs to exist at all.
    """
    project_id = await create_project(client)
    created = await client.post(
        f"/api/v1/projects/{project_id}/stories",
        json={
            "actor": "a QA engineer",
            "goal": "reach the records page",
            "acceptance_criteria": [
                {"criterion_id": "ac-1", "description": "the records page opens"}
            ],
        },
    )
    assert created.status_code == 201
    story_id = created.json()["story_id"]

    listed = await client.get(f"/api/v1/projects/{project_id}/stories")
    assert listed.status_code == 200
    assert [story["story_id"] for story in listed.json()] == [story_id]

    read = await client.get(f"/api/v1/stories/{story_id}")
    assert read.status_code == 200
    assert read.json()["goal"] == "reach the records page"
    assert read.json()["acceptance_criteria"][0]["criterion_id"] == "ac-1"


async def test_reading_a_story_that_does_not_exist_is_a_404(client: httpx.AsyncClient) -> None:
    await bootstrap_token(client)
    response = await client.get("/api/v1/stories/nope")
    assert response.status_code == 404


async def test_the_story_listing_is_bounded(client: httpx.AsyncClient) -> None:
    # An unbounded listing is a response whose size nobody chose.
    project_id = await create_project(client)
    response = await client.get(f"/api/v1/projects/{project_id}/stories?limit=500")
    assert response.status_code == 422


async def test_a_projects_runs_can_be_listed(client: httpx.AsyncClient) -> None:
    """Without this a finished run was reachable only by its id.

    The console could show the run it had just started and nothing else — every run from
    an earlier session, a schedule or the CLI was invisible to it.
    """
    project_id = await create_project(client)
    other = await create_project(client, name="Somebody else")
    first = await create_run(client, project_id)
    second = await client.post(
        "/api/v1/runs",
        json={"project_id": project_id},
        headers={"Idempotency-Key": f"second-{project_id}"},
    )
    assert second.status_code == 201, second.text
    await create_run(client, other)

    # `create_project` leaves the client holding the *last* project's token, which is
    # what an operator would also have to switch. Back to the one under test.
    await authorise_for(client, project_id)
    listed = await client.get(f"/api/v1/projects/{project_id}/runs")
    assert listed.status_code == 200
    ids = [run["run_id"] for run in listed.json()]

    assert set(ids) == {first, second.json()["run_id"]}, "a project's runs, and only those"
    assert listed.json()[0]["project_id"] == project_id


async def test_the_run_listing_is_bounded(client: httpx.AsyncClient) -> None:
    # A project accumulates runs for as long as it is tested, so the page size is a
    # promise about response size rather than a suggestion.
    project_id = await create_project(client)
    response = await client.get(f"/api/v1/projects/{project_id}/runs?limit=500")
    assert response.status_code == 422


async def test_a_project_says_whether_it_can_run(client: httpx.AsyncClient) -> None:
    """`default_run_policy_id` is part of the project.

    A run with no policy named resolves the project's default, so a project without one
    cannot run. Without this field a client had no way to say so before someone tried,
    and the precondition surfaced as a validation error at the end of the flow.
    """
    await bootstrap_token(client)
    created = await client.post("/api/v1/projects", json={"name": "Policyless"})
    project_id = created.json()["project_id"]
    assert created.json()["default_run_policy_id"] is None
    await authorise_for(client, project_id)

    await client.post(f"/api/v1/projects/{project_id}/run-policies", json=DEFAULT_POLICY_PAYLOAD)

    read = await client.get(f"/api/v1/projects/{project_id}")
    assert read.json()["default_run_policy_id"] is not None


async def test_a_run_can_ask_to_explore(
    client: httpx.AsyncClient, workflows: RecordingWorkflowGateway
) -> None:
    """Exploring is a request, not something inferred from a missing plan.

    A plan-less run has always meant "work towards this goal with the planner", and
    quietly turning that into a deterministic crawl would remove a capability nobody
    asked to lose.
    """
    project_id = await create_bare_project(client, "Explore me")
    await client.post(
        f"/api/v1/projects/{project_id}/run-policies",
        json={
            "allowed_origins": ["http://localhost:3000"],
            "max_duration_seconds": 60,
            "max_actions": 10,
            "max_model_calls": 0,
            "set_as_project_default": True,
        },
    )

    response = await client.post(
        "/api/v1/runs",
        json={"project_id": project_id, "explore": True},
        headers={"Idempotency-Key": "explore-1"},
    )

    assert response.status_code == 201
    assert workflows.explored == [response.json()["run_id"]]


async def test_the_same_key_cannot_switch_a_run_between_modes(
    client: httpx.AsyncClient,
) -> None:
    # Exploring and planning are different requests. Replaying the first for the second
    # would hand back a run that does something else than what was asked for.
    project_id = await create_bare_project(client, "Modes")
    await client.post(
        f"/api/v1/projects/{project_id}/run-policies",
        json={
            "allowed_origins": ["http://localhost:3000"],
            "max_duration_seconds": 60,
            "max_actions": 10,
            "max_model_calls": 0,
            "set_as_project_default": True,
        },
    )
    headers = {"Idempotency-Key": "same-key"}
    body = {"project_id": project_id}

    first = await client.post("/api/v1/runs", json={**body, "explore": True}, headers=headers)
    second = await client.post("/api/v1/runs", json=body, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409


class TestOneReportInTwoRenderings:
    """The same answer as a contract and as prose, negotiated rather than given two URLs.

    `render_markdown` existed for two phases as an exported function nothing called: the
    report was machine-readable and nobody could read it. Two paths would have been two
    things to keep in step; one path with an `Accept` header is one report.
    """

    async def test_the_default_is_the_versioned_document(self, client: httpx.AsyncClient) -> None:
        project_id = await create_project(client)
        run_id = await create_run(client, project_id)

        response = await client.get(f"/api/v1/runs/{run_id}/report")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        assert response.json()["schema_version"] == "roveqa.run-report.v1"

    async def test_asking_for_markdown_gets_prose(self, client: httpx.AsyncClient) -> None:
        project_id = await create_project(client)
        run_id = await create_run(client, project_id)

        response = await client.get(
            f"/api/v1/runs/{run_id}/report", headers={"Accept": "text/markdown"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/markdown")
        assert response.text.startswith(f"# Run {run_id}")
        # The section that keeps a hypothesis from reading as a finding is in the prose
        # too, not only in the JSON keys.
        assert "## Observed" in response.text
