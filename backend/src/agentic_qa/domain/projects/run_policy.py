"""RunPolicy: the rules a run may not exceed (Projects bounded context).

Mirrors `contracts/run-policy.schema.json`. Origins follow RFC 6454 and match exactly
— no implicit subdomains, no path prefixes, scheme-sensitive (docs/13). Ambiguous
allowlist matching is a classic bypass, so the parsing is strict and the comparison
is boring on purpose.

Policies are immutable once created: a run records which policy governed it, and
editing one in place would rewrite the rules of runs already finished.
"""

from dataclasses import dataclass, field
from urllib.parse import urlsplit

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.validation import require_identifier, require_text

ALLOWED_SCHEMES = frozenset({"http", "https"})


def normalize_origin(value: str) -> str:
    """Return `scheme://host[:port]`, rejecting anything carrying more than that."""
    candidate = require_text(value, field="allowed_origin", max_length=500).lower()
    parts = urlsplit(candidate)
    if parts.scheme not in ALLOWED_SCHEMES:
        raise InvalidEntityError(f"origin scheme must be http or https: {value}")
    if not parts.hostname:
        raise InvalidEntityError(f"origin must include a host: {value}")
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        raise InvalidEntityError(f"origin must not include a path or query: {value}")
    if parts.username or parts.password:
        raise InvalidEntityError(f"origin must not include credentials: {value}")
    port = f":{parts.port}" if parts.port is not None else ""
    return f"{parts.scheme}://{parts.hostname}{port}"


@dataclass
class RunPolicy:
    policy_id: str
    project_id: str
    allowed_origins: tuple[str, ...]
    max_duration_seconds: int
    max_actions: int
    max_model_calls: int
    destructive_actions: bool = False
    allow_file_uploads: bool = False
    upload_path_allowlist: tuple[str, ...] = field(default=())
    allow_downloads: bool = False
    max_depth: int | None = None
    synthetic_data_allowed: bool = True

    def __post_init__(self) -> None:
        self.policy_id = require_identifier(self.policy_id, field="policy_id")
        self.project_id = require_identifier(self.project_id, field="project_id")
        self.allowed_origins = tuple(normalize_origin(origin) for origin in self.allowed_origins)
        if not self.allowed_origins:
            # A run with no allowlist could reach anything, including internal
            # services. There is no safe default, so there is no default.
            raise InvalidEntityError("a run policy must allow at least one origin")
        for name, value in (
            ("max_duration_seconds", self.max_duration_seconds),
            ("max_actions", self.max_actions),
        ):
            if value < 1:
                raise InvalidEntityError(f"{name} must be at least 1")
        if self.max_model_calls < 0:
            raise InvalidEntityError("max_model_calls must not be negative")
        if self.max_depth is not None and self.max_depth < 0:
            raise InvalidEntityError("max_depth must not be negative")
        self.upload_path_allowlist = tuple(
            require_text(path, field="upload_path") for path in self.upload_path_allowlist
        )

    def allows_origin(self, url: str) -> bool:
        """Exact origin match against the allowlist."""
        try:
            origin = normalize_origin(_origin_of(url))
        except InvalidEntityError:
            return False
        return origin in self.allowed_origins


def _origin_of(url: str) -> str:
    parts = urlsplit(url.strip())
    port = f":{parts.port}" if parts.port is not None else ""
    return f"{parts.scheme}://{parts.hostname or ''}{port}"
