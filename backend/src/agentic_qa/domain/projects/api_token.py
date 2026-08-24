"""An API token: what a CI job presents, and what the database is allowed to keep.

Two objects and a rule. `ApiToken` is the *record* — which project, what it is called,
when and by whom it was issued — and it has nowhere to put the token's value, the same
way `EnvironmentSession` has nowhere to put a cookie. `IssuedToken` exists for the single
moment the value is real, on its way to being printed once and forgotten (ADR 0020).

The hashing choice is the part worth reading, because the conventional answer is wrong
here. Password KDFs — bcrypt, argon2, scrypt — are slow on purpose: a human-chosen
password has perhaps thirty bits of entropy and an attacker holding the hash can walk the
whole space, so the defence is to make each guess expensive. A token minted here is 256
bits from the operating system's CSPRNG. There is no space to walk. Making verification
slow would cost latency on every request in exchange for defeating an attack that
arithmetic already defeats.

What is easy to get wrong, and is not skipped, is the comparison: `==` on a digest returns
early at the first differing byte, which leaks the prefix to anyone who can time it.
"""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.validation import MAX_NAME_LENGTH, require_identifier, require_text

TOKEN_PREFIX = "roveqa_"
"""Greppable, and matchable by the secret scanning most forges run.

Not used for parsing — the server hashes the whole string and looks that up — so it costs
nothing to carry and buys a token that can be *found* in a log that should not have had
it.
"""

TOKEN_ENTROPY_BYTES = 32
"""256 bits, which is what makes a fast hash the right one rather than a shortcut."""


def mint_secret() -> str:
    """A new token value. The only place one is created."""
    return f"{TOKEN_PREFIX}{secrets.token_urlsafe(TOKEN_ENTROPY_BYTES)}"


def fingerprint(secret: str) -> str:
    """What the database stores instead of the token.

    SHA-256, for the reason in the module docstring. Hex rather than bytes so it can be a
    unique index on a plain text column and be read by a human comparing two rows.
    """
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def matches(secret: str, stored_fingerprint: str) -> bool:
    """Constant-time comparison. Never `==`, which returns at the first differing byte."""
    return hmac.compare_digest(fingerprint(secret), stored_fingerprint)


@dataclass(frozen=True)
class ApiToken:
    """The record of a token. Deliberately without the token.

    Everything here is safe to list, log and render, which is the property that makes the
    admin command's `list` and any future console screen possible without a second thought.
    """

    token_id: str
    project_id: str
    label: str
    """What a person calls it — "github actions", "nightly". Shown when listing, so
    revoking the right one does not depend on recognising a uuid."""

    fingerprint: str
    """SHA-256 of the value, hex. Unique: two tokens hashing the same would mean the
    CSPRNG repeated itself, and the database says so rather than silently accepting it."""

    issued_at: datetime
    issued_by: str = ""
    """Free text, for provenance. The first question after finding a token is where it
    came from, and a blank answer is still better than a guessed one."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "token_id", require_identifier(self.token_id, field="token_id"))
        object.__setattr__(
            self, "project_id", require_identifier(self.project_id, field="project_id")
        )
        object.__setattr__(
            self, "label", require_text(self.label, field="label", max_length=MAX_NAME_LENGTH)
        )
        object.__setattr__(self, "fingerprint", require_text(self.fingerprint, field="fingerprint"))
        if self.issued_at.tzinfo is None:
            raise InvalidEntityError("issued_at must be timezone-aware")

    def covers(self, project_id: str) -> bool:
        """Whether this token may act on that project.

        A method rather than an equality check at the call site, because "what a token
        reaches" is a rule and a rule spread across handlers is one that grows an
        exception. Today it is one project; if that ever changes, it changes here.
        """
        return self.project_id == project_id


@dataclass(frozen=True)
class IssuedToken:
    """A token at the one moment its value exists.

    Returned by issuing and by nothing else. Separate from `ApiToken` so that the type a
    repository stores and a listing returns simply cannot carry a secret — the value is
    unreachable from anywhere that did not just mint it.
    """

    record: ApiToken
    secret: str

    def __repr__(self) -> str:
        # Hand-written, because a dataclass prints its fields and one stray log line
        # would put the token somewhere nothing redacts.
        return f"IssuedToken(record={self.record.token_id!r}, secret=<not shown>)"


def issue(
    *,
    token_id: str,
    project_id: str,
    label: str,
    issued_by: str = "",
    now: datetime | None = None,
) -> IssuedToken:
    """Mint a token and its record together.

    One function, so a record cannot be created with a fingerprint of something nobody
    holds and a value cannot be minted without a record to find it by.
    """
    secret = mint_secret()
    record = ApiToken(
        token_id=token_id,
        project_id=project_id,
        label=label,
        fingerprint=fingerprint(secret),
        issued_at=now or datetime.now(UTC),
        issued_by=issued_by,
    )
    return IssuedToken(record=record, secret=secret)
