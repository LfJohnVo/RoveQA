"""A keyring on disk, outside the database and outside the backup (ADR 0019).

The design in one sentence: **PostgreSQL holds ciphertext, this holds the keys, and
revoking means destroying a key.** A dump restored from any backup ever taken brings the
ciphertext back and it decrypts to nothing, because what was destroyed was never in the
dump.

That is the property a tombstone row cannot give you. A `revoked_at` column restores along
with everything else; so does an epoch counter, and so does an expiry. The mechanism has to
be the *absence* of something, kept somewhere `pg_restore` cannot reach.

What this does not defend against is worth stating where somebody will read it: an attacker
with the host has this directory. It protects a leaked database dump, and it protects
against restore-resurrection. It does not protect a compromised machine, and a single-node
self-hosted deployment cannot honestly claim that it does.
"""

import asyncio
import logging
import os
import secrets
import stat
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from agentic_qa.application.ports.sessions import SessionNotUsableError

logger = logging.getLogger(__name__)

KEY_BYTES = 32
NONCE_BYTES = 12
"""AES-GCM's standard nonce size. A fresh one per seal, never reused with a key — which
here is free, because a key seals exactly one secret exactly once."""

DEFAULT_KEYRING_PATH = "/data/keyring"


class FileSecretKeyring:
    """One file per secret, `0600`, in a directory the backup script does not touch."""

    def __init__(self, directory: Path | str = DEFAULT_KEYRING_PATH) -> None:
        self._directory = Path(directory)

    async def seal(self, secret_id: str, plaintext: bytes) -> bytes:
        key = secrets.token_bytes(KEY_BYTES)
        nonce = secrets.token_bytes(NONCE_BYTES)
        # `secret_id` as associated data: ciphertext moved onto another session's row
        # fails to authenticate rather than quietly decrypting under the wrong identity.
        sealed = AESGCM(key).encrypt(nonce, plaintext, secret_id.encode())
        await asyncio.to_thread(self._write_key, secret_id, key)
        return nonce + sealed

    async def open(self, secret_id: str, ciphertext: bytes) -> bytes:
        key = await asyncio.to_thread(self._read_key, secret_id)
        if key is None:
            # The normal path after a revocation, and after restoring a dump older than
            # one. Named as what it is so nobody reports it as corruption.
            raise SessionNotUsableError(
                f"no key for {secret_id}: it was revoked, or this database was restored "
                "from a backup taken before the key existed"
            )
        try:
            return AESGCM(key).decrypt(
                ciphertext[:NONCE_BYTES], ciphertext[NONCE_BYTES:], secret_id.encode()
            )
        except InvalidTag as tampered:
            raise SessionNotUsableError(
                f"the stored state for {secret_id} does not authenticate under its key"
            ) from tampered

    async def forget(self, secret_id: str) -> None:
        await asyncio.to_thread(self._delete_key, secret_id)

    # -- disk, off the event loop -------------------------------------------------

    def _path_for(self, secret_id: str) -> Path:
        # Identifiers are validated upstream, but this is the one place where getting it
        # wrong writes outside the keyring, so it is checked here too rather than trusted.
        if not secret_id or "/" in secret_id or "\\" in secret_id or secret_id.startswith("."):
            raise ValueError(f"unusable secret id: {secret_id!r}")
        return self._directory / f"{secret_id}.key"

    def _write_key(self, secret_id: str, key: bytes) -> None:
        path = self._path_for(secret_id)
        self._directory.mkdir(parents=True, exist_ok=True)
        os.chmod(self._directory, stat.S_IRWXU)  # noqa: PTH101 - the mode is the point
        # Opened with O_EXCL and the mode set at creation: writing and then chmod-ing
        # leaves a window in which the key is world-readable, and a window is all it takes.
        descriptor = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR
        )
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(key)

    def _read_key(self, secret_id: str) -> bytes | None:
        try:
            return self._path_for(secret_id).read_bytes()
        except FileNotFoundError:
            return None

    def _delete_key(self, secret_id: str) -> None:
        try:
            self._path_for(secret_id).unlink()
        except FileNotFoundError:
            # Already gone is the state the caller asked for.
            return
        logger.info("destroyed the key for %s; its stored state is now unreadable", secret_id)
