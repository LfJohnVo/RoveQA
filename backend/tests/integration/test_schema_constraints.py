"""The durable schema must defend the run invariants, not just the Python layer.

Autogenerate silently dropped these CHECK constraints once already, so they are
verified against the real database.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

INSERT_PROJECT = text("INSERT INTO projects (project_id, name) VALUES ('p-ck', 'Checks')")


async def seed(session: AsyncSession) -> None:
    await session.execute(INSERT_PROJECT)


async def test_status_must_be_a_known_value(postgres_session: AsyncSession) -> None:
    await seed(postgres_session)
    with pytest.raises(IntegrityError):
        await postgres_session.execute(
            text(
                "INSERT INTO runs (run_id, project_id, status) "
                "VALUES ('r-bad', 'p-ck', 'not-a-status')"
            )
        )


async def test_verdict_must_be_a_known_value(postgres_session: AsyncSession) -> None:
    await seed(postgres_session)
    with pytest.raises(IntegrityError):
        await postgres_session.execute(
            text(
                "INSERT INTO runs (run_id, project_id, status, verdict) "
                "VALUES ('r-bad', 'p-ck', 'completed', 'not-a-verdict')"
            )
        )


async def test_non_terminal_run_cannot_carry_a_verdict(postgres_session: AsyncSession) -> None:
    await seed(postgres_session)
    with pytest.raises(IntegrityError):
        await postgres_session.execute(
            text(
                "INSERT INTO runs (run_id, project_id, status, verdict) "
                "VALUES ('r-bad', 'p-ck', 'running', 'passed')"
            )
        )


async def test_run_requires_an_existing_project(postgres_session: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        await postgres_session.execute(
            text("INSERT INTO runs (run_id, project_id, status) VALUES ('r-x', 'ghost', 'created')")
        )


async def test_criterion_ids_are_unique_within_a_story(postgres_session: AsyncSession) -> None:
    await seed(postgres_session)
    await postgres_session.execute(
        text(
            "INSERT INTO user_stories "
            "(story_id, project_id, actor, goal, preconditions, forbidden_outcomes) "
            "VALUES ('s-ck', 'p-ck', 'user', 'goal', '[]'::jsonb, '[]'::jsonb)"
        )
    )
    await postgres_session.execute(
        text(
            "INSERT INTO acceptance_criteria (story_id, criterion_id, description, position) "
            "VALUES ('s-ck', 'ac-1', 'first', 0)"
        )
    )
    with pytest.raises(IntegrityError):
        await postgres_session.execute(
            text(
                "INSERT INTO acceptance_criteria "
                "(story_id, criterion_id, description, position) "
                "VALUES ('s-ck', 'ac-1', 'duplicate', 1)"
            )
        )


KNOWLEDGE_COLUMNS = (
    "candidate_id, project_id, environment_id, dedup_key, kind, status, observed, "
    "model_derived, source_run_id, valid_from, support_count, success_count, "
    "failure_count, contradiction_count, reliability, payload"
)


def knowledge_values(*, observed: str, model_derived: str, status: str) -> str:
    return (
        f"('k-1', 'p-ck', 'staging', 'acceptance_fact:abc', 'acceptance_fact', '{status}', "
        f"{observed}, {model_derived}, 'r-1', now(), 1, 1, 0, 0, 1.0, '{{}}'::jsonb)"
    )


async def test_a_model_derived_candidate_cannot_be_trusted_in_the_database(
    postgres_session: AsyncSession,
) -> None:
    """The rule the whole learning design rests on, defended below the Python layer.

    The domain refuses this too. Both matter: an adapter, a migration backfill or a
    hand-written UPDATE could all reach the table without passing through the entity,
    and a trusted hypothesis is what a later run would act on as established fact.
    """
    await seed(postgres_session)
    with pytest.raises(IntegrityError):
        await postgres_session.execute(
            text(
                f"INSERT INTO knowledge_candidates ({KNOWLEDGE_COLUMNS}) VALUES "
                + knowledge_values(observed="false", model_derived="true", status="trusted")
            )
        )


async def test_knowledge_must_come_from_somewhere(postgres_session: AsyncSession) -> None:
    await seed(postgres_session)
    with pytest.raises(IntegrityError):
        await postgres_session.execute(
            text(
                f"INSERT INTO knowledge_candidates ({KNOWLEDGE_COLUMNS}) VALUES "
                + knowledge_values(observed="false", model_derived="false", status="candidate")
            )
        )
