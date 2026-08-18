"""Shared value checks for domain entities."""

from agentic_qa.domain.errors import InvalidEntityError

# Contracts bound identifiers at 200 chars (see contracts/test-plan.schema.json).
MAX_IDENTIFIER_LENGTH = 200
MAX_NAME_LENGTH = 240
MAX_TEXT_LENGTH = 4000


def require_text(value: str, *, field: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Return the trimmed value, or raise when it is blank or too long."""
    if not isinstance(value, str):  # defensive: entities cross process boundaries
        raise InvalidEntityError(f"{field} must be a string, got {type(value).__name__}")
    trimmed = value.strip()
    if not trimmed:
        raise InvalidEntityError(f"{field} must not be blank")
    if len(trimmed) > max_length:
        raise InvalidEntityError(f"{field} exceeds {max_length} characters")
    return trimmed


def require_identifier(value: str, *, field: str) -> str:
    return require_text(value, field=field, max_length=MAX_IDENTIFIER_LENGTH)
