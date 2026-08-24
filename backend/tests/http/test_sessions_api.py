"""A session goes in and never comes back out (ADR 0019).

This is the phase gate written as a test: plant a secret, exercise every surface that a
session touches, and look for it in all of them. It is deliberately not a unit test of
the sealing — that has its own file — but a sweep of the *exits*, because a credential
does not leak from the place that stores it. It leaks from the fifth place that reads it.

What is checked here: the response to registering, the listing, the OpenAPI document,
every error body, and the logs the request writes. What cannot be checked here is the
prompt, the state map and the graph — those need a browser and have their own tests —
so this asserts the surfaces the API owns and nothing it does not.
"""

import json
import logging
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from agentic_qa.bootstrap.container import Container
from agentic_qa.infrastructure.keyring.file_keyring import FileSecretKeyring
from tests.fakes.repositories import InMemoryStore
from tests.fakes.unit_of_work import InMemoryUnitOfWork
from tests.http.test_api_contract import asgi_client, create_project

SECRET_COOKIE = "s3cr3t-session-value-nobody-should-ever-see"
STORAGE_STATE = json.dumps(
    {"cookies": [{"name": "sid", "value": SECRET_COOKIE, "domain": "app.test", "path": "/"}]}
)


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    store = InMemoryStore()
    container = Container(
        unit_of_work=lambda: InMemoryUnitOfWork(store),
        keyring=FileSecretKeyring(tmp_path / "keyring"),
    )
    async with asgi_client(container) as http:
        yield http


@pytest.fixture
def captured_logs() -> Iterator[list[logging.LogRecord]]:
    """Everything the process logs while a session is registered.

    A log file is the exit nobody remembers. It outlives the run, it is copied into
    support tickets, and nothing redacts it after the fact.
    """
    records: list[logging.LogRecord] = []

    class Collector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = Collector()
    root = logging.getLogger()
    root.addHandler(handler)
    previous = root.level
    root.setLevel(logging.DEBUG)
    try:
        yield records
    finally:
        root.removeHandler(handler)
        root.setLevel(previous)


async def make_environment(client: httpx.AsyncClient) -> str:
    project_id = await create_project(client)
    response = await client.post(
        f"/api/v1/projects/{project_id}/environments", json={"name": "staging"}
    )
    assert response.status_code == 201, response.text
    environment_id: str = response.json()["environment_id"]
    return environment_id


async def register(client: httpx.AsyncClient, environment_id: str, **overrides: object) -> str:
    body: dict[str, object] = {
        "label": "admin",
        "storage_state": STORAGE_STATE,
        "established_by": "captured by hand",
    }
    body.update(overrides)
    response = await client.post(f"/api/v1/environments/{environment_id}/sessions", json=body)
    assert response.status_code == 201, response.text
    session_id: str = response.json()["session_id"]
    return session_id


class TestTheSecretDoesNotComeBack:
    async def test_the_response_carries_the_record_and_not_the_state(
        self, client: httpx.AsyncClient
    ) -> None:
        environment_id = await make_environment(client)

        response = await client.post(
            f"/api/v1/environments/{environment_id}/sessions",
            json={"label": "admin", "storage_state": STORAGE_STATE},
        )

        assert response.status_code == 201
        assert SECRET_COOKIE not in response.text
        assert response.json()["label"] == "admin"

    async def test_the_listing_carries_neither_the_state_nor_the_ciphertext(
        self, client: httpx.AsyncClient
    ) -> None:
        environment_id = await make_environment(client)
        await register(client, environment_id)

        listed = await client.get(f"/api/v1/environments/{environment_id}/sessions")

        assert listed.status_code == 200
        assert SECRET_COOKIE not in listed.text
        assert len(listed.json()) == 1

    async def test_no_endpoint_anywhere_returns_a_stored_session(
        self, client: httpx.AsyncClient
    ) -> None:
        # Structural, and the reason it is asserted rather than assumed: the containment
        # argument rests on there being no read path, and "nobody added one" is a fact
        # about today that a test can keep true tomorrow.
        schemas = (await client.get("/openapi.json")).json()["components"]["schemas"]

        # It goes in...
        assert "storage_state" in json.dumps(schemas["RegisterSessionRequest"])
        # ...and no response model anywhere carries it back.
        for name, schema in schemas.items():
            if name.endswith("Request"):
                continue
            assert "storage_state" not in json.dumps(schema), name

    async def test_nothing_logged_while_registering_contains_it(
        self, client: httpx.AsyncClient, captured_logs: list[logging.LogRecord]
    ) -> None:
        environment_id = await make_environment(client)
        await register(client, environment_id)

        written = "\n".join(record.getMessage() for record in captured_logs)

        assert SECRET_COOKIE not in written

    async def test_an_error_body_does_not_echo_the_request(self, client: httpx.AsyncClient) -> None:
        # A validation error that quoted the offending value would put the whole session
        # in a 422 body — the one response nobody thinks of as sensitive.
        await make_environment(client)
        response = await client.post(
            "/api/v1/environments/env-that-does-not-exist/sessions",
            json={"label": "", "storage_state": STORAGE_STATE},
        )

        assert response.status_code in (403, 404, 422)
        assert SECRET_COOKIE not in response.text


