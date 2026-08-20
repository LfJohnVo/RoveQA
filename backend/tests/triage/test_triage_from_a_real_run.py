"""Triage over a real failing run, end to end.

Everything else in this package proves the pieces. This proves the chain: a real
browser opens a real page, a criterion really is not met, the result lands in
PostgreSQL, and the run-boundary activity turns it into a stored cluster whose members
point back at that exact row.

The deep half is deliberately absent here — no analyst is wired — because that is the
default deployment and the Phase 11 gate about it: with no large model anywhere, the
grouping still happens, still lands, and is still worth reading.
"""

import asyncio
from dataclasses import replace
from pathlib import Path
from typing import Any

import psycopg
import pytest
from temporalio.testing import ActivityEnvironment

from agentic_qa.application.ports.deep_analysis import ClusterAnalysisRequest, ClusterHypothesis
from agentic_qa.application.ports.idempotency import FAILURE_ANALYSIS_SCOPE
from agentic_qa.infrastructure.workflows.temporal.activities import RunActivities
from agentic_qa.infrastructure.workflows.temporal.contracts import (
    AnalyzeFailuresParams,
    EpisodeParams,
    TransitionParams,
)
from tests.qa.test_evidence_chain import prepared
from tests.target_app.server import running_target_app


class RefusingAnalyst:
    """Stands in for a deep endpoint that is down — the state this system spends most
    of its life in, since the deep model is optional and usually not running."""

    async def analyze(self, request: ClusterAnalysisRequest) -> ClusterHypothesis:
        return ClusterHypothesis(cluster_id=request.cluster_id, failure="deep model unavailable")


async def run_and_triage(artifact_root: Path) -> Any:
    async with (
        running_target_app() as (base_url, _state),
        prepared(base_url, artifact_root) as (container, run_id),
    ):
        activities = RunActivities(container)
        outcome = await ActivityEnvironment().run(
            activities.run_episode, EpisodeParams(run_id=run_id, episode_index=0)
        )
        await ActivityEnvironment().run(
            activities.transition_run_status,
            TransitionParams(run_id=run_id, target_status="running"),
        )
        await ActivityEnvironment().run(
            activities.transition_run_status,
            TransitionParams(run_id=run_id, target_status="completed", verdict=outcome.verdict),
        )

        recorded = await ActivityEnvironment().run(
            activities.analyze_failures, AnalyzeFailuresParams(run_id=run_id)
        )
        # The same run again, now with a deep endpoint that refuses. The pass already
        # ran, so nothing should be asked and nothing should change.
        with_broken_deep = RunActivities(replace(container, deep_analyst=RefusingAnalyst()))
        replayed = await ActivityEnvironment().run(
            with_broken_deep.analyze_failures, AnalyzeFailuresParams(run_id=run_id)
        )

        async with container.unit_of_work() as uow:
            run = await uow.runs.get(run_id)
            assert run is not None
            clusters = await uow.failure_clusters.list_for_project(run.project_id, limit=10)
            results = await uow.criterion_results.list_for_run(run_id)
            record = await uow.idempotency.get(FAILURE_ANALYSIS_SCOPE, run_id)
        return outcome, clusters, results, record, run_id, (recorded, replayed)


def execute(artifact_root: Path) -> Any:
    try:
        return asyncio.run(run_and_triage(artifact_root))
    except (OSError, psycopg.OperationalError) as error:
        pytest.skip(f"PostgreSQL not reachable: {error}")


def test_a_real_failure_becomes_a_stored_cluster(tmp_path: Path) -> None:
    _outcome, clusters, _results, _record, run_id, _counts = execute(tmp_path)

    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.criterion_id == "ac-listing"
    assert cluster.run_ids == (run_id,)
    assert cluster.status == "independent"
    assert cluster.reason.startswith("1 failure matching")


def test_the_cluster_points_back_at_the_row_it_came_from(tmp_path: Path) -> None:
    """A member is a pointer, not a copy — so the observation and the evidence refs a
    reader follows are the ones the run actually wrote."""
    _outcome, clusters, results, _record, run_id, _counts = execute(tmp_path)

    member = clusters[0].members[0]
    assert (member.run_id, member.criterion_id) == (run_id, "ac-listing")

    result = next(item for item in results if item.criterion_id == member.criterion_id)
    assert result.evidence_refs


def test_with_no_deep_model_the_cluster_arrives_without_a_hypothesis(tmp_path: Path) -> None:
    # The gate, over a real run: nothing here needed a large model to be reachable.
    _outcome, clusters, _results, _record, _run_id, counts = execute(tmp_path)

    assert clusters[0].hypothesis is None
    assert counts == (0, 0)


def test_the_pass_is_recorded_so_a_retry_asks_nothing(tmp_path: Path) -> None:
    _outcome, _clusters, _results, record, run_id, _counts = execute(tmp_path)

    assert record is not None
    assert record.resource_id == run_id
