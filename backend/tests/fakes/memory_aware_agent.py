"""A planner that reacts to memory, for measuring what memory is worth.

The scripted gateway used elsewhere cannot answer the question this phase has to
answer. Its script is fixed, so a warm run and a cold run take exactly the same steps
and the measured saving is always zero — not because memory is worthless, but because
nothing in the double can use it.

This one behaves the way a competent planner would: with no memory it probes candidate
routes one at a time until the goal is in reach; when memory names the route, it goes
straight there. That is the mechanism the benchmark measures — whether retrieval
reaches the planner in a usable, labelled form and whether acting on it costs fewer
calls and fewer browser actions.

What it deliberately does *not* measure is whether a real language model draws the same
conclusion. That needs the real endpoint, and the benchmark reports which of the two it
ran against rather than presenting one as the other.
"""

from dataclasses import dataclass, field

from agentic_qa.application.ports.models import (
    CriterionJudgement,
    JudgementRequest,
    PlannedAction,
    PlanningRequest,
)
from agentic_qa.domain.browser.actions import (
    ActionTarget,
    BrowserAction,
    BrowserActionType,
)
from agentic_qa.domain.knowledge.compatibility import Compatibility


@dataclass
class MemoryAwarePlanner:
    """Explores when cold; follows a remembered route when warm.

    A hypothesis or an item needing revalidation is *checked*, not followed blindly:
    it costs one confirming step rather than saving one. That is the behaviour the
    system asks a real planner for, so the double has to pay the same price or the
    benchmark would flatter memory that has not been verified.
    """

    goal_url: str
    """The route the goal is behind. The planner does not know it unless it finds it."""

    decoys: tuple[str, ...] = ()
    """Routes a cold planner tries first. Exploration cost, in other words."""

    calls: int = 0
    visited: list[str] = field(default_factory=list)
    followed_memory: bool = False
    revalidated: bool = False

    async def next_action(self, request: PlanningRequest) -> PlannedAction:
        self.calls += 1

        if self.goal_url in self.visited:
            # Done. Continuing to walk the decoys after arriving would make a warm run
            # cost the same as a cold one and hide the saving the benchmark measures.
            return PlannedAction(action=None, rationale="the goal is reachable")

        remembered = self._remembered_route(request)
        if remembered is not None:
            self.followed_memory = True
            return PlannedAction(action=self._goto(remembered), rationale="recalled route")

        for candidate in (*self.decoys, self.goal_url):
            if candidate not in self.visited:
                return PlannedAction(action=self._goto(candidate), rationale="exploring")

        return PlannedAction(action=None, rationale="nothing left to try")

    async def judge(self, request: JudgementRequest) -> CriterionJudgement:
        return CriterionJudgement(satisfied=None, reasoning="not judged in this benchmark")

    def _remembered_route(self, request: PlanningRequest) -> str | None:
        for item in request.memory:
            url = item.summary.removeprefix("reachable: ")
            if url == item.summary:
                continue
            if item.model_derived or item.compatibility is Compatibility.REVALIDATE:
                # Worth checking, never worth trusting. Recorded so the report can say
                # the saving came from verified memory rather than from a guess.
                self.revalidated = True
                continue
            return url
        return None

    def _goto(self, url: str) -> BrowserAction:
        self.visited.append(url)
        return BrowserAction(
            type=BrowserActionType.NAVIGATE,
            intent=f"open {url}",
            target=ActionTarget(url=url),
        )
