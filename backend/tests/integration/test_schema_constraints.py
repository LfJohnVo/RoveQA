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
