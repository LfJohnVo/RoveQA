"""The concurrency gate: an endpoint never serves more calls than it declared.

Run against the in-memory semaphore and against real Redis, because the limit only
means anything if it holds between processes: two workers each counting to two locally
would send four calls to a box that fits two.
"""

import asyncio
import json

import httpx
import pytest

from agentic_qa.application.ports.semaphores import ResourceSemaphore
from agentic_qa.domain.inference.tasks import InferenceBudget, ModelCapability, TaskType
from agentic_qa.infrastructure.inference.errors import ModelUnavailableError
from agentic_qa.infrastructure.inference.metrics import InferenceMetrics
from agentic_qa.infrastructure.inference.router import ModelEndpoint
from agentic_qa.infrastructure.inference.schemas import BrowserDecision
from agentic_qa.infrastructure.inference.vllm.client import VLLMChatClient

DECISION = json.dumps({"finished": True, "rationale": "nothing to do"})


class ConcurrencyProbe:
    """A model server that reports the most calls it ever had in flight at once."""

    def __init__(self, hold_seconds: float = 0.05) -> None:
        self.in_flight = 0
        self.peak = 0
        self.served = 0
        self._hold = hold_seconds

    async def handle(self, request: httpx.Request) -> httpx.Response:
        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        try:
            await asyncio.sleep(self._hold)
            self.served += 1
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": DECISION}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                },
            )
        finally:
            self.in_flight -= 1


def build_client(
    probe: ConcurrencyProbe,
    semaphore: ResourceSemaphore,
    *,
    capacity: int,
    endpoint_name: str,
    slot_wait_seconds: float = 30.0,
) -> VLLMChatClient:
    endpoint = ModelEndpoint(
        name=endpoint_name,
        base_url="http://vllm:8000",
        model="test-model",
        capability=ModelCapability.FAST,
        max_concurrency=capacity,
        budget=InferenceBudget(timeout_seconds=5.0, max_attempts=1),
    )
    return VLLMChatClient(
        endpoint=endpoint,
        http=httpx.AsyncClient(transport=httpx.MockTransport(probe.handle)),
        semaphore=semaphore,
        metrics=InferenceMetrics(),
        retry_backoff_seconds=0.0,
        slot_wait_seconds=slot_wait_seconds,
    )


async def ask(client: VLLMChatClient) -> BrowserDecision:
    return await client.complete_json(
        task=TaskType.GUI_ACTION, system="s", user="u", schema=BrowserDecision
    )


@pytest.mark.parametrize("capacity", [1, 2])
async def test_calls_never_exceed_the_declared_capacity(
    resource_semaphore: ResourceSemaphore, capacity: int
) -> None:
    probe = ConcurrencyProbe()
    client = build_client(
        probe, resource_semaphore, capacity=capacity, endpoint_name=f"cap{capacity}"
    )

    results = await asyncio.gather(*(ask(client) for _ in range(6)))

    assert len(results) == 6, "every call must still complete, just not all at once"
    assert probe.served == 6
    assert probe.peak <= capacity, f"{probe.peak} calls were in flight with capacity {capacity}"


async def test_two_independent_clients_share_the_endpoint_budget(
    resource_semaphore: ResourceSemaphore,
) -> None:
    """Two workers, one GPU. The limit lives with the endpoint, not with the caller."""
    probe = ConcurrencyProbe()
    workers = [
        build_client(probe, resource_semaphore, capacity=1, endpoint_name="shared")
        for _ in range(2)
    ]

    await asyncio.gather(*(ask(client) for client in workers for _ in range(2)))

    assert probe.served == 4
    assert probe.peak == 1


async def test_a_saturated_endpoint_reports_unavailable_instead_of_waiting_forever(
    resource_semaphore: ResourceSemaphore,
) -> None:
    """A queue with no deadline is a run that never ends and never says why."""
    probe = ConcurrencyProbe(hold_seconds=0.4)
    blocking = build_client(probe, resource_semaphore, capacity=1, endpoint_name="tight")
    impatient = build_client(
        probe, resource_semaphore, capacity=1, endpoint_name="tight", slot_wait_seconds=0.0
    )

    holder = asyncio.create_task(ask(blocking))
    await _wait_until_held(resource_semaphore, "model:tight")

    with pytest.raises(ModelUnavailableError, match="capacity"):
        await ask(impatient)

    await holder


async def _wait_until_held(semaphore: ResourceSemaphore, resource: str) -> None:
    """Wait on the observable condition — the slot being taken — not on a guessed delay."""
    for _ in range(200):
        if await semaphore.in_use(resource) > 0:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"{resource} was never taken")
