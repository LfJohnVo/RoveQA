"""OpenAI-compatible chat client for one model endpoint.

Named for vLLM because that is what it was written against, but it talks the
protocol rather than the product: the deep endpoint (Phase 11) is served the same
way and reuses this rather than growing a second HTTP path to keep safe.

Everything about *talking to one model server safely* lives here: admission control,
timeouts, bounded transport retries, the circuit breaker and metrics. The caller gets
either a validated Pydantic object or a typed error — never raw model text to
interpret.

Structured output is requested through `response_format: json_schema`, so vLLM
constrains decoding to the schema instead of us hoping the model formats JSON. Validation
still runs on our side: a server that ignores the field, an older vLLM, or a truncated
completion must fail closed rather than reach the browser.

Retries here cover transport only, and only for failures that carry no answer
(connection errors, timeouts, 5xx). Semantic retries belong to the graph's Recover node
and to nobody else (ADR 0009); a 4xx is a request we built wrong, and sending it again
would be the same request.
"""

import asyncio
import json
import logging
import time
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from agentic_qa.application.ports.semaphores import ResourceSemaphore, SlotReservation
from agentic_qa.domain.inference.tasks import TaskType
from agentic_qa.infrastructure.inference.circuit import CircuitBreaker
from agentic_qa.infrastructure.inference.errors import (
    ModelOutputError,
    ModelUnavailableError,
)
from agentic_qa.infrastructure.inference.metrics import InferenceMetrics
from agentic_qa.infrastructure.inference.router import ModelEndpoint

logger = logging.getLogger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)

MIN_SLOT_TTL_SECONDS = 120.0
SLOT_TTL_MARGIN = 2.0
"""Lease on a model slot, derived from the endpoint's own timeout.

It has to outlast the call it protects: a lease that expires while the call is still
running hands the slot to somebody else and puts two requests on a box sized for one.
A deep endpoint answers in minutes, so a fixed constant cannot be right for both it and
the fast one. The margin keeps the lease longer than the call while still short enough
that a killed worker frees capacity on its own."""

SLOT_POLL_SECONDS = 0.05


