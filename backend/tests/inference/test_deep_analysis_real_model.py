"""Optional system test against a real deep endpoint.

Skipped unless `DEEP_BASE_URL` and `DEEP_MODEL` are set. The mock-transport tests cover
the contract; this covers the claim that a real server, with real guided decoding,
actually satisfies it — which is where every earlier phase found the defects that fakes
could not.

Any OpenAI-compatible server works. Against the bigger model this endpoint exists for:

    docker compose --profile deep-gpu up -d vllm-deep
    docker compose --profile gates run --rm \
      -e DEEP_BASE_URL=http://vllm-deep:8000 -e DEEP_MODEL=<tag> \
      backend-tests pytest tests/inference/test_deep_analysis_real_model.py -v
"""

import os

import httpx
import pytest

from agentic_qa.application.ports.deep_analysis import ClusterAnalysisRequest
from agentic_qa.bootstrap.agent_runtime import build_model_router
from agentic_qa.bootstrap.settings import Settings
from agentic_qa.domain.inference.tasks import ModelCapability
from agentic_qa.infrastructure.inference.airllm.gateway import AirLLMDeepAnalyst
from agentic_qa.infrastructure.inference.router import ModelRouter
from tests.fakes.semaphores import InMemoryResourceSemaphore

pytestmark = pytest.mark.skipif(
    not (os.environ.get("DEEP_BASE_URL") and os.environ.get("DEEP_MODEL")),
    reason="no real deep endpoint configured",
)

CLUSTER = ClusterAnalysisRequest(
    cluster_id="product:realcheck",
    failure_kind="product",
    criterion_id="ac-checkout",
    observation="the order confirmation page never appeared after submitting payment",
    grouping_reason=(
        "12 failures matching product on ac-checkout, HTTP 503, route /checkout/confirm"
    ),
    affected_runs=12,
    route="/checkout/confirm",
    http_status="503",
)


def configured_router() -> ModelRouter:
    router = build_model_router(Settings.from_env())
    assert router is not None
    assert router.serves(ModelCapability.DEEP)
    return router


def analyst(http: httpx.AsyncClient) -> AirLLMDeepAnalyst:
    return AirLLMDeepAnalyst(
        router=configured_router(), http=http, semaphore=InMemoryResourceSemaphore()
    )


async def test_a_real_deep_model_produces_a_hypothesis_the_contract_accepts() -> None:
    async with httpx.AsyncClient() as http:
        hypothesis = await analyst(http).analyze(CLUSTER)

    # About the contract, not the model's judgement: whatever it concluded arrives as a
    # labelled hypothesis with a check attached, or as a declared failure. Never as
    # something in between, and never as an observation.
    assert hypothesis.failure is None, f"the endpoint could not answer: {hypothesis.failure}"
    assert hypothesis.probable_cause
    assert hypothesis.recommended_check
    assert hypothesis.model_derived is True
    assert hypothesis.invocation is not None
    assert hypothesis.invocation.model == Settings.from_env().deep_model


async def test_the_hypothesis_stays_attached_to_the_cluster_it_was_asked_about() -> None:
    """The model is shown a summary and no evidence, so anything it said about *which*
    runs are in the cluster would be invention. The schema gives it nowhere to say it,
    and the cluster id on the way out is ours, never the model's."""
    async with httpx.AsyncClient() as http:
        hypothesis = await analyst(http).analyze(CLUSTER)

    assert hypothesis.failure is None
    assert hypothesis.cluster_id == CLUSTER.cluster_id
