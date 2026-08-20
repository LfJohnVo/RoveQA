"""The FalkorDB projection of durable knowledge (ADR 0008).

Graphiti supplies the graph model and the driver. It does *not* supply the ingestion
or the search here, and both omissions are deliberate:

**Ingestion.** `add_episode` and `add_triplet` run an LLM to discover entities and to
decide when two of them are the same thing. Neither job exists in this system: the
candidates arriving from PostgreSQL are already structured, and their identity is a
deterministic `dedup_key`. Handing identity to a model would put a guess in charge of
what counts as the same fact — the one thing this bounded context refuses everywhere
else. So nodes are written directly, with UUIDs derived from the candidate id, which
also makes every write idempotent and a rebuild reproduce the same identities.

**Search.** Graphiti's search pipeline exists to fuse several retrieval methods and
rerank them with a cross-encoder. We want the opposite: a scoped list of candidate ids,
ordered afterwards by reliability, freshness and compatibility in the domain. One
full-text query gives exactly that, and asking the library's pipeline for it meant
fighting three separate FalkorDB incompatibilities for a ranking we then discarded.

Not constructing `Graphiti` at all has a second benefit worth more than the code it
saves: that constructor builds an OpenAI LLM client and embedder whenever those slots
are left empty. There is no slot here to leave empty, so a local-first deployment
cannot acquire a hosted dependency by omission.
"""

import hashlib
import logging
import uuid
from typing import Any

from agentic_qa.application.ports.embeddings import EmbeddingGateway
from agentic_qa.application.ports.graph import GraphHit, GraphUnavailableError
from agentic_qa.domain.knowledge.experience import KnowledgeExperienceCandidate, summarize
from agentic_qa.infrastructure.knowledge.graphiti.clients import GraphitiEmbedder
from agentic_qa.infrastructure.knowledge.graphiti.library import (
    EntityNode,
    FalkorDriver,
    GraphProvider,
    get_fulltext_indices,
)

logger = logging.getLogger(__name__)

CANDIDATE_LABEL = "KnowledgeCandidate"

_NAMESPACE = uuid.UUID("6f0d2a2e-7f1e-4d2b-9f4a-1a1b2c3d4e5f")
"""Fixed namespace for candidate node UUIDs.

Derived rather than random so the same candidate always occupies the same node: two
syncs update one node, and a rebuild recreates the graph the runs already referenced
instead of a parallel copy of it.
"""

_SEARCH = (
    "CALL db.idx.fulltext.queryNodes('Entity', $query) YIELD node, score "
    "WHERE node.group_id = $group_id "
    "RETURN node.candidate_id AS candidate_id, score ORDER BY score DESC LIMIT $limit"
)
"""Scoped full-text lookup.

The scope is an equality test on a property, not a term inside the full-text query.
FalkorDB indexes `group_id` as full text as well, and matching it as a phrase fails
whenever the tokenizer splits the value — which silently returned zero results for
every search. An equality predicate cannot be confused by tokenization.
"""

_PROJECT_NODES = "MATCH (n:Entity) WHERE n.project_id = $project_id RETURN n.uuid AS uuid"
"""Nodes belonging to one project, matched on the exact id stored on each node.

Never on a group-id prefix: group ids are digests, so a prefix match could reach a
different scope entirely — wiping memory nobody asked to rebuild.
"""


def group_id_for(project_id: str, environment_id: str) -> str:
    """Graphiti's tenancy key: one opaque alphanumeric token.

    Graphiti restricts this value to letters, digits, `-` and `_`, and sanitising to
    fit would not be injective — two different scopes could reduce to the same string
    and share a projection. A digest of the untouched pair cannot collide in practice,
    and the readable values travel on each node instead (`project_id`,
    `environment_id`), which is where a human browsing the graph would look anyway.
    """
    return hashlib.sha256(f"{project_id}::{environment_id}".encode()).hexdigest()[:32]


def node_uuid_for(candidate_id: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, candidate_id))


