"""A borrowed browser session, and the secrets an environment declares (ADR 0019).

The domain holds *identity and validity*, never bytes. `EnvironmentSession` says which
environment a session belongs to, where it came from and until when it is worth trusting;
the sealed `storage_state` behind it is infrastructure's problem and never passes through
here. A dataclass that carried the cookies would be a dataclass that could be logged.

The same rule shapes `SecretName`: an action names a secret, the Playwright adapter
resolves it, and nothing in between is able to print what it resolved.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.validation import MAX_NAME_LENGTH, require_identifier, require_text

MAX_SECRET_NAME_LENGTH = 100

SECRET_NAME_ALPHABET = frozenset("abcdefghijklmnopqrstuvwxyz0123456789._-")
"""Deliberately narrow. A secret name travels into a prompt, so it must not be able to
carry a delimiter, a newline or anything else that reads as structure once it is there."""


@dataclass(frozen=True)
class SecretName:
    """What an action is allowed to say instead of a password.

    A value object rather than a bare string so that the one place which validates the
    alphabet is the one place the type can be created. A `str` would be validated at
    whichever call sites remembered.
    """

    value: str

    def __post_init__(self) -> None:
        name = require_text(self.value, field="secret name", max_length=MAX_SECRET_NAME_LENGTH)
        if not set(name) <= SECRET_NAME_ALPHABET:
            raise InvalidEntityError(
                "a secret name may use lowercase letters, digits, dot, underscore and hyphen"
            )
        object.__setattr__(self, "value", name)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class EnvironmentSession:
    """A session somebody established by logging in, lent to a run.

    `valid_until` is a claim, not a guarantee — a site can end a session early and this
    object has no way to know. It exists so the *common* case, an expiry nobody noticed,
    is caught before a run spends its budget discovering it. The uncommon case is caught
    by looking at the page.
    """

    session_id: str
    environment_id: str
    label: str
    """What a person calls it — "admin", "read-only reviewer". Shown in the console and
    the CLI so rotating the right one does not depend on recognising a uuid."""

    established_at: datetime
    valid_until: datetime | None = None
    """None means nobody stated an expiry. Distinguished from an expiry in the past: one
    is unknown, the other is known to be over."""

    established_by: str = ""
    """Free text, for provenance. Whoever captured the storage state and how — the
    question a reader asks first is "where did this come from"."""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "session_id", require_identifier(self.session_id, field="session_id")
        )
        object.__setattr__(
            self, "environment_id", require_identifier(self.environment_id, field="environment_id")
        )
        object.__setattr__(
            self, "label", require_text(self.label, field="label", max_length=MAX_NAME_LENGTH)
        )
        for field_name in ("established_at", "valid_until"):
            moment = getattr(self, field_name)
            if moment is not None and moment.tzinfo is None:
                # A naive timestamp compared against an aware one raises at the worst
                # possible moment, which here is halfway through provisioning a browser.
                raise InvalidEntityError(f"{field_name} must be timezone-aware")
        if self.valid_until is not None and self.valid_until <= self.established_at:
            raise InvalidEntityError("a session cannot expire before it was established")

    def has_expired(self, *, now: datetime | None = None) -> bool:
        """Whether the stated validity is over. Unknown validity is not expiry."""
        if self.valid_until is None:
            return False
        return (now or datetime.now(UTC)) >= self.valid_until
