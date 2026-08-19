"""Model routing policy.

The domain asks for a `TaskType`; this maps it to a capability and then to whichever
endpoint is configured to serve that capability. Model names live here and in the
environment, never in a use case (docs/08).

The shape is deliberately capability-indexed rather than task-indexed so Phase 09 can
register a `POOLING` endpoint for embeddings, and Phase 11 a `DEEP` one for AirLLM,
without touching anything above.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field

from agentic_qa.domain.inference.tasks import (
    InferenceBudget,
    ModelCapability,
    TaskType,
    capability_for,
)
from agentic_qa.infrastructure.inference.errors import NoEndpointConfiguredError


@dataclass(frozen=True)
class ModelEndpoint:
    """One OpenAI-compatible server.

    `max_concurrency` is the real limit of the box behind it: a single GPU serving
    generation cannot absorb unbounded parallel runs, so admission is bounded before
    the request is sent rather than by letting requests queue and time out.
    """

    name: str
    base_url: str
    model: str
    capability: ModelCapability
    max_concurrency: int = 1
    budget: InferenceBudget = field(default_factory=InferenceBudget)

    def __post_init__(self) -> None:
        if self.max_concurrency < 1:
            raise ValueError(f"endpoint {self.name} needs capacity for at least one call")
        # Both "http://vllm:8000" and "http://vllm:8000/v1" are what people paste into
        # an OpenAI-compatible base URL. Normalizing here beats a 404 that looks like
        # the model server being down.
        object.__setattr__(self, "base_url", self.base_url.rstrip("/").removesuffix("/v1"))

    @property
    def chat_completions_url(self) -> str:
        return f"{self.base_url}/v1/chat/completions"

    @property
    def slot_resource(self) -> str:
        """Semaphore key. Shared by every task routed to this endpoint, which is the
        point: the limit belongs to the server, not to a kind of question."""
        return f"model:{self.name}"


class ModelRouter:
    """Chooses the endpoint for a task. First registered wins per capability."""

    def __init__(self, endpoints: Iterable[ModelEndpoint]) -> None:
        self._by_capability: dict[ModelCapability, ModelEndpoint] = {}
        for endpoint in endpoints:
            self._by_capability.setdefault(endpoint.capability, endpoint)

    def endpoint_for(self, task: TaskType) -> ModelEndpoint:
        capability = capability_for(task)
        endpoint = self._by_capability.get(capability)
        if endpoint is None:
            # Failing loudly beats silently downgrading a deep-analysis task onto the
            # fast model: the answer would look fine and be worth much less.
            raise NoEndpointConfiguredError(capability)
        return endpoint

    def serves(self, capability: ModelCapability) -> bool:
        return capability in self._by_capability
