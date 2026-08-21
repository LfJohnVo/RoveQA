"""Redaction before anything is learned.

Memory outlives the run that produced it, gets retrieved into prompts, and ends up in
a graph a human browses. So the moment to refuse unsafe content is capture — not
retrieval, where a single missed filter leaks everything captured so far.

Two different dangers, handled differently:

**Secrets** are redacted. A token in a captured URL is not knowledge; blanking it keeps
whatever *was* knowledge around it (docs/13).

**Instruction-shaped page text is rejected outright.** A page saying "ignore previous
instructions" is untrusted data that would be replayed into a future planner's context
as if the system had learned it. There is no safe redaction of that — the whole item
goes (`.claude/rules/knowledge.md`).
"""

import re
from dataclasses import dataclass
from typing import Any

REDACTED = "[redacted]"
MAX_PAYLOAD_CHARS = 4000

_SECRET_KEYS = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|authorization|cookie|session|credential|bearer)",
    re.IGNORECASE,
)

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Query-string credentials: keep the route, lose the value.
    re.compile(r"([?&](?:token|key|api_key|access_token|password|sig)=)[^&\s]+", re.IGNORECASE),
    # userinfo in a URL. The @ is left in place so the host stays readable — the
    # origin is part of the observation; the credentials are not.
    re.compile(r"(https?://)[^/\s:@]+:[^/\s@]+(?=@)"),
    re.compile(r"\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE),
    # JWT-shaped things
    re.compile(r"\beyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\b"),
)

_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(?:the\s+)?(?:above|prior|previous)", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+now\b.{0,40}\b(assistant|agent|system)\b", re.IGNORECASE),
    re.compile(r"^\s*(system|assistant)\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"<\s*/?\s*(page_observation|system|instructions)\s*>", re.IGNORECASE),
)


class UnsafeKnowledgeError(Exception):
    """Content that must not be learned at all, rather than learned redacted."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class RedactionResult:
    payload: dict[str, Any]
    redacted_fields: tuple[str, ...]

    @property
    def changed(self) -> bool:
        return bool(self.redacted_fields)


def redact_payload(payload: dict[str, Any]) -> RedactionResult:
    """Clean a payload, or refuse it.

    Raises `UnsafeKnowledgeError` when the content is instruction-shaped: that is a
    refusal, not a redaction, because the danger is the text existing in a future
    prompt at all.
    """
    redacted: list[str] = []
    cleaned = _walk(payload, path="", redacted=redacted)
    if not isinstance(cleaned, dict):  # pragma: no cover - payload is always a mapping
        raise UnsafeKnowledgeError("payload must be an object")
    return RedactionResult(payload=cleaned, redacted_fields=tuple(redacted))


def _walk(value: Any, *, path: str, redacted: list[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: _redact_entry(key, item, path=f"{path}.{key}" if path else key, redacted=redacted)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _walk(item, path=f"{path}[{index}]", redacted=redacted)
            for index, item in enumerate(value)
        ]
    if isinstance(value, str):
        return _clean_text(value, path=path, redacted=redacted)
    return value


def _redact_entry(key: str, value: Any, *, path: str, redacted: list[str]) -> Any:
    if _SECRET_KEYS.search(key) and isinstance(value, str | int | float):
        # The key names a secret, so the value is one regardless of how it looks.
        redacted.append(path)
        return REDACTED
    return _walk(value, path=path, redacted=redacted)


def _replacement(match: re.Match[str]) -> str:
    prefix = match.group(1) if match.re.groups else ""
    return f"{prefix}{REDACTED}"


def _clean_text(value: str, *, path: str, redacted: list[str]) -> str:
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(value):
            raise UnsafeKnowledgeError(
                f"{path or 'payload'} contains instruction-shaped text and is not learnable"
            )

    cleaned = value
    for pattern in _SECRET_PATTERNS:
        # Some patterns keep a readable prefix (the scheme, the query parameter name);
        # others, like a bare JWT, have nothing worth keeping and no group at all.
        cleaned = pattern.sub(_replacement, cleaned)
    if cleaned != value:
        redacted.append(path)

    if len(cleaned) > MAX_PAYLOAD_CHARS:
        # Bounded at capture: unbounded page content in a payload becomes unbounded
        # page content in a prompt later.
        cleaned = f"{cleaned[:MAX_PAYLOAD_CHARS]}… [truncated]"
        redacted.append(f"{path}:truncated")
    return cleaned


def redact_secrets(value: str) -> str:
    """Clean a string that is *evidence*, keeping it rather than refusing it.

    `redact_payload` refuses instruction-shaped text, because knowledge that will be
    replayed into a future prompt must not carry an instruction. Evidence is the opposite
    case: a console error is worth reporting precisely when it is strange, and refusing to
    report it would hide the finding. So the secret patterns apply and the injection
    refusal does not -- evidence is read by a person, in a report, not fed back to a model.
    """
    cleaned = value
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub(_replacement, cleaned)
    if len(cleaned) > MAX_PAYLOAD_CHARS:
        return f"{cleaned[:MAX_PAYLOAD_CHARS]}… [truncated]"
    return cleaned
