"""Durable idempotency records.

A lost response must never cost a second run or a second side effect (docs/12). The
record lives in PostgreSQL, never only in Redis, and is committed in the same
transaction as the resource it identifies — a record pointing at a resource that was
never created would be worse than no record at all.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

RUN_CREATION_SCOPE = "runs.create"


def request_fingerprint(scope: str, payload: dict[str, str]) -> str:
    """Stable hash of the logical request.

    Two requests with the same key are "the same request" only if this matches;
    otherwise the key is being reused for different work and must fail typed.
    """
    canonical = json.dumps({"scope": scope, **payload}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class IdempotencyRecord:
    scope: str
    key: str
    request_fingerprint: str
    resource_id: str
    created_at: datetime | None = None


class IdempotencyRepository(Protocol):
    async def get(self, scope: str, key: str) -> IdempotencyRecord | None: ...

    async def add(self, record: IdempotencyRecord) -> None:
        """Persist a record. Raises AlreadyExistsError when (scope, key) is taken.

        A concurrent duplicate loses this race and surfaces as a typed conflict; the
        client retries and gets the replay. Retention: records are kept indefinitely
        in v1, purging is a maintenance concern (Phase 13).
        """
        ...