class TestRegisteringAndRotating:
    async def test_a_session_for_an_unknown_environment_is_a_404(
        self, client: httpx.AsyncClient
    ) -> None:
        # With a token in hand, so this is the handler answering and not the guard.
        await make_environment(client)
        response = await client.post(
            "/api/v1/environments/nope/sessions",
            json={"label": "admin", "storage_state": STORAGE_STATE},
        )

        assert response.status_code == 404

    async def test_rotating_adds_rather_than_overwrites(self, client: httpx.AsyncClient) -> None:
        # The previous session stays on the record. An overwrite would erase the answer
        # to "what were we using yesterday", which is the first question after runs
        # start failing.
        environment_id = await make_environment(client)
        first = await register(client, environment_id, label="old")
        second = await register(client, environment_id, label="new")

        listed = (await client.get(f"/api/v1/environments/{environment_id}/sessions")).json()

        assert [item["session_id"] for item in listed] == [second, first]

    async def test_an_expiry_before_the_start_is_refused(self, client: httpx.AsyncClient) -> None:
        environment_id = await make_environment(client)

        response = await client.post(
            f"/api/v1/environments/{environment_id}/sessions",
            json={
                "label": "admin",
                "storage_state": STORAGE_STATE,
                "valid_until": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            },
        )

        assert response.status_code == 422

    async def test_an_oversized_state_is_refused_before_it_is_sealed(
        self, client: httpx.AsyncClient
    ) -> None:
        # A storage state is kilobytes. Something megabytes long is a mistake or an
        # attack, and either way better refused than encrypted and kept forever.
        environment_id = await make_environment(client)

        response = await client.post(
            f"/api/v1/environments/{environment_id}/sessions",
            json={"label": "admin", "storage_state": "x" * 600_000},
        )

        assert response.status_code == 422


class TestRevoking:
    async def test_it_leaves_the_record_and_destroys_the_key(
        self, client: httpx.AsyncClient
    ) -> None:
        environment_id = await make_environment(client)
        session_id = await register(client, environment_id)

        gone = await client.post(
            f"/api/v1/environments/{environment_id}/sessions/{session_id}/revoke"
        )

        assert gone.status_code == 204
        # The row is the audit trail: who registered what, when. What makes the session
        # unusable is the absence of a key the database never held.
        listed = (await client.get(f"/api/v1/environments/{environment_id}/sessions")).json()
        assert [item["session_id"] for item in listed] == [session_id]

    async def test_revoking_twice_is_not_an_error(self, client: httpx.AsyncClient) -> None:
        # A client that lost the response has to be able to repeat it.
        environment_id = await make_environment(client)
        session_id = await register(client, environment_id)
        path = f"/api/v1/environments/{environment_id}/sessions/{session_id}/revoke"

        assert (await client.post(path)).status_code == 204
        assert (await client.post(path)).status_code == 204

    async def test_a_session_of_another_environment_cannot_be_revoked_by_guessing(
        self, client: httpx.AsyncClient
    ) -> None:
        mine = await make_environment(client)
        session_id = await register(client, mine)
        somebody_else = await make_environment(client)

        response = await client.post(
            f"/api/v1/environments/{somebody_else}/sessions/{session_id}/revoke"
        )

        assert response.status_code == 404
