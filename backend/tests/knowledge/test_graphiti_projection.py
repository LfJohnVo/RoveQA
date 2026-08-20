"""The projection against a real FalkorDB.

The in-memory double proves the sync logic; this proves the adapter. They test
different things, and the failures that only show up here are the ones that matter:
a Cypher query that FalkorDB rejects, a node identity that is not stable across
processes, a scope that leaks because `group_id` was not what filtered.

Skipped rather than mocked when FalkorDB is unreachable, with the URL in the reason.
A green suite that silently never touched the store would be worse than a red one.
"""

import asyncio
import inspect
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from agentic_qa.domain.knowledge.experience import (
    CandidateKind,
    CandidateStatus,
    KnowledgeExperienceCandidate,
    Provenance,
    Quality,
    Validity,
)
from agentic_qa.infrastructure.knowledge.graphiti.projection import (
    GraphitiMemoryProjection,
    group_id_for,
    node_uuid_for,
)

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)

DEFAULT_FALKORDB_TEST_URL = "redis://localhost:6380"


def falkordb_test_url() -> str:
    return os.environ.get("FALKORDB_TEST_URL", DEFAULT_FALKORDB_TEST_URL)


def candidate(
    project_id: str,
    *,
    summary: str,
    kind: CandidateKind = CandidateKind.PLAYBOOK,
    environment_id: str = "staging",
    observed: bool = True,
) -> KnowledgeExperienceCandidate:
    return KnowledgeExperienceCandidate(
        candidate_id=f"cand-{uuid4()}",
        project_id=project_id,
        environment_id=environment_id,
        kind=kind,
        observed=observed,
        model_derived=not observed,
        created_at=NOW,
        provenance=Provenance(source_run_id="run-1"),
        validity=Validity(valid_from=NOW, app_version="2.1.0", role="admin"),
        payload={"summary": summary},
        status=CandidateStatus.PROMOTED,
        quality=Quality(support_count=3, success_count=3, last_verified_at=NOW),
    )


@asynccontextmanager
async def projection() -> AsyncIterator[GraphitiMemoryProjection]:
    """A projection over a disposable graph, torn down whatever the test did."""
    from urllib.parse import urlsplit

    from agentic_qa.infrastructure.knowledge.graphiti.library import FalkorDriver

    parts = urlsplit(falkordb_test_url())
    driver = FalkorDriver(
        host=parts.hostname or "localhost",
        port=parts.port or 6379,
        # A graph of its own per test run: these tests wipe what they touch.
        database=f"roveqa_test_{uuid4().hex[:8]}",
    )
    graph = GraphitiMemoryProjection(driver=driver)
    if not await graph.is_available():
        await graph.aclose()
        pytest.skip(f"FalkorDB not reachable at {falkordb_test_url()}")
    # Indices are what make text search work at all; production creates them at
    # startup, so a test on a fresh graph has to do the same or it would be measuring
    # an unindexed store nobody runs.
    await graph.build_indices()
    try:
        yield graph
    finally:
        await graph.aclose()


def execute(scenario: Any) -> Any:
    try:
        return asyncio.run(scenario())
    except OSError as error:  # pragma: no cover - store not reachable at all
        pytest.skip(f"FalkorDB not reachable at {falkordb_test_url()}: {error}")


def test_a_candidate_is_written_and_found_again() -> None:
    async def scenario() -> Any:
        async with projection() as graph:
            project_id = f"proj-{uuid4().hex[:8]}"
            item = candidate(project_id, summary="the records page is reachable from the header")
            node_id = await graph.materialize(item)
            hits = await graph.search(
                "records page", project_id=project_id, environment_id="staging"
            )
            return item, node_id, hits

    item, node_id, hits = execute(scenario)

    # Identity derived from the candidate, so two syncs update one node and a rebuild
    # recreates the graph the runs already referenced.
    assert node_id == node_uuid_for(item.candidate_id)
    assert [hit.candidate_id for hit in hits] == [item.candidate_id]


def test_writing_the_same_candidate_twice_leaves_one_node() -> None:
    async def scenario() -> Any:
        async with projection() as graph:
            project_id = f"proj-{uuid4().hex[:8]}"
            item = candidate(project_id, summary="checkout is reachable from the cart")
            first = await graph.materialize(item)
            second = await graph.materialize(item)
            hits = await graph.search("checkout", project_id=project_id, environment_id="staging")
            return first, second, hits

    first, second, hits = execute(scenario)

    assert first == second
    # Idempotent by construction: a retried sync and a rebuild are both safe.
    assert len(hits) == 1


def test_a_forgotten_candidate_stops_being_found() -> None:
    async def scenario() -> Any:
        async with projection() as graph:
            project_id = f"proj-{uuid4().hex[:8]}"
            item = candidate(project_id, summary="a route that was later removed")
            await graph.materialize(item)
            await graph.forget(item.candidate_id)
            return await graph.search("route", project_id=project_id, environment_id="staging")

    assert execute(scenario) == []


