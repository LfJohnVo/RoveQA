"""The API against the real database.

The contract tests run the app over in-memory adapters; this proves the same app
works through the composition root, a real session and committed transactions.
"""

from collections.abc import Callable

from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.bootstrap.container import Container
from tests.conftest import DEFAULT_POLICY_PAYLOAD
from tests.fakes.workflows import RecordingWorkflowGateway
from tests.http.test_api_contract import asgi_client

UnitOfWorkFactory = Callable[[], UnitOfWork]


async def test_run_creation_and_replay_against_postgres(
    postgres_unit_of_work_factory: UnitOfWorkFactory,
) -> None:
    container = Container(
        unit_of_work=postgres_unit_of_work_factory, workflows=RecordingWorkflowGateway()
    )

    async with asgi_client(container) as client:
        created = await client.post("/api/v1/projects", json={"name": "Checkout"})
        assert created.status_code == 201
        project_id = created.json()["project_id"]
        policy = await client.post(
            f"/api/v1/projects/{project_id}/run-policies", json=DEFAULT_POLICY_PAYLOAD
        )
        assert policy.status_code == 201

        headers = {"Idempotency-Key": "k-http-pg"}
        first = await client.post("/api/v1/runs", json={"project_id": project_id}, headers=headers)
        second = await client.post("/api/v1/runs", json={"project_id": project_id}, headers=headers)

        assert first.status_code == 201
        assert second.status_code == 200
        assert second.json()["run_id"] == first.json()["run_id"]

        # Durable read: a fresh request must see the committed run.
        fetched = await client.get(f"/api/v1/runs/{first.json()['run_id']}")
        assert fetched.status_code == 200
        assert fetched.json()["status"] == "queued"
