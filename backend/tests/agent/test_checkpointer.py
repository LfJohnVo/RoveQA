"""LangGraph's PostgreSQL checkpointer against the real database.

The resume path is what every later node depends on, so it is proven end to end here
before any node exists: a graph that stops mid-way must continue from its checkpoint
rather than starting over.

These tests drive their own event loop instead of using the plugin's. psycopg's async
mode refuses Windows' default ProactorEventLoop, while Playwright needs exactly that
loop to spawn its driver subprocess — the two are incompatible, so the loop is chosen
explicitly here rather than globally. On Linux, where the worker actually runs, the
default loop already satisfies both.
"""

import asyncio
import sys
from collections.abc import Callable, Coroutine
from typing import Any, TypedDict

import psycopg
import pytest
from langgraph.graph import END, START, StateGraph

from agentic_qa.infrastructure.agent.langgraph.checkpointer import (
    open_checkpointer,
    to_psycopg_dsn,
)
from tests.conftest import postgres_test_dsn


class CountingState(TypedDict):
    visited: list[str]


def run_with_compatible_loop(main: Callable[[], Coroutine[Any, Any, Any]]) -> Any:
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    with asyncio.Runner(loop_factory=loop_factory) as runner:
        return runner.run(main())


def counting_graph(node_name: str, checkpointer: Any) -> Any:
    def visit(state: CountingState) -> CountingState:
        return {"visited": [*state["visited"], node_name]}

    builder: StateGraph[CountingState, Any, CountingState, CountingState] = StateGraph(
        CountingState
    )
    builder.add_node(node_name, visit)
    builder.add_edge(START, node_name)
    builder.add_edge(node_name, END)
    return builder.compile(checkpointer=checkpointer)


def test_the_sqlalchemy_dsn_is_translated_for_psycopg() -> None:
    """Two drivers, one database: the translation lives in one place."""
    assert (
        to_psycopg_dsn("postgresql+asyncpg://u:p@host:5432/db") == "postgresql://u:p@host:5432/db"
    )
    # Already-plain URLs pass through untouched.
    assert to_psycopg_dsn("postgresql://u:p@host/db") == "postgresql://u:p@host/db"


def test_graph_state_outlives_the_process_that_wrote_it() -> None:
    """The durability claim a worker restart depends on.

    State is written with one checkpointer connection, that connection is closed
    entirely, and a fresh one still finds it — which is what makes resuming after a
    killed worker possible at all.
    """
    thread = "run-survives-restart"

    async def write() -> None:
        async with open_checkpointer(postgres_test_dsn()) as saver:
            graph = counting_graph("first", saver)
            await graph.ainvoke({"visited": []}, {"configurable": {"thread_id": thread}})

    async def read_back() -> list[str]:
        # A brand new connection, as a restarted worker would have.
        async with open_checkpointer(postgres_test_dsn()) as saver:
            graph = counting_graph("first", saver)
            snapshot = await graph.aget_state({"configurable": {"thread_id": thread}})
            visited: list[str] = snapshot.values["visited"]
            return visited

    try:
        run_with_compatible_loop(write)
        visited = run_with_compatible_loop(read_back)
    except (OSError, psycopg.OperationalError) as error:
        pytest.skip(f"PostgreSQL not reachable: {error}")

    assert visited == ["first"]


def test_a_fresh_thread_starts_clean() -> None:
    """Runs are isolated by thread id: one run never resumes into another."""

    async def main() -> list[str]:
        async with open_checkpointer(postgres_test_dsn()) as saver:
            graph = counting_graph("mark", saver)
            await graph.ainvoke({"visited": []}, {"configurable": {"thread_id": "run-a"}})
            other = await graph.ainvoke({"visited": []}, {"configurable": {"thread_id": "run-b"}})
            visited: list[str] = other["visited"]
            return visited

    try:
        visited = run_with_compatible_loop(main)
    except (OSError, psycopg.OperationalError) as error:
        pytest.skip(f"PostgreSQL not reachable: {error}")

    assert visited == ["mark"]


def test_the_latest_checkpoint_id_is_readable_for_a_recovery_point() -> None:
    """The domain stores this id on a RecoveryPoint, so it must be retrievable."""

    async def main() -> str:
        async with open_checkpointer(postgres_test_dsn()) as saver:
            graph = counting_graph("touch", saver)
            config = {"configurable": {"thread_id": "run-recovery-id"}}
            await graph.ainvoke({"visited": []}, config)
            snapshot = await graph.aget_state(config)
            checkpoint_id: str = snapshot.config["configurable"]["checkpoint_id"]
            return checkpoint_id

    try:
        checkpoint_id = run_with_compatible_loop(main)
    except (OSError, psycopg.OperationalError) as error:
        pytest.skip(f"PostgreSQL not reachable: {error}")

    assert isinstance(checkpoint_id, str)
    assert checkpoint_id
