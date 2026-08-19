"""Optional system test against a real vLLM endpoint.

Skipped unless `VLLM_BASE_URL` and `VLLM_MODEL` are set, because CI has no GPU and a
suite that silently needs one is a suite that goes red for the wrong reason. The fake
model covers the contract; this covers the claim that a real server, with real guided
decoding, actually satisfies it.

Run it against a live endpoint with:

    docker compose --profile gates run --rm \
      -e VLLM_BASE_URL=http://vllm:8000 -e VLLM_MODEL=<tag> \
      backend-tests pytest tests/inference/test_real_model.py -v
"""

import os

import httpx
import pytest

from agentic_qa.application.ports.models import PlanningRequest
from agentic_qa.bootstrap.agent_runtime import build_model_router
from agentic_qa.bootstrap.settings import Settings
from agentic_qa.infrastructure.inference.vllm.gateway import VLLMModelGateway
from tests.fakes.semaphores import InMemoryResourceSemaphore

pytestmark = pytest.mark.skipif(
    not (os.environ.get("VLLM_BASE_URL") and os.environ.get("VLLM_MODEL")),
    reason="no real model endpoint configured",
)


async def test_a_real_model_produces_a_decision_the_contract_accepts() -> None:
    settings = Settings.from_env()
    router = build_model_router(settings)
    assert router is not None

    async with httpx.AsyncClient() as http:
        gateway = VLLMModelGateway(router=router, http=http, semaphore=InMemoryResourceSemaphore())
        planned = await gateway.next_action(
            PlanningRequest(
                goal="Open the shopping cart",
                observation=(
                    "Page: http://target.test/\n"
                    "Visible controls: button 'Cart', button 'Sign in', link 'Products'"
                ),
            )
        )

    # The assertion is about the contract, not about the model's judgement: whatever it
    # decided must be a legal action or an declared failure, never something in between.
    assert planned.failure is None, f"the endpoint could not answer: {planned.failure}"
    assert planned.action is not None
    assert planned.action.intent
