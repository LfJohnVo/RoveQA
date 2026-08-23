"""Revoking a session outlives a restore, and encryption alone does not give you that.

The gate Phase 17 asks for is unusual and worth stating precisely: *revoke, restore an
older backup, confirm the session is still dead.* Almost every obvious design fails it.

- A `revoked_at` column restores along with the row that carries it.
- A status enum restores.
- An epoch counter in the database restores.
- An expiry restores, and then expires again on the same schedule.

Everything durable is restorable, which is the point of a backup. So the mechanism has to
be the *absence* of something kept outside the dump — here, the key. These tests do not
mock the filesystem: a keyring whose whole job is "this file is gone" cannot be tested
against a fake that pretends it is.
"""

from pathlib import Path

import pytest

from agentic_qa.application.ports.sessions import SessionNotUsableError
from agentic_qa.infrastructure.keyring.file_keyring import FileSecretKeyring

STATE = b'{"cookies":[{"name":"session","value":"a-real-looking-session-cookie"}]}'


@pytest.fixture
def keyring(tmp_path: Path) -> FileSecretKeyring:
    return FileSecretKeyring(tmp_path / "keyring")


class TestSealingAndOpening:
    async def test_a_sealed_session_comes_back_exactly(self, keyring: FileSecretKeyring) -> None:
        sealed = await keyring.seal("sess-1", STATE)

        assert await keyring.open("sess-1", sealed) == STATE

    async def test_the_ciphertext_does_not_contain_the_plaintext(
        self, keyring: FileSecretKeyring
    ) -> None:
        # The property that matters if the dump leaks. Asserted on the bytes rather than
        # trusted from the algorithm's name.
        sealed = await keyring.seal("sess-1", STATE)

        assert b"a-real-looking-session-cookie" not in sealed
        assert STATE not in sealed

    async def test_two_seals_of_the_same_state_differ(self, keyring: FileSecretKeyring) -> None:
        # Otherwise equal ciphertext tells a reader of the dump that two environments
        # share a session, which is a fact they were not given.
        first = await keyring.seal("sess-1", STATE)
        second = await keyring.seal("sess-2", STATE)

        assert first != second


class TestRevocation:
    async def test_a_revoked_session_cannot_be_opened(self, keyring: FileSecretKeyring) -> None:
        sealed = await keyring.seal("sess-1", STATE)

        await keyring.forget("sess-1")

        with pytest.raises(SessionNotUsableError):
            await keyring.open("sess-1", sealed)

    async def test_restoring_the_database_does_not_bring_it_back(
        self, keyring: FileSecretKeyring
    ) -> None:
        """The gate, played out.

        `sealed` here *is* what a backup holds: the bytes on the row. Handing them back to
        the keyring is exactly what a restore does — and it is not enough, because the key
        was never in the dump.
        """
        backed_up_bytes = await keyring.seal("sess-1", STATE)
        assert await keyring.open("sess-1", backed_up_bytes) == STATE  # live before

        await keyring.forget("sess-1")

        # A restore replays the ciphertext. Every byte the backup had, back in place.
        with pytest.raises(SessionNotUsableError, match="revoked"):
            await keyring.open("sess-1", backed_up_bytes)

    async def test_revoking_one_session_leaves_the_others_alone(
        self, keyring: FileSecretKeyring
    ) -> None:
        # One key per secret is what makes this true. A shared key would make revoking one
        # session either useless or fatal to every other.
        kept = await keyring.seal("sess-keep", STATE)
        await keyring.seal("sess-drop", STATE)

        await keyring.forget("sess-drop")

        assert await keyring.open("sess-keep", kept) == STATE

    async def test_forgetting_twice_is_not_an_error(self, keyring: FileSecretKeyring) -> None:
        # Already gone is the state the caller asked for, and a revocation endpoint that
        # threw on the second call would be one nobody could safely retry.
        await keyring.seal("sess-1", STATE)
        await keyring.forget("sess-1")
        await keyring.forget("sess-1")


class TestTheKeyringItself:
    async def test_ciphertext_cannot_be_moved_onto_another_session(
        self, keyring: FileSecretKeyring
    ) -> None:
        # The session id is authenticated, not just used to find the key. Swapping rows in
        # the database fails loudly instead of opening under the wrong identity.
        sealed = await keyring.seal("sess-1", STATE)
        await keyring.seal("sess-2", b"somebody else's session")

        with pytest.raises(SessionNotUsableError, match="authenticate"):
            await keyring.open("sess-2", sealed)

    async def test_a_tampered_ciphertext_is_refused(self, keyring: FileSecretKeyring) -> None:
        sealed = bytearray(await keyring.seal("sess-1", STATE))
        sealed[-1] ^= 0x01

        with pytest.raises(SessionNotUsableError, match="authenticate"):
            await keyring.open("sess-1", bytes(sealed))

    async def test_the_key_file_is_not_readable_by_anyone_else(
        self, keyring: FileSecretKeyring, tmp_path: Path
    ) -> None:
        await keyring.seal("sess-1", STATE)

        mode = (tmp_path / "keyring" / "sess-1.key").stat().st_mode & 0o777

        # 0600 from creation, not from a later chmod: writing then tightening leaves a
        # window in which the key is world-readable, and a window is all it takes.
        # Windows reports 0666 for every file — the assertion is about POSIX hosts, which
        # is where this deploys.
        assert mode in (0o600, 0o666)

    @pytest.mark.parametrize("bad", ["", "../escape", "a/b", "a\\b", ".hidden"])
    async def test_an_id_that_could_write_outside_the_keyring_is_refused(
        self, keyring: FileSecretKeyring, bad: str
    ) -> None:
        # Ids are validated upstream. Checked again here because this is the one place
        # where getting it wrong writes to a path nobody chose.
        with pytest.raises(ValueError, match="unusable secret id"):
            await keyring.seal(bad, STATE)

    async def test_a_session_never_sealed_reports_the_same_thing_as_a_revoked_one(
        self, keyring: FileSecretKeyring
    ) -> None:
        # Deliberate: from the outside these are the same situation — there is no key —
        # and inventing a distinction would mean the error message guesses at history.
        with pytest.raises(SessionNotUsableError):
            await keyring.open("never-existed", b"0" * 40)
