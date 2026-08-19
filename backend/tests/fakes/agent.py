"""Deterministic doubles for the agent graph.

The planner is scripted rather than random so a durability test can be re-run and
mean the same thing. The browser double records what it was asked to do and can be
told to fail a specific step, which is how recovery gets exercised without a flaky
page.
"""

from dataclasses import dataclass, field

from agentic_qa.application.ports.browser import ActionOutcome
from agentic_qa.application.ports.models import (
    CriterionJudgement,
    JudgementRequest,
    PlannedAction,
    PlanningRequest,
)
from agentic_qa.domain.browser.actions import BrowserAction


@dataclass
class ScriptedModelGateway:
    """Returns the scripted actions in order, then reports the goal is reached."""

    script: list[BrowserAction] = field(default_factory=list)
    calls: int = 0
    judgements: dict[str, bool | None] = field(default_factory=dict)
    """criterion description -> satisfied. Anything unscripted comes back as unclear,
    which is what a real model should also say when it cannot tell."""

    judged: list[str] = field(default_factory=list)

    async def next_action(self, request: PlanningRequest) -> PlannedAction:
        self.calls += 1
        if not self.script:
            return PlannedAction(action=None, rationale="nothing left to do")
        return PlannedAction(action=self.script.pop(0), rationale="scripted")

    async def judge(self, request: JudgementRequest) -> CriterionJudgement:
        self.judged.append(request.criterion)
        return CriterionJudgement(
            satisfied=self.judgements.get(request.criterion), reasoning="scripted judgement"
        )


@dataclass
class RecordingBrowserGateway:
    """Records executed actions; `fail_intents` makes chosen steps fail once."""

    executed: list[str] = field(default_factory=list)
    fail_intents: set[str] = field(default_factory=set)
    url: str = "http://target.test/"
    captures: int = 0

    async def execute(self, action: BrowserAction) -> ActionOutcome:
        self.executed.append(action.intent)
        if action.intent in self.fail_intents:
            self.fail_intents.discard(action.intent)  # fails once, then succeeds
            return ActionOutcome(succeeded=False, current_url=self.url, detail="element missing")
        return ActionOutcome(succeeded=True, current_url=self.url)

    async def capture_screenshot(self) -> bytes:
        self.captures += 1
        return b"fake-png-bytes"

    async def current_url(self) -> str | None:
        return self.url

    async def aclose(self) -> None:
        return None


@dataclass
class CrashingBrowserGateway(RecordingBrowserGateway):
    """Raises on a chosen intent, simulating the worker dying mid-action."""

    crash_on_intent: str | None = None

    async def execute(self, action: BrowserAction) -> ActionOutcome:
        if action.intent == self.crash_on_intent:
            self.executed.append(action.intent)
            raise RuntimeError("worker died mid-action")
        return await super().execute(action)
