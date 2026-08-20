"""What a real run actually learns.

Everything else about consolidation is tested against constructed inputs. This drives
the same wiring the worker uses — a real browser against a real page, real evidence,
the real activity — because the interesting failures live in the seams: a run that
learns nothing because no recovery point was written, or a page's own text arriving
in the payload unredacted.

The run under test fails (the page never confirms the criterion), which is the more
demanding case: a verified failure is a fact worth keeping, not a missing result.
"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
import pytest
from temporalio.testing import ActivityEnvironment

from agentic_qa.application.ports.idempotency import EXPERIENCE_CONSOLIDATION_SCOPE
from agentic_qa.domain.knowledge.experience import CandidateKind, CandidateStatus
from agentic_qa.infrastructure.workflows.temporal.activities import RunActivities
from agentic_qa.infrastructure.workflows.temporal.contracts import (
    ConsolidateParams,
    EpisodeParams,
    TransitionParams,
)
from tests.qa.test_evidence_chain import prepared
from tests.target_app.server import running_target_app


async def run_and_learn(artifact_root: Path) -> Any:
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

        learned = await ActivityEnvironment().run(
            activities.consolidate_experience, ConsolidateParams(run_id=run_id)
        )
        # A retry of the same activity, which is what Temporal does after a lost
        # acknowledgement. It must not teach the same run's lesson twice.
        replayed = await ActivityEnvironment().run(
            activities.consolidate_experience, ConsolidateParams(run_id=run_id)
        )

        async with container.unit_of_work() as uow:
            run = await uow.runs.get(run_id)
            assert run is not None
            candidates = await uow.knowledge.list_for_scope(
                project_id=run.project_id,
                environment_id=run.environment_id or "default",
            )
            record = await uow.idempotency.get(EXPERIENCE_CONSOLIDATION_SCOPE, run_id)
        return learned, replayed, candidates, record, run_id


def execute(artifact_root: Path) -> Any:
    try:
        return asyncio.run(run_and_learn(artifact_root))
    except (OSError, psycopg.OperationalError) as error:
        pytest.skip(f"PostgreSQL not reachable: {error}")


def test_a_finished_run_leaves_durable_knowledge(tmp_path: Path) -> None:
    learned, _replayed, candidates, record, run_id = execute(tmp_path)

    assert learned > 0
    kinds = {candidate.kind for candidate in candidates}
    # Where it got to, and what it verified there.
    assert CandidateKind.ROUTE in kinds
    assert CandidateKind.FAILURE_SIGNATURE in kinds

    # The record that makes consolidation once-per-run is durable, not in memory.
    assert record is not None
    assert record.resource_id == run_id


def test_everything_learned_names_the_run_it_came_from(tmp_path: Path) -> None:
    # Memory that cannot be traced back cannot be invalidated when the app changes.
    _learned, _replayed, candidates, _record, run_id = execute(tmp_path)

    for candidate in candidates:
        assert candidate.provenance.source_run_id == run_id
        assert candidate.validity.valid_from <= datetime.now(UTC)
        assert candidate.validity.origin is not None


def test_a_first_run_teaches_nothing_the_agent_may_act_on(tmp_path: Path) -> None:
    # One run is a coincidence. Nothing reaches an actionable status until a second
    # independent run agrees.
    _learned, _replayed, candidates, _record, _run_id = execute(tmp_path)

    assert candidates
    assert all(candidate.status is CandidateStatus.CANDIDATE for candidate in candidates)
    assert not any(candidate.is_actionable for candidate in candidates)


def test_a_retried_activity_learns_nothing_new(tmp_path: Path) -> None:
    learned, replayed, candidates, _record, _run_id = execute(tmp_path)

    assert learned > 0
    assert replayed == 0
    # Support still counts one run, because there was only one run.
    assert all(candidate.quality.support_count == 1 for candidate in candidates)


def test_the_page_cannot_write_into_what_the_agent_remembers(tmp_path: Path) -> None:
    """Page text is untrusted data. Whatever is stored must be safe to replay."""
    _learned, _replayed, candidates, _record, _run_id = execute(tmp_path)

    for candidate in candidates:
        payload = str(candidate.payload).lower()
        assert "ignore previous instructions" not in payload
        assert "bearer " not in payload
        # Bounded at capture, so a large page cannot become a large prompt later.
        assert len(payload) < 8000
