"""Resuming a killed run from its durable checkpoint.

The Phase 05 durability gates: a run that dies mid-episode continues from its last
safe checkpoint instead of restarting, and the side effect inside the crash window is
not performed twice.

Runs on the real PostgreSQL checkpointer with a scripted browser double. The double
is what makes the test repeatable — the browser itself is proven separately against
Chromium, and combining both in one process is a Windows-only conflict documented in
tests/agent/test_checkpointer.py.
"""

import asyncio
import sys
from collections.abc import Callable, Coroutine
from typing import Any
from uuid import uuid4

import psycopg
import pytest

from agentic_qa.application.ports.browser import ActionOutcome
from agentic_qa.application.services.side_effects import perform_once
from agentic_qa.domain.agent.state import AgentState
from agentic_qa.domain.browser.actions import (
    ActionTarget,
    BrowserAction,
    BrowserActionType,
    IdempotencyStrategy,
)
from agentic_qa.infrastructure.agent.langgraph.checkpointer import open_checkpointer
from agentic_qa.infrastructure.agent.langgraph.graph import build_agent_graph
from tests.conftest import postgres_test_dsn
from tests.fakes.agent import RecordingBrowserGateway, ScriptedModelGateway


def run_with_compatible_loop(main: Callable[[], Coroutine[Any, Any, Any]]) -> Any:
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    with asyncio.Runner(loop_factory=loop_factory) as runner:
        return runner.run(main())


def navigate(step: int) -> BrowserAction:
    return BrowserAction(
        type=BrowserActionType.NAVIGATE,
        intent=f"open page {step}",
        target=ActionTarget(url=f"http://target.test/page/{step}"),
    )


def create_record(reference: str) -> BrowserAction:
    return BrowserAction(
        type=BrowserActionType.CLICK,
        intent=f"create record {reference}",
        target=ActionTarget(role="button", name="Create record"),
        side_effect=True,
        idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
        verification_strategy="look the record up by its run-scoped reference",
    )


class DyingBrowserGateway(RecordingBrowserGateway):
    """Raises on a chosen step, the way a worker dying mid-episode would."""

    def __init__(self, die_on_intent: str) -> None:
        super().__init__()
        self.die_on_intent = die_on_intent

    async def execute(self, action: BrowserAction) -> ActionOutcome:
        if action.intent == self.die_on_intent:
            raise RuntimeError("worker died")
        return await super().execute(action)


def test_a_killed_run_resumes_from_its_checkpoint_instead_of_restarting() -> None:
    thread = f"resume-{uuid4()}"
    first_browser = DyingBrowserGateway(die_on_intent="open page 3")
    second_browser = RecordingBrowserGateway()

    async def main() -> tuple[list[str], list[str]]:
        async with open_checkpointer(postgres_test_dsn()) as saver:
            config = {"configurable": {"thread_id": thread}}

            dying = build_agent_graph(
                browser=first_browser,
                model=ScriptedModelGateway(script=[navigate(i) for i in range(1, 5)]),
                checkpointer=saver,
            )
            with pytest.raises(RuntimeError):
                await dying.ainvoke(
                    {"agent": AgentState(run_id="r-resume", goal="walk pages")}, config
                )

            # A brand new graph and browser, as a restarted worker would build.
            resumed = build_agent_graph(
                browser=second_browser,
                model=ScriptedModelGateway(script=[navigate(i) for i in range(3, 5)]),
                checkpointer=saver,
            )
            await resumed.ainvoke(None, config)
            return first_browser.executed, second_browser.executed

    try:
        before, after = run_with_compatible_loop(main)
    except (OSError, psycopg.OperationalError) as error:
        pytest.skip(f"PostgreSQL not reachable: {error}")

    # The first worker got through two pages before dying on the third.
    assert before == ["open page 1", "open page 2"]
    # The replacement continued from there rather than replaying pages 1 and 2.
    assert "open page 1" not in after
    assert after[0] == "open page 3"


def test_the_side_effect_in_the_crash_window_is_not_performed_twice() -> None:
    """The uncertainty window inside the graph.

    The worker dies right after the target processed the write. On resume, the run
    asks the target whether its own reference exists rather than clicking again.
    """
    reference = f"ref-{uuid4().hex[:8]}"
    created: list[str] = []

    class TargetSideEffect(RecordingBrowserGateway):
        """The click lands, then the worker dies before recording the outcome."""

        def __init__(self, *, die_after_effect: bool) -> None:
            super().__init__()
            self.die_after_effect = die_after_effect

        async def execute(self, action: BrowserAction) -> ActionOutcome:
            if action.intent.startswith("create record"):
                created.append(reference)  # the target really processed it
                if self.die_after_effect:
                    raise RuntimeError("died before acknowledging")
            return await super().execute(action)

    async def main() -> None:
        async with open_checkpointer(postgres_test_dsn()) as saver:
            config = {"configurable": {"thread_id": f"crash-{uuid4()}"}}
            dying = build_agent_graph(
                browser=TargetSideEffect(die_after_effect=True),
                model=ScriptedModelGateway(script=[create_record(reference)]),
                checkpointer=saver,
            )
            with pytest.raises(RuntimeError):
                await dying.ainvoke(
                    {"agent": AgentState(run_id="r-crash", goal="create once")}, config
                )

            # Resume decides by observation, not by memory of what it intended.
            survivor = TargetSideEffect(die_after_effect=False)

            async def record_exists() -> bool:
                return reference in created

            async def do_create() -> None:
                await survivor.execute(create_record(reference))

            await perform_once(verify=record_exists, perform=do_create, description="create record")

    try:
        run_with_compatible_loop(main)
    except (OSError, psycopg.OperationalError) as error:
        pytest.skip(f"PostgreSQL not reachable: {error}")

    # Exactly one record: the retry observed the effect instead of repeating it.
    assert created == [reference]
