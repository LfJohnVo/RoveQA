"""Ports for borrowed sessions and declared secrets (ADR 0019).

Two collaborators, deliberately separate, because they have different failure modes and
live in different places.

`SessionRepository` owns the *record* — which environment, whose, until when — and the
sealed bytes that go with it. It is PostgreSQL, and everything it holds is restorable.

`SecretKeyring` owns the keys, and it is not PostgreSQL and not in any backup. That
separation is the whole revocation design: destroying a key is an act a `pg_restore`
cannot undo, while any flag, status or epoch stored beside the ciphertext comes back with
it. Revoking is `forget`, and it means it.
"""

from typing import Protocol

from agentic_qa.domain.projects.session import EnvironmentSession


class SessionNotUsableError(Exception):
    """The session exists on paper and cannot be used.

    Raised rather than returned as None because the two are different situations and the
    caller must not conflate them: "this environment has no session" is a configuration
    the run may proceed under, while "the session it names cannot be opened" is a run
    that must stop and say why. The message reaches a `FailureKind.SESSION`, so it is
    written for whoever has to fix it.
    """


class SecretKeyring(Protocol):
    """Where the keys live, which is nowhere the database can reach.

    Deliberately narrow. There is no `list` and no `export`: a keyring that could enumerate
    itself is one an accidental log statement could print.
    """

    async def seal(self, secret_id: str, plaintext: bytes) -> bytes:
        """Mint a key for `secret_id` and return the ciphertext.

        One key per secret. Sharing a key across sessions would make revoking one of them
        either useless or fatal to the others.
        """
        ...

    async def open(self, secret_id: str, ciphertext: bytes) -> bytes:
        """Return the plaintext, or raise `SessionNotUsableError` if the key is gone.

        Key gone is the *normal* path after a revocation, so it is a stated outcome rather
        than an unexpected one.
        """
        ...

    async def forget(self, secret_id: str) -> None:
        """Destroy the key. This is what revocation is.

        Idempotent: forgetting something already forgotten is the state the caller wanted.
        """
        ...


class SessionRepository(Protocol):
    async def add(self, session: EnvironmentSession, sealed_state: bytes) -> None:
        """Persist the record and the sealed bytes together.

        One operation because half of it is unusable: a record with no state cannot open a
        browser, and state with no record belongs to nobody.
        """
        ...

    async def get(self, session_id: str) -> EnvironmentSession | None: ...

    async def current_for_environment(self, environment_id: str) -> EnvironmentSession | None:
        """The session a run of this environment should borrow, or None.

        The most recently established one. Rotating therefore means adding a new session,
        not editing an old one — an audit trail rather than an overwrite, and the reason
        `add` has no `update` sibling.
        """
        ...

    async def sealed_state(self, session_id: str) -> bytes | None:
        """The ciphertext. Opening it needs the keyring, which this does not have."""
        ...

    async def list_for_environment(self, environment_id: str) -> list[EnvironmentSession]:
        """Every session recorded for the environment, newest first.

        Records only — a listing that carried the bytes would be a listing nobody could
        safely render.
        """
        ...
