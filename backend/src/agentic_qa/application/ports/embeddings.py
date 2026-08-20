"""Embedding gateway port.

A separate port from `ModelGateway` because the two fail differently and are allowed
to fail differently. A planner without a model cannot decide anything and the episode
ends unresolved; an embedder that is down only costs semantic recall, and the graph
still answers by traversal and by the deterministic ranking in PostgreSQL.

Local by decision, not by accident (ADR 0008). Graphiti will happily default to a
hosted provider if nothing is injected, which would turn a local-first deployment into
one that quietly sends page-derived text to a third party.
"""

from collections.abc import Sequence
from typing import Protocol


class EmbeddingGateway(Protocol):
    @property
    def model(self) -> str:
        """Which model produced the vectors.

        Recorded with the projection: embeddings from two different models are not
        comparable, so a model change is a rebuild rather than a silent drift in what
        "similar" means.
        """
        ...

    @property
    def dimension(self) -> int: ...

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Vectors in the same order as the inputs.

        Raises rather than returning short or padded output: a caller that silently
        received fewer vectors than texts would attach them to the wrong items.
        """
        ...
