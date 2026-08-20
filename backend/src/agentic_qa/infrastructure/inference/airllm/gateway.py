"""DeepAnalyst backed by AirLLM.

AirLLM runs a model far larger than the GPU by streaming its layers, which buys depth
at the cost of minutes per answer. That trade is only acceptable off the browser loop,
so this adapter is reached at run boundaries and nowhere else (docs/08).

It speaks the same OpenAI-compatible protocol as the fast endpoint and therefore reuses
the same client: admission control, timeouts, the circuit breaker and structured-output
validation are already solved there, and a second HTTP path would be a second place for
an unbounded call to hide. What differs is entirely configuration — a long timeout, one
slot, and no blind transport retry of a call that costs minutes.

Failures come back as `ClusterHypothesis(failure=...)` rather than as exceptions. A
deep endpoint that is down must leave the run reporting exactly what triage found, not
turn a finished run into a crashed one.
"""

import logging
from uuid import uuid4

import httpx

from agentic_qa.application.ports.deep_analysis import (
    ClusterAnalysisRequest,
    ClusterHypothesis,
    HypothesisConfidence,
)
from agentic_qa.application.ports.models import ModelInvocation
from agentic_qa.application.ports.semaphores import ResourceSemaphore
from agentic_qa.domain.inference.tasks import TaskType
from agentic_qa.infrastructure.inference.errors import (
    ModelOutputError,
    ModelUnavailableError,
    NoEndpointConfiguredError,
)
from agentic_qa.infrastructure.inference.metrics import InferenceMetrics
from agentic_qa.infrastructure.inference.prompts import (
    DEEP_ANALYSIS_PROMPT_VERSION,
    DEEP_ANALYSIS_SYSTEM_PROMPT,
    build_cluster_analysis_prompt,
)
from agentic_qa.infrastructure.inference.router import ModelRouter
from agentic_qa.infrastructure.inference.schemas import ClusterAnalysis
from agentic_qa.infrastructure.inference.vllm.client import VLLMChatClient

logger = logging.getLogger(__name__)

ANALYSIS_TASK = TaskType.ROOT_CAUSE_ANALYSIS


class AirLLMDeepAnalyst:
    """Implements `DeepAnalyst` (application port) over the DEEP-capability endpoint."""

    def __init__(
        self,
        *,
        router: ModelRouter,
        http: httpx.AsyncClient,
        semaphore: ResourceSemaphore,
        metrics: InferenceMetrics | None = None,
    ) -> None:
        self._router = router
        self._http = http
        self._semaphore = semaphore
        self._metrics = metrics or InferenceMetrics()
        self._client: VLLMChatClient | None = None

    @property
    def metrics(self) -> InferenceMetrics:
        return self._metrics

    async def analyze(self, request: ClusterAnalysisRequest) -> ClusterHypothesis:
        try:
            analysis = await self._deep_client().complete_json(
                task=ANALYSIS_TASK,
                system=DEEP_ANALYSIS_SYSTEM_PROMPT,
                user=build_cluster_analysis_prompt(request),
                schema=ClusterAnalysis,
            )
        except NoEndpointConfiguredError as error:
            return ClusterHypothesis(cluster_id=request.cluster_id, failure=str(error))
        except ModelUnavailableError as error:
            return ClusterHypothesis(
                cluster_id=request.cluster_id, failure=f"deep model unavailable: {error}"
            )
        except ModelOutputError as error:
            return ClusterHypothesis(
                cluster_id=request.cluster_id, failure=f"unusable deep model output: {error}"
            )

        return ClusterHypothesis(
            cluster_id=request.cluster_id,
            probable_cause=analysis.probable_cause,
            recommended_check=analysis.recommended_check,
            confidence=HypothesisConfidence(analysis.confidence),
            invocation=ModelInvocation(
                invocation_id=str(uuid4()),
                model=self._router.endpoint_for(ANALYSIS_TASK).model,
                prompt_version=DEEP_ANALYSIS_PROMPT_VERSION,
            ),
        )

    def _deep_client(self) -> VLLMChatClient:
        """One client for the endpoint, so its circuit breaker remembers across calls.

        Built lazily and not cached until the router actually resolves an endpoint: a
        worker with no deep endpoint configured must fail on the call, not at wiring.
        """
        if self._client is None:
            self._client = VLLMChatClient(
                endpoint=self._router.endpoint_for(ANALYSIS_TASK),
                http=self._http,
                semaphore=self._semaphore,
                metrics=self._metrics,
            )
        return self._client
