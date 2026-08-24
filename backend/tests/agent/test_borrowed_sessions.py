"""Provisioning a session, and what happens when there is not a usable one (ADR 0019).

The activity is the layer that decides this, and it is the layer that must not raise.
Every failure here — an expired session, a revoked one, a dump restored from before the
revocation — is a *fact about the run*, not a malfunction: letting it escape would reach
Temporal as an infrastructure failure and be retried until the timeout, re-opening a
session that will be just as expired next time (ADR 0009).

None of these need a browser. What is under test is what the activity resolves and what
it does when it cannot.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from agentic_qa.application.ports.browser import BrowserSetup
from agentic_qa.application.ports.sessions import SessionNotUsableError
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.bootstrap.container import Container
from agentic_qa.domain.projects.environment import Environment
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.projects.session import EnvironmentSession
from agentic_qa.infrastructure.keyring.file_keyring import FileSecretKeyring
from agentic_qa.infrastructure.workflows.temporal.activities import RunActivities
from tests.fakes.repositories import InMemoryStore
from tests.fakes.unit_of_work import InMemoryUnitOfWork

STATE = b'{"cookies":[{"name":"session","value":"a-real-looking-session-cookie"}]}'
NOW = datetime.now(UTC)


@pytest.fixture
def unit_of_work() -> Callable[[], UnitOfWork]:
    store = InMemoryStore()

    def factory() -> UnitOfWork:
        return InMemoryUnitOfWork(store)

    return factory


@asynccontextmanager
async def seeded(
    unit_of_work: Callable[[], UnitOfWork], environment_id: str = "env-1"
) -> AsyncIterator[str]:
    project_id = f"p-{uuid4()}"
    async with unit_of_work() as uow:
        await uow.projects.add(Project(project_id=project_id, name="Sessions"))
        await uow.environments.add(
            Environment(environment_id=environment_id, project_id=project_id, name="staging")
        )
        await uow.commit()
    yield project_id


def activities(unit_of_work: Callable[[], UnitOfWork], keyring: Any = None) -> RunActivities:
    return RunActivities(Container(unit_of_work=unit_of_work, keyring=keyring))


class TestAnAnonymousContextStaysFirstClass:
    async def test_a_run_with_no_environment_provisions_nothing(
        self, unit_of_work: Callable[[], UnitOfWork], tmp_path: Path
    ) -> None:
        # Most of what this product tests needs no session at all — a landing page, a
        # documentation site, a shop with guest checkout. That is the ordinary path.
        setup = await activities(unit_of_work, FileSecretKeyring(tmp_path))._provision(None)

        assert setup == BrowserSetup()

    async def test_an_environment_with_no_session_provisions_nothing(
        self, unit_of_work: Callable[[], UnitOfWork], tmp_path: Path
    ) -> None:
        async with seeded(unit_of_work):
            setup = await activities(unit_of_work, FileSecretKeyring(tmp_path))._provision("env-1")

        assert setup.storage_state_json is None

    async def test_no_keyring_at_all_is_a_working_configuration(
        self, unit_of_work: Callable[[], UnitOfWork]
    ) -> None:
        # A deployment that never registered a session has no keyring, and everything an
        # anonymous browser can reach still works.
        async with seeded(unit_of_work):
            setup = await activities(unit_of_work, None)._provision("env-1")

        assert setup.storage_state_json is None


class TestAUsableSessionIsProvisioned:
    async def test_the_stored_state_is_opened_and_handed_over(
        self, unit_of_work: Callable[[], UnitOfWork], tmp_path: Path
    ) -> None:
        keyring = FileSecretKeyring(tmp_path)
        async with seeded(unit_of_work):
            sealed = await keyring.seal("sess-1", STATE)
            async with unit_of_work() as uow:
                await uow.sessions.add(_session("sess-1"), sealed)
                await uow.commit()

            setup = await activities(unit_of_work, keyring)._provision("env-1")

        assert setup.storage_state_json == STATE

    async def test_the_newest_session_wins_after_a_rotation(
        self, unit_of_work: Callable[[], UnitOfWork], tmp_path: Path
    ) -> None:
        # Rotating adds a session rather than editing one, so "current" is decided by
        # time. A rotation that kept serving the old one would be a rotation in name only.
        keyring = FileSecretKeyring(tmp_path)
        async with seeded(unit_of_work):
            async with unit_of_work() as uow:
                await uow.sessions.add(
                    _session("sess-old", at=NOW - timedelta(days=1)),
                    await keyring.seal("sess-old", b"stale"),
                )
                await uow.sessions.add(_session("sess-new"), await keyring.seal("sess-new", STATE))
                await uow.commit()

            setup = await activities(unit_of_work, keyring)._provision("env-1")

        assert setup.storage_state_json == STATE


class TestAnUnusableSessionStopsTheRunAndSaysWhy:
    async def test_an_expired_session_is_refused_before_the_browser_starts(
        self, unit_of_work: Callable[[], UnitOfWork], tmp_path: Path
    ) -> None:
        # Refused here rather than discovered twenty actions later on a login page, where
        # the run has already spent its budget and every criterion looks unmet.
        keyring = FileSecretKeyring(tmp_path)
        async with seeded(unit_of_work):
            async with unit_of_work() as uow:
                await uow.sessions.add(
                    _session("sess-1", at=NOW - timedelta(days=2), until=NOW - timedelta(days=1)),
                    await keyring.seal("sess-1", STATE),
                )
                await uow.commit()

            with pytest.raises(SessionNotUsableError, match="expired"):
                await activities(unit_of_work, keyring)._provision("env-1")

    async def test_a_revoked_session_is_refused_even_though_the_row_is_intact(
        self, unit_of_work: Callable[[], UnitOfWork], tmp_path: Path
    ) -> None:
        """The revocation gate, seen from the layer that provisions.

        Nothing about the database changed: the record is there, unexpired, with its
        ciphertext. What is gone is the key, and that is what a restore cannot bring back.
        """
        keyring = FileSecretKeyring(tmp_path)
        async with seeded(unit_of_work):
            async with unit_of_work() as uow:
                await uow.sessions.add(_session("sess-1"), await keyring.seal("sess-1", STATE))
                await uow.commit()

            await keyring.forget("sess-1")

            with pytest.raises(SessionNotUsableError, match="revoked"):
                await activities(unit_of_work, keyring)._provision("env-1")

            # And the record really is still there — this is not a missing row.
            async with unit_of_work() as uow:
                assert await uow.sessions.get("sess-1") is not None


def _session(
    session_id: str, *, at: datetime | None = None, until: datetime | None = None
) -> EnvironmentSession:
    return EnvironmentSession(
        session_id=session_id,
        environment_id="env-1",
        label="admin",
        established_at=at or NOW,
        valid_until=until,
        established_by="captured by hand",
    )
