"""Redis Streams fan-out for run events.

Streams are bounded (`MAXLEN ~`): they carry recent history for live clients, and
anything older is recovered from PostgreSQL. Trimming is what keeps Redis from
quietly becoming a second, unbounded copy of the journal (docs/09).

Driver replies are normalized and validated at runtime rather than trusted through a
cast: a shape we do not recognise is a bug to surface, not data to guess at.
"""

import json
import logging
from collections.abc import AsyncIterator, Sequence
from datetime import datetime

from redis.asyncio import Redis
from redis.typing import EncodableT, FieldT

from agentic_qa.application.ports.events import RunEvent

logger = logging.getLogger(__name__)

STREAM_MAX_LENGTH = 1000
"""Recent window only; the durable log is the one that must be complete."""

BLOCK_MILLISECONDS = 5_000
STREAM_START = "0-0"


def stream_key(run_id: str) -> str:
    return f"stream:run:{run_id}"


def _as_text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode()
    if isinstance(value, str):
        return value
    raise TypeError(f"expected text from Redis, got {type(value).__name__}")


def _encode(event: RunEvent) -> dict[FieldT, EncodableT]:
    return {
        "event_id": event.event_id,
        "run_id": event.run_id,
        "sequence": str(event.sequence),
        "type": event.type,
        "occurred_at": event.occurred_at.isoformat(),
        "payload": json.dumps(event.payload),
        "request_id": event.request_id or "",
    }


def _decode(fields: dict[str, str]) -> RunEvent:
    return RunEvent(
        event_id=fields["event_id"],
        run_id=fields["run_id"],
        sequence=int(fields["sequence"]),
        type=fields["type"],
        occurred_at=datetime.fromisoformat(fields["occurred_at"]),
        payload=json.loads(fields["payload"]),
        request_id=fields["request_id"] or None,
    )


def _parse_read_reply(raw: object) -> list[tuple[str, dict[str, str]]]:
    """Flatten an XREAD reply into (message_id, fields) pairs."""
    messages: list[tuple[str, dict[str, str]]] = []
    if not isinstance(raw, Sequence) or isinstance(raw, str | bytes):
        return messages
    for stream in raw:
        if not isinstance(stream, Sequence) or len(stream) != 2:
            continue
        entries = stream[1]
        if not isinstance(entries, Sequence) or isinstance(entries, str | bytes):
            continue
        for entry in entries:
            if not isinstance(entry, Sequence) or len(entry) != 2:
                continue
            message_id, fields = entry[0], entry[1]
            if not isinstance(fields, dict):
                continue
            messages.append(
                (_as_text(message_id), {_as_text(k): _as_text(v) for k, v in fields.items()})
            )
    return messages


class RedisRunEventSubscription:
    def __init__(self, client: Redis, run_id: str, last_id: str) -> None:
        self._client = client
        self._key = stream_key(run_id)
        self._last_id = last_id
        self._closed = False

    async def __aiter__(self) -> AsyncIterator[RunEvent]:
        while not self._closed:
            raw = await self._client.xread(
                {self._key: self._last_id}, count=100, block=BLOCK_MILLISECONDS
            )
            for message_id, fields in _parse_read_reply(raw):
                self._last_id = message_id
                yield _decode(fields)

    async def aclose(self) -> None:
        self._closed = True


class RedisRunEventPublisher:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def publish(self, event: RunEvent) -> None:
        await self._client.xadd(
            stream_key(event.run_id),
            _encode(event),
            maxlen=STREAM_MAX_LENGTH,
            approximate=True,
        )

    async def subscribe(self, run_id: str) -> RedisRunEventSubscription:
        # Anchor at the stream's current end *before* the caller reads durable
        # history, so an event published in between is delivered rather than lost.
        entries = await self._client.xrevrange(stream_key(run_id), count=1)
        last_id = _as_text(entries[0][0]) if entries else STREAM_START
        return RedisRunEventSubscription(self._client, run_id, last_id)
