"""LangGraph checkpointer wiring.

The graph's own checkpointer owns its tables and its ids; the domain never reads
them. What the domain keeps is a `RecoveryPoint` pointing at one of those ids plus
the browser data needed to rebuild there (ADR 0009).

LangGraph's Postgres saver speaks psycopg, while the rest of the backend speaks
asyncpg through SQLAlchemy. Two drivers against one database is the price of using
the library's own checkpointer instead of reimplementing it; the DSN is translated
here so nothing above this module has to know.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from agentic_qa.domain.agent.state import (
    AgentState,
    EpisodeSummary,
    StepOutcome,
    StepRecord,
)
from agentic_qa.domain.browser.actions import (
    ActionTarget,
    BrowserAction,
    BrowserActionType,
    IdempotencyStrategy,
)
from agentic_qa.domain.qa.verification import (
    CriterionOutcome,
    CriterionResult,
    FailureKind,
)

logger = logging.getLogger(__name__)

CHECKPOINTED_TYPES = (
    AgentState,
    EpisodeSummary,
    StepOutcome,
    StepRecord,
    BrowserAction,
    BrowserActionType,
    ActionTarget,
    IdempotencyStrategy,
    CriterionResult,
    CriterionOutcome,
    FailureKind,
)
"""Exactly what a checkpoint may reconstruct.

LangGraph's default is to rebuild whatever a checkpoint row names and warn about it,
which has two problems. A future release turns that warning into a refusal, and resume
— the whole point of checkpointing — would break on a library upgrade. And until then,
anything able to write to the checkpoint table can name any importable type.

Naming the list from the classes themselves means a rename moves the entry with it
instead of silently dropping it. LangGraph's own safe built-ins stay allowed.
"""


def to_psycopg_dsn(sqlalchemy_dsn: str) -> str:
    """Translate `postgresql+asyncpg://...` into the plain URL psycopg expects."""
    return sqlalchemy_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


def build_serializer() -> JsonPlusSerializer:
    return JsonPlusSerializer(
        allowed_msgpack_modules=[
            (checkpointed.__module__, checkpointed.__qualname__)
            for checkpointed in CHECKPOINTED_TYPES
        ]
    )


@asynccontextmanager
async def open_checkpointer(sqlalchemy_dsn: str) -> AsyncIterator[AsyncPostgresSaver]:
    """Open a checkpointer and make sure its tables exist.

    `setup()` is idempotent, so a worker that restarts mid-run finds the same tables
    and can resume rather than failing on first use.
    """
    dsn = to_psycopg_dsn(sqlalchemy_dsn)
    async with AsyncPostgresSaver.from_conn_string(dsn, serde=build_serializer()) as saver:
        await saver.setup()
        yield saver
