"""The one model the projection is allowed to use: a local embedder.

Graphiti builds an OpenAI client whenever a client slot is left empty, which in a
local-first deployment is not a convenience but a silent egress. The projection avoids
that by construction rather than by configuration — it never builds the `Graphiti`
object, so there is no slot to leave empty (ADR 0008).

What remains is the adapter from our own `EmbeddingGateway` to Graphiti's embedder
interface, used to embed node names when an embedding endpoint is configured.
"""

from collections.abc import Iterable

from agentic_qa.application.ports.embeddings import EmbeddingGateway
from agentic_qa.infrastructure.knowledge.graphiti.library import (
    EmbedderClient,
)


class GraphMemoryModelUseError(RuntimeError):
    """Something asked the projection to consult a model.

    Ingestion here is deterministic by design: candidates arrive already structured and
    already deduplicated by `dedup_key`, so nothing needs a model to decide what an
    entity is or whether two facts are the same one.
    """


class GraphitiEmbedder(EmbedderClient):
    """Adapts our `EmbeddingGateway` to the interface Graphiti expects.

    The one model this projection does use, and a local one (ADR 0008). Only text is
    embedded: the token-sequence inputs the interface allows are refused rather than
    coerced, because guessing what a caller meant by a list of ints is how an
    embedding ends up computed over the wrong thing.
    """

    def __init__(self, gateway: EmbeddingGateway) -> None:
        self._gateway = gateway

    async def create(
        self, input_data: str | list[str] | Iterable[int] | Iterable[Iterable[int]]
    ) -> list[float]:
        texts = _as_texts(input_data)
        vectors = await self._gateway.embed(texts)
        # Graphiti's contract is one vector even for a list of inputs: it embeds a
        # single logical item that may arrive split into fragments.
        return vectors[0]

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        return await self._gateway.embed(input_data_list)


def _as_texts(
    input_data: str | list[str] | Iterable[int] | Iterable[Iterable[int]],
) -> list[str]:
    if isinstance(input_data, str):
        return [input_data]
    if isinstance(input_data, list) and all(isinstance(item, str) for item in input_data):
        return [" ".join(input_data)]
    raise TypeError("the embedding gateway takes text, not pre-tokenised input")