def test_a_search_cannot_reach_another_project() -> None:
    async def scenario() -> Any:
        async with projection() as graph:
            mine = f"proj-{uuid4().hex[:8]}"
            theirs = f"proj-{uuid4().hex[:8]}"
            await graph.materialize(candidate(mine, summary="my own login playbook"))
            await graph.materialize(candidate(theirs, summary="their own login playbook"))
            return await graph.search("login playbook", project_id=mine, environment_id="staging")

    hits = execute(scenario)

    # One project's knowledge, because group_id is what filtered inside the query.
    assert len(hits) == 1


def test_a_search_cannot_reach_another_environment() -> None:
    async def scenario() -> Any:
        async with projection() as graph:
            project_id = f"proj-{uuid4().hex[:8]}"
            await graph.materialize(
                candidate(project_id, summary="staging login form", environment_id="staging")
            )
            await graph.materialize(
                candidate(project_id, summary="production login form", environment_id="production")
            )
            return await graph.search(
                "login form", project_id=project_id, environment_id="production"
            )

    hits = execute(scenario)
    assert len(hits) == 1


def test_clearing_a_project_leaves_other_projects_alone() -> None:
    async def scenario() -> Any:
        async with projection() as graph:
            mine = f"proj-{uuid4().hex[:8]}"
            theirs = f"proj-{uuid4().hex[:8]}"
            await graph.materialize(candidate(mine, summary="my dashboard route"))
            kept = candidate(theirs, summary="their dashboard route")
            await graph.materialize(kept)

            await graph.clear(mine)

            mine_hits = await graph.search(
                "dashboard route", project_id=mine, environment_id="staging"
            )
            theirs_hits = await graph.search(
                "dashboard route", project_id=theirs, environment_id="staging"
            )
            return mine_hits, theirs_hits, kept

    mine_hits, theirs_hits, kept = execute(scenario)

    assert mine_hits == []
    # A rebuild of one project must not wipe another's projection.
    assert [hit.candidate_id for hit in theirs_hits] == [kept.candidate_id]


def test_clearing_a_project_removes_every_environment_it_had() -> None:
    async def scenario() -> Any:
        async with projection() as graph:
            project_id = f"proj-{uuid4().hex[:8]}"
            await graph.materialize(
                candidate(project_id, summary="a staging route", environment_id="staging")
            )
            await graph.materialize(
                candidate(project_id, summary="a production route", environment_id="production")
            )
            await graph.clear(project_id)
            return [
                await graph.search("route", project_id=project_id, environment_id=environment)
                for environment in ("staging", "production")
            ]

    assert execute(scenario) == [[], []]


def test_the_labels_a_human_needs_travel_into_the_graph() -> None:
    async def scenario() -> Any:
        async with projection() as graph:
            from graphiti_core.nodes import EntityNode

            project_id = f"proj-{uuid4().hex[:8]}"
            item = candidate(project_id, summary="a guessed shortcut", observed=False)
            await graph.materialize(item)
            node = await EntityNode.get_by_uuid(
                graph._driver,  # noqa: SLF001 - inspecting what was actually stored
                node_uuid_for(item.candidate_id),
            )
            return item, node

    item, node = execute(scenario)

    # Someone browsing the graph can tell a verified fact from a model's hypothesis
    # without going back to PostgreSQL.
    assert node.attributes["model_derived"] is True
    assert node.attributes["observed"] is False
    assert node.attributes["candidate_id"] == item.candidate_id
    assert node.group_id == group_id_for(item.project_id, item.environment_id)


def test_the_payload_is_not_copied_into_the_graph() -> None:
    async def scenario() -> Any:
        async with projection() as graph:
            from graphiti_core.nodes import EntityNode

            project_id = f"proj-{uuid4().hex[:8]}"
            item = candidate(project_id, summary="a summary worth searching")
            await graph.materialize(item)
            node = await EntityNode.get_by_uuid(
                graph._driver,  # noqa: SLF001
                node_uuid_for(item.candidate_id),
            )
            return node

    node = execute(scenario)

    # Captured detail stays in one place. Duplicating it into a second store adds a
    # second place a leak could come from for no retrieval benefit.
    assert "payload" not in node.attributes


def test_the_projection_never_builds_a_hosted_client() -> None:
    """The guard against acquiring a hosted dependency by omission.

    Graphiti's orchestrator builds an OpenAI LLM client and embedder for any client
    slot left empty. The projection avoids that by never constructing it — asserted
    here rather than trusted, because the failure mode is a local-first deployment
    quietly sending page-derived text to a third party.
    """
    text = inspect.getsource(inspect.getmodule(GraphitiMemoryProjection))  # type: ignore[arg-type]

    assert "Graphiti(" not in text
    assert "llm_client" not in text
    # And the module that does import the library exposes no LLM surface to import.
    from agentic_qa.infrastructure.knowledge.graphiti import library

    assert not [name for name in library.__all__ if "LLM" in name or "CrossEncoder" in name]
