"""Endpoint behaviour: what gets retried, what does not, and what is never coerced.

The transport is an `httpx.MockTransport`, so these exercise the real client — the same
request building, status handling, parsing and metrics as production — against a server
that can be made to misbehave on demand.
"""

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from agentic_qa.domain.inference.tasks import InferenceBudget, ModelCapability, TaskType
from agentic_qa.infrastructure.inference.circuit import CircuitBreaker
from agentic_qa.infrastructure.inference.errors import (
    ModelOutputError,
    ModelUnavailableError,
)
from agentic_qa.infrastructure.inference.metrics import InferenceMetrics
from agentic_qa.infrastructure.inference.router import ModelEndpoint
from agentic_qa.infrastructure.inference.schemas import BrowserDecision
from agentic_qa.infrastructure.inference.vllm.client import VLLMChatClient
from tests.fakes.semaphores import InMemoryResourceSemaphore

Handler = Callable[[httpx.Request], httpx.Response]


def completion(content: str, *, prompt_tokens: int = 120, completion_tokens: int = 25) -> Any:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
    }


VALID_DECISION = json.dumps(
    {"action_type": "back", "intent": "return to the listing", "rationale": "wrong page"}
)


def build_client(
    handler: Handler,
    *,
    metrics: InferenceMetrics | None = None,
    breaker: CircuitBreaker | None = None,
    max_attempts: int = 2,
    max_concurrency: int = 2,
) -> VLLMChatClient:
    endpoint = ModelEndpoint(
        name="fast",
        base_url="http://vllm:8000",
        model="test-model",
        capability=ModelCapability.FAST,
        max_concurrency=max_concurrency,
        budget=InferenceBudget(timeout_seconds=1.0, max_attempts=max_attempts),
    )
    return VLLMChatClient(
        endpoint=endpoint,
        http=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        semaphore=InMemoryResourceSemaphore(),
        metrics=metrics or InferenceMetrics(),
        breaker=breaker,
        retry_backoff_seconds=0.0,
    )


async def ask(client: VLLMChatClient) -> BrowserDecision:
    return await client.complete_json(
        task=TaskType.GUI_ACTION, system="s", user="u", schema=BrowserDecision
    )


async def test_a_valid_completion_is_returned_as_a_validated_object() -> None:
    client = build_client(lambda _: httpx.Response(200, json=completion(VALID_DECISION)))

    decision = await ask(client)

    assert decision.intent == "return to the listing"


async def test_the_request_asks_the_server_to_constrain_decoding() -> None:
    """Without `response_format` the schema is a suggestion the model may ignore."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=completion(VALID_DECISION))

    await ask(build_client(handler))

    assert str(seen[0].url) == "http://vllm:8000/v1/chat/completions"
    body: dict[str, Any] = json.loads(seen[0].content)
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["schema"]["title"] == "BrowserDecision"
    assert body["model"] == "test-model"
    # Planning is a decision, not prose: variance would make a failure harder to repeat.
    assert body["temperature"] == 0.0


async def test_output_that_violates_the_schema_is_rejected_not_repaired() -> None:
    metrics = InferenceMetrics()
    client = build_client(
        lambda _: httpx.Response(200, json=completion('{"action_type": "evaluate"}')),
        metrics=metrics,
    )

    with pytest.raises(ModelOutputError):
        await ask(client)

    assert metrics.by_endpoint["fast"].invalid_outputs == 1


async def test_output_that_is_not_json_at_all_is_rejected() -> None:
    client = build_client(
        lambda _: httpx.Response(200, json=completion("Sure! Here is what I would click."))
    )

    with pytest.raises(ModelOutputError):
        await ask(client)


async def test_a_completion_with_no_choices_is_rejected() -> None:
    client = build_client(lambda _: httpx.Response(200, json={"choices": []}))

    with pytest.raises(ModelOutputError):
        await ask(client)


async def test_a_server_error_is_retried_within_the_budget() -> None:
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=completion(VALID_DECISION))

    decision = await ask(build_client(handler, max_attempts=2))

    assert len(attempts) == 2
    assert decision.intent


async def test_a_rejected_request_is_not_retried() -> None:
    """A 400 is our request, not their weather; sending it again sends the same bytes."""
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        return httpx.Response(400, json={"error": "context length exceeded"})

    with pytest.raises(ModelUnavailableError):
        await ask(build_client(handler, max_attempts=3))

    assert len(attempts) == 1


async def test_a_timeout_exhausts_the_budget_and_then_reports_unavailable() -> None:
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        raise httpx.ReadTimeout("too slow", request=request)

    with pytest.raises(ModelUnavailableError):
        await ask(build_client(handler, max_attempts=3))

    assert len(attempts) == 3


async def test_the_slot_is_released_even_when_the_endpoint_fails() -> None:
    """A leaked slot shrinks capacity permanently after the first failure."""
    semaphore = InMemoryResourceSemaphore()
    endpoint = ModelEndpoint(
        name="fast",
        base_url="http://vllm:8000",
        model="test-model",
        capability=ModelCapability.FAST,
        budget=InferenceBudget(timeout_seconds=1.0, max_attempts=1),
    )
    client = VLLMChatClient(
        endpoint=endpoint,
        http=httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(500))),
        semaphore=semaphore,
        metrics=InferenceMetrics(),
        retry_backoff_seconds=0.0,
    )

    with pytest.raises(ModelUnavailableError):
        await ask(client)

    assert await semaphore.in_use(endpoint.slot_resource) == 0


async def test_repeated_transport_failures_stop_being_attempted() -> None:
    """A dead box should cost a run seconds, not a timeout per decision forever."""
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        return httpx.Response(500)

    breaker = CircuitBreaker(failure_threshold=2, reset_after_seconds=60.0)
    client = build_client(handler, breaker=breaker, max_attempts=1)

    for _ in range(2):
        with pytest.raises(ModelUnavailableError):
            await ask(client)
    calls_before = len(attempts)

    with pytest.raises(ModelUnavailableError, match="calls are paused"):
        await ask(client)

    assert len(attempts) == calls_before, "the tripped circuit still reached the server"


async def test_unusable_output_does_not_trip_the_circuit() -> None:
    """The endpoint is answering. Taking it offline over a prompt problem helps nobody."""
    breaker = CircuitBreaker(failure_threshold=1, reset_after_seconds=60.0)
    client = build_client(
        lambda _: httpx.Response(200, json=completion("not json")),
        breaker=breaker,
        max_attempts=1,
    )

    with pytest.raises(ModelOutputError):
        await ask(client)

    assert not breaker.is_open


async def test_latency_and_tokens_are_recorded_per_endpoint() -> None:
    metrics = InferenceMetrics()
    client = build_client(
        lambda _: httpx.Response(
            200, json=completion(VALID_DECISION, prompt_tokens=900, completion_tokens=40)
        ),
        metrics=metrics,
    )

    await ask(client)

    stats = metrics.by_endpoint["fast"]
    assert stats.calls == 1
    assert stats.prompt_tokens == 900
    assert stats.completion_tokens == 40
    assert stats.average_latency_ms >= 0
