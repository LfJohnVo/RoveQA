"""Local embeddings from a vLLM pooling endpoint.

A separate endpoint from the generation one (ADR 0008): a pooling model and a chat
model are different servers, and sharing one would make every embedding wait behind
the planner's queue.

Deliberately small. There is no admission control or circuit breaker here, unlike the
chat client, because the failure modes are not comparable: a planner that cannot reach
its model ends the episode, while an embedder that is down costs semantic recall and
nothing else. Adding the same machinery would be protecting against a consequence that
does not exist.
"""

import logging
from collections.abc import Sequence

import httpx

from agentic_qa.infrastructure.inference.errors import ModelUnavailableError

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_BATCH = 64
"""Embedding a whole rebuild in one request is how a rebuild becomes one request that
times out. Batches keep progress incremental and the payload bounded."""


class VLLMEmbeddingGateway:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        http: httpx.AsyncClient,
        dimension: int = 0,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._http = http
        self._dimension = dimension
        self._timeout = timeout_seconds

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(texts), MAX_BATCH):
            vectors.extend(await self._embed_batch(list(texts[start : start + MAX_BATCH])))

        if len(vectors) != len(texts):
            # Silently returning fewer would attach vectors to the wrong items, and
            # the mistake would surface much later as inexplicably bad retrieval.
            raise ModelUnavailableError(
                f"embedding endpoint returned {len(vectors)} vectors for {len(texts)} inputs"
            )
        return vectors

    async def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        try:
            response = await self._http.post(
                f"{self._base_url}/v1/embeddings",
                json={"model": self._model, "input": batch},
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise ModelUnavailableError(f"embedding endpoint unreachable: {error}") from error

        data = payload.get("data")
        if not isinstance(data, list):
            raise ModelUnavailableError("embedding response has no data array")

        # Ordered by index rather than by arrival: the OpenAI contract allows the
        # server to return them out of order, and a silently reordered batch pairs
        # every vector with the wrong text.
        ordered = sorted(data, key=lambda item: int(item.get("index", 0)))
        vectors = [[float(value) for value in item["embedding"]] for item in ordered]

        if vectors and self._dimension == 0:
            self._dimension = len(vectors[0])
        if any(len(vector) != self._dimension for vector in vectors):
            raise ModelUnavailableError("embedding endpoint returned inconsistent dimensions")
        return vectors
