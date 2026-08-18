"""PageFingerprint v1 (docs/07).

A stable identity for "the same kind of page", built from structure rather than
content: route pattern, title, and the semantic controls present. Two visits to the
same screen with different data must agree; a redesign must not.

A known fingerprint may later unlock a deterministic playbook, and a changed one
forces revalidation — so it must never encode volatile detail like record ids.
"""

import hashlib
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

_NUMERIC_SEGMENT = re.compile(r"^\d+$")
_UUID_SEGMENT = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


def route_pattern(url: str) -> str:
    """Collapse identifier-looking path segments so /records/42 and /records/43 agree."""
    path = urlsplit(url).path or "/"
    segments = []
    for segment in path.split("/"):
        if not segment:
            continue
        if _NUMERIC_SEGMENT.match(segment) or _UUID_SEGMENT.match(segment):
            segments.append("{id}")
        else:
            segments.append(segment)
    return "/" + "/".join(segments)


@dataclass(frozen=True)
class PageFingerprint:
    route: str
    title: str
    control_signature: tuple[str, ...]
    digest: str = field(default="")

    @classmethod
    def build(cls, *, url: str, title: str, controls: tuple[str, ...]) -> "PageFingerprint":
        route = route_pattern(url)
        # Sorted so DOM ordering changes that do not alter the available controls
        # produce the same fingerprint.
        signature = tuple(sorted({control.strip().lower() for control in controls if control}))
        payload = "|".join((route, title.strip().lower(), *signature))
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return cls(route=route, title=title, control_signature=signature, digest=digest)

    def matches(self, other: "PageFingerprint") -> bool:
        return self.digest == other.digest