class GraphitiMemoryProjection:
    """Implements `GraphMemoryPort` over FalkorDB."""

    def __init__(
        self,
        *,
        driver: FalkorDriver,
        embeddings: EmbeddingGateway | None = None,
    ) -> None:
        self._driver = driver
        self._embedder = GraphitiEmbedder(embeddings) if embeddings is not None else None
        self._indices_ready = False
        _cancel_library_index_setup(driver)

    async def materialize(self, candidate: KnowledgeExperienceCandidate) -> str:
        await self._ready()
        node = self._node_for(candidate)
        try:
            if self._embedder is not None:
                # Only when an embedding endpoint is configured. Without one the node
                # still lands and stays findable by text.
                await node.generate_name_embedding(self._embedder)
            await node.save(self._driver)
        except Exception as error:
            raise GraphUnavailableError(
                f"writing candidate to the graph failed: {error}"
            ) from error
        return node.uuid

    async def forget(self, candidate_id: str) -> None:
        try:
            await EntityNode.delete_by_uuids(self._driver, [node_uuid_for(candidate_id)])
        except Exception as error:
            raise GraphUnavailableError(
                f"removing a candidate from the graph failed: {error}"
            ) from error

    async def search(
        self, query: str, *, project_id: str, environment_id: str, limit: int = 20
    ) -> list[GraphHit]:
        await self._ready()
        terms = self._driver.build_fulltext_query(query)
        if not terms:
            # Nothing searchable survived tokenization (stopwords only, or empty). An
            # unfiltered query would return the whole scope, which is not "no answer".
            return []

        try:
            records, _, _ = await self._driver.execute_query(
                _SEARCH,
                query=terms,
                group_id=group_id_for(project_id, environment_id),
                limit=limit,
            )
        except Exception as error:
            raise GraphUnavailableError(f"searching the graph failed: {error}") from error

        return [
            GraphHit(candidate_id=str(record["candidate_id"]), score=float(record["score"]))
            for record in records
            if record.get("candidate_id")
        ]

    async def clear(self, project_id: str) -> None:
        """Drop every environment's projection for one project."""
        try:
            records, _, _ = await self._driver.execute_query(_PROJECT_NODES, project_id=project_id)
            uuids = [str(record["uuid"]) for record in records]
            if uuids:
                await EntityNode.delete_by_uuids(self._driver, uuids)
        except Exception as error:
            raise GraphUnavailableError(f"clearing the graph failed: {error}") from error

    async def is_available(self) -> bool:
        try:
            await self._driver.execute_query("RETURN 1")
        except Exception as error:  # noqa: BLE001 - a status check must never raise
            logger.info("graph store is not reachable: %s", error)
            return False
        return True

    async def build_indices(self) -> None:
        """Create exactly the indices this projection needs. Idempotent."""
        for statement in self._index_statements():
            try:
                await self._driver.execute_query(statement)
            except Exception as error:  # noqa: BLE001 - an existing index is not a failure
                logger.debug("index statement skipped (%s): %s", error, statement.strip()[:80])

    async def aclose(self) -> None:
        await self._driver.close()

    async def _ready(self) -> None:
        """Ensure the indices exist, once per instance.

        Lazy rather than done in the constructor: building a projection stays cheap, and
        a store that happens to be down does not turn construction into a failure.
        """
        if self._indices_ready:
            return
        await self.build_indices()
        self._indices_ready = True

    def _index_statements(self) -> list[str]:
        """Range indices for the properties we filter on, plus the `Entity` full-text
        index taken from the library.

        The full-text one comes from Graphiti rather than being written here so its
        label and property set stay the ones `build_fulltext_query` expects; selecting
        it by label means a future version that changes the shape breaks a test instead
        of silently returning nothing.
        """
        statements = [
            "CREATE INDEX FOR (n:Entity) ON (n.uuid)",
            "CREATE INDEX FOR (n:Entity) ON (n.group_id)",
            "CREATE INDEX FOR (n:Entity) ON (n.project_id)",
        ]
        statements.extend(
            statement
            for statement in get_fulltext_indices(GraphProvider.FALKORDB)
            if "label: 'Entity'" in statement
        )
        return statements

    def _node_for(self, candidate: KnowledgeExperienceCandidate) -> EntityNode:
        summary = summarize(candidate)
        return EntityNode(
            uuid=node_uuid_for(candidate.candidate_id),
            name=summary,
            group_id=group_id_for(candidate.project_id, candidate.environment_id),
            labels=[CANDIDATE_LABEL, candidate.kind.value],
            created_at=candidate.created_at,
            summary=summary,
            attributes=_attributes(candidate),
        )


def _cancel_library_index_setup(driver: FalkorDriver) -> None:
    """Stop Graphiti's own index build before it can run.

    `FalkorDriver.__init__` schedules `build_indices_and_constraints()` as a background
    task. Several of the statements it emits are composite indices FalkorDB 4.20.3
    rejects, and it rejects them by *closing the connection* — which aborts the rest of
    that loop and leaves the connection broken for whatever ran next.

    Cancelling is safe: the task is only scheduled, never started, while this
    synchronous constructor runs, and `build_indices` creates exactly what this
    projection needs. Indexing structures we never write was pointless before it was
    harmful.
    """
    task = getattr(driver, "_init_task", None)
    if task is not None and not task.done():
        task.cancel()


def _attributes(candidate: KnowledgeExperienceCandidate) -> dict[str, Any]:
    """What travels into the graph, and nothing else.

    The payload is deliberately not copied. It has already been redacted, but the graph
    is browsed by humans and traversed by retrieval, and duplicating captured page
    content into a second store adds a second place a leak could come from for no
    retrieval benefit — the summary is what search matches on. The durable row remains
    the place to read the detail.
    """
    return {
        "candidate_id": candidate.candidate_id,
        # Stored so `clear` can match a project exactly rather than by a digest prefix,
        # and so a human browsing the graph sees the real scope behind the group id.
        "project_id": candidate.project_id,
        "environment_id": candidate.environment_id,
        "kind": candidate.kind.value,
        # Carried so someone reading the graph can tell a verified fact from a model's
        # hypothesis without going back to PostgreSQL.
        "observed": candidate.observed,
        "model_derived": candidate.model_derived,
        "reliability": candidate.quality.reliability,
        "support_count": candidate.quality.support_count,
        "source_run_id": candidate.provenance.source_run_id,
        "app_version": candidate.validity.app_version or "",
        "page_fingerprint": candidate.validity.page_fingerprint or "",
        "role": candidate.validity.role or "",
        "origin": candidate.validity.origin or "",
    }