class VLLMChatClient:
    def __init__(
        self,
        *,
        endpoint: ModelEndpoint,
        http: httpx.AsyncClient,
        semaphore: ResourceSemaphore,
        metrics: InferenceMetrics,
        breaker: CircuitBreaker | None = None,
        retry_backoff_seconds: float = 0.5,
        slot_wait_seconds: float = 30.0,
    ) -> None:
        self._endpoint = endpoint
        self._http = http
        self._semaphore = semaphore
        self._metrics = metrics
        self._breaker = breaker or CircuitBreaker()
        self._retry_backoff = retry_backoff_seconds
        self._slot_wait = slot_wait_seconds

    async def complete_json(
        self, *, task: TaskType, system: str, user: str, schema: type[SchemaT]
    ) -> SchemaT:
        """Ask for one completion shaped like `schema`, or raise a typed error."""
        endpoint = self._endpoint
        if not self._breaker.allow():
            self._metrics.record_failure(endpoint=endpoint.name, task=task, reason="circuit_open")
            raise ModelUnavailableError(f"endpoint {endpoint.name} is failing; calls are paused")

        reservation = await self._reserve_slot()
        started = time.monotonic()
        try:
            payload = await self._post_with_retries(system=system, user=user, schema=schema)
        except ModelUnavailableError as error:
            self._breaker.record_failure()
            self._metrics.record_failure(
                endpoint=endpoint.name, task=task, reason=type(error).__name__
            )
            raise
        finally:
            await self._semaphore.release(reservation)

        self._breaker.record_success()
        usage = payload.get("usage") or {}
        self._metrics.record_call(
            endpoint=endpoint.name,
            task=task,
            latency_ms=(time.monotonic() - started) * 1000,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
        )
        return self._parse(payload, schema=schema, task=task)

    async def _reserve_slot(self) -> SlotReservation:
        """Wait, bounded, for one of the endpoint's slots.

        Waiting is right here: a busy GPU is not a failure, it is a queue. Waiting
        *forever* would be, so the wait has a deadline and saturation is then reported
        as unavailability.
        """
        endpoint = self._endpoint
        deadline = time.monotonic() + self._slot_wait
        while True:
            reservation = await self._semaphore.acquire(
                endpoint.slot_resource,
                capacity=endpoint.max_concurrency,
                ttl_seconds=max(
                    MIN_SLOT_TTL_SECONDS, endpoint.budget.timeout_seconds * SLOT_TTL_MARGIN
                ),
            )
            if reservation is not None:
                return reservation
            if time.monotonic() >= deadline:
                raise ModelUnavailableError(
                    f"endpoint {endpoint.name} stayed at capacity "
                    f"({endpoint.max_concurrency}) for {self._slot_wait:.0f}s"
                )
            await asyncio.sleep(SLOT_POLL_SECONDS)

    async def _post_with_retries(
        self, *, system: str, user: str, schema: type[BaseModel]
    ) -> dict[str, Any]:
        endpoint = self._endpoint
        body = {
            "model": endpoint.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": endpoint.budget.max_output_tokens,
            # Planning is a decision, not prose: sampling variance here buys nothing
            # and makes a failing run harder to reproduce.
            "temperature": 0.0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                    "strict": True,
                },
            },
        }

        last_error: Exception | None = None
        for attempt in range(1, endpoint.budget.max_attempts + 1):
            try:
                response = await self._http.post(
                    endpoint.chat_completions_url,
                    json=body,
                    timeout=endpoint.budget.timeout_seconds,
                )
            except (httpx.TimeoutException, httpx.TransportError) as error:
                last_error = error
            else:
                if response.status_code < 400:
                    return self._decode_envelope(response)
                if response.status_code < 500:
                    # Our request, not their weather. Retrying sends the same bytes.
                    raise ModelUnavailableError(
                        f"endpoint {endpoint.name} rejected the request ({response.status_code})"
                    )
                last_error = ModelUnavailableError(
                    f"endpoint {endpoint.name} returned {response.status_code}"
                )

            if attempt < endpoint.budget.max_attempts:
                logger.info(
                    "retrying %s after transport failure (attempt %d/%d)",
                    endpoint.name,
                    attempt,
                    endpoint.budget.max_attempts,
                )
                await asyncio.sleep(self._retry_backoff * attempt)

        raise ModelUnavailableError(
            f"endpoint {endpoint.name} unreachable after "
            f"{endpoint.budget.max_attempts} attempts: {last_error}"
        )

    def _decode_envelope(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as error:
            raise ModelUnavailableError(
                f"endpoint {self._endpoint.name} answered with non-JSON body"
            ) from error
        if not isinstance(payload, dict):
            raise ModelUnavailableError(
                f"endpoint {self._endpoint.name} answered with an unexpected body"
            )
        return payload

    def _parse(self, payload: dict[str, Any], *, schema: type[SchemaT], task: TaskType) -> SchemaT:
        """Validate the completion. Nothing is coerced, repaired or guessed."""
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            self._reject(task, "malformed_envelope")
            raise ModelOutputError(
                f"endpoint {self._endpoint.name} returned no completion"
            ) from error

        if not isinstance(content, str):
            self._reject(task, "non_text_completion")
            raise ModelOutputError(f"endpoint {self._endpoint.name} returned no text")

        try:
            return schema.model_validate_json(content)
        except (ValidationError, json.JSONDecodeError) as error:
            # The offending text is not logged: it is model output derived from an
            # untrusted page and may carry fixture credentials (docs/13).
            self._reject(task, "schema_violation")
            raise ModelOutputError(
                f"endpoint {self._endpoint.name} produced output that does not "
                f"satisfy {schema.__name__}"
            ) from error

    def _reject(self, task: TaskType, reason: str) -> None:
        self._metrics.record_invalid_output(endpoint=self._endpoint.name, task=task, reason=reason)
