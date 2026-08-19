"""Routing policy: capability in, endpoint out."""

import pytest

from agentic_qa.domain.inference.tasks import (
    CAPABILITY_BY_TASK,
    ModelCapability,
    TaskType,
    capability_for,
)
from agentic_qa.infrastructure.inference.errors import NoEndpointConfiguredError
from agentic_qa.infrastructure.inference.router import ModelEndpoint, ModelRouter


def endpoint(
    name: str = "fast", capability: ModelCapability = ModelCapability.FAST
) -> ModelEndpoint:
    return ModelEndpoint(
        name=name, base_url="http://vllm:8000", model="test-model", capability=capability
    )


def test_every_task_type_declares_a_capability() -> None:
    """A task with no capability would route nowhere the first time it is used."""
    assert set(CAPABILITY_BY_TASK) == set(TaskType)


def test_planning_routes_to_the_fast_endpoint() -> None:
    router = ModelRouter([endpoint()])

    assert router.endpoint_for(TaskType.GUI_ACTION).name == "fast"


def test_a_deep_task_does_not_silently_fall_back_to_the_fast_model() -> None:
    """Answering a root-cause question on the fast model looks fine and is worth less."""
    router = ModelRouter([endpoint()])

    assert capability_for(TaskType.ROOT_CAUSE_ANALYSIS) is ModelCapability.DEEP
    with pytest.raises(NoEndpointConfiguredError):
        router.endpoint_for(TaskType.ROOT_CAUSE_ANALYSIS)


def test_capabilities_can_be_served_by_different_endpoints() -> None:
    """Phase 09/11 register pooling and deep endpoints without touching the caller."""
    router = ModelRouter([endpoint(), endpoint(name="embed", capability=ModelCapability.POOLING)])

    assert router.endpoint_for(TaskType.EMBEDDING).name == "embed"
    assert router.serves(ModelCapability.POOLING)
    assert not router.serves(ModelCapability.DEEP)


@pytest.mark.parametrize(
    "configured", ["http://vllm:8000", "http://vllm:8000/", "http://vllm:8000/v1"]
)
def test_the_base_url_is_normalized_however_it_was_configured(configured: str) -> None:
    """`/v1` is what people paste; a doubled path would look like the server is down."""
    built = ModelEndpoint(
        name="fast", base_url=configured, model="m", capability=ModelCapability.FAST
    )

    assert built.chat_completions_url == "http://vllm:8000/v1/chat/completions"


def test_an_endpoint_with_no_capacity_is_refused() -> None:
    with pytest.raises(ValueError, match="at least one call"):
        ModelEndpoint(
            name="fast",
            base_url="http://vllm:8000",
            model="m",
            capability=ModelCapability.FAST,
            max_concurrency=0,
        )


def test_slots_are_keyed_by_endpoint_not_by_task() -> None:
    """The limit belongs to the server, so every task routed there shares it."""
    assert endpoint().slot_resource == "model:fast"
