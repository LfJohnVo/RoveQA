"""Request identity, propagated to responses and logs.

`X-Request-Id` is accepted from the caller or generated, kept in a context variable
for the whole request, echoed in every response and attached to every log record, so
one identifier correlates client, API and (from Phase 02 activities) run events.
"""

import logging
from contextvars import ContextVar
from uuid import uuid4

REQUEST_ID_HEADER = "X-Request-Id"
MAX_INBOUND_REQUEST_ID_LENGTH = 200

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(value: str) -> None:
    _request_id.set(value)


def get_request_id() -> str:
    return _request_id.get()


def new_request_id() -> str:
    return str(uuid4())


def accept_inbound_request_id(raw: str | None) -> str:
    """Reuse the caller's id when it is sane, otherwise mint one.

    An unbounded or blank header is caller-controlled input and must not reach logs
    verbatim (bounded payloads, docs/11).
    """
    if raw is None:
        return new_request_id()
    candidate = raw.strip()
    if not candidate or len(candidate) > MAX_INBOUND_REQUEST_ID_LENGTH:
        return new_request_id()
    return candidate


class RequestIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True
