"""Building the projection from configuration.

Kept apart from the projection itself so the composition root can decide whether
there is a graph at all without importing Graphiti. Absence is a normal state: a
deployment with no FalkorDB still learns, still retrieves and still runs — it only
loses the traversal and semantic-search layer over what PostgreSQL already holds.
"""

import logging
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

import httpx

from agentic_qa.application.ports.embeddings import EmbeddingGateway
from agentic_qa.bootstrap.settings import Settings

if TYPE_CHECKING:  # pragma: no cover - import only for the annotation
    from agentic_qa.infrastructure.knowledge.graphiti.projection import (
        GraphitiMemoryProjection,
    )

logger = logging.getLogger(__name__)

DEFAULT_FALKORDB_PORT = 6379


def build_graph_projection(
    settings: Settings, *, http: httpx.AsyncClient | None = None
) -> "GraphitiMemoryProjection | None":
    if not settings.falkordb_url:
        logger.info("no FalkorDB configured; memory is served from PostgreSQL only")
        return None

    from agentic_qa.infrastructure.knowledge.graphiti.library import FalkorDriver
    from agentic_qa.infrastructure.knowledge.graphiti.projection import GraphitiMemoryProjection

    parts = urlsplit(settings.falkordb_url)
    driver = FalkorDriver(
        host=parts.hostname or "localhost",
        port=parts.port or DEFAULT_FALKORDB_PORT,
        username=parts.username,
        password=parts.password,
        database=settings.graph_database,
    )
    return GraphitiMemoryProjection(
        driver=driver, embeddings=build_embedding_gateway(settings, http=http)
    )


def build_embedding_gateway(
    settings: Settings, *, http: httpx.AsyncClient | None = None
) -> EmbeddingGateway | None:
    """Absent unless a pooling endpoint is configured.

    Deliberately not falling back to the generation endpoint: a chat model asked for
    embeddings either refuses or returns something that is not comparable to what the
    rest of the graph was built with, and both failures surface much later as
    inexplicably bad retrieval.
    """
    if not settings.embedding_base_url or not settings.embedding_model:
        return None

    from agentic_qa.infrastructure.inference.vllm.embeddings import VLLMEmbeddingGateway

    return VLLMEmbeddingGateway(
        base_url=settings.embedding_base_url,
        model=settings.embedding_model,
        http=http if http is not None else httpx.AsyncClient(),
    )
