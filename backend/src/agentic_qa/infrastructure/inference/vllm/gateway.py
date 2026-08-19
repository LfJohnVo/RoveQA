"""ModelGateway backed by vLLM.

The graph is unchanged by this file's existence: it still asks a `ModelGateway` for the
next action and receives a typed `PlannedAction`. What arrives here as JSON leaves as a
domain `BrowserAction` or as a declared failure — there is no third path where a
half-understood decision reaches the browser.

Two failure modes, both ending in `PlannedAction(failure=...)` rather than an exception:

- the endpoint could not answer (down, saturated, timed out),
- the endpoint answered something unusable.

Returning a typed failure instead of raising keeps the retry split from ADR 0009
intact. Raising would surface as an activity crash and let Temporal retry the whole
episode as if the infrastructure had broken, which for a model that answered badly
would just mean asking it again from further back.
"""

import logging

import httpx

from agentic_qa.application.ports.models import PlannedAction, PlanningRequest
from agentic_qa.application.ports.semaphores import ResourceSemaphore
from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.inference.tasks import TaskType
from agentic_qa.infrastructure.inference.errors import (
    ModelOutputError,
    ModelUnavailableError,
    NoEndpointConfiguredError,
)
from agentic_qa.infrastructure.inference.metrics import InferenceMetrics
from agentic_qa.infrastructure.inference.prompts import SYSTEM_PROMPT, build_planning_prompt
from agentic_qa.infrastructure.inference.router import ModelRouter
from agentic_qa.infrastructure.inference.schemas import BrowserDecision
from agentic_qa.infrastructure.inference.vllm.client import VLLMChatClient

logger = logging.getLogger(__name__)

PLANNING_TASK = TaskType.GUI_ACTION


class VLLMModelGateway:
    """Implements `ModelGateway` (application port) over an OpenAI-compatible server."""

    def __init__(
        self,
        *,
        router: ModelRouter,
        http: httpx.AsyncClient,
        semaphore: ResourceSemaphore,
        metrics: InferenceMetrics | None = None,
    ) -> None:
        self._router = router
        self._metrics = metrics or InferenceMetrics()
        # One client per endpoint, so the circuit breaker's memory of an endpoint's
        # health survives across calls instead of resetting on every decision.
        self._clients: dict[str, VLLMChatClient] = {}
        self._http = http
        self._semaphore = semaphore

    @property
    def metrics(self) -> InferenceMetrics:
        return self._metrics

    async def next_action(self, request: PlanningRequest) -> PlannedAction:
        try:
            client = self._client_for(PLANNING_TASK)
            decision = await client.complete_json(
                task=PLANNING_TASK,
                system=SYSTEM_PROMPT,
                user=build_planning_prompt(request),
                schema=BrowserDecision,
            )
        except NoEndpointConfiguredError as error:
            return PlannedAction(action=None, failure=str(error))
        except ModelUnavailableError as error:
            return PlannedAction(action=None, failure=f"model unavailable: {error}")
        except ModelOutputError as error:
            return PlannedAction(action=None, failure=f"unusable model output: {error}")

        try:
            action = decision.to_domain_action()
        except InvalidEntityError as error:
            # The schema was satisfied but the action is not a legal one — a click with
            # no target, a write with no way to verify it. Rejected here, never sent.
            logger.warning("planner proposed an invalid action: %s", error)
            self._metrics.record_invalid_output(
                endpoint=self._router.endpoint_for(PLANNING_TASK).name,
                task=PLANNING_TASK,
                reason="invalid_action",
            )
            return PlannedAction(
                action=None, failure=f"planner proposed an invalid action: {error}"
            )

        return PlannedAction(action=action, rationale=decision.rationale)

    def _client_for(self, task: TaskType) -> VLLMChatClient:
        endpoint = self._router.endpoint_for(task)
        client = self._clients.get(endpoint.name)
        if client is None:
            client = VLLMChatClient(
                endpoint=endpoint,
                http=self._http,
                semaphore=self._semaphore,
                metrics=self._metrics,
            )
            self._clients[endpoint.name] = client
        return client
