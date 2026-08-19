"""TestPlan repository port.

Plans are immutable per version, so there is no `save`: a plan changes by gaining a
version. That is what lets a finished run be re-read against the exact rules it ran
under instead of whatever the plan says today.
"""

from typing import Protocol

from agentic_qa.domain.qa.test_plan import TestPlan


class TestPlanRepository(Protocol):
    async def add(self, plan: TestPlan) -> None:
        """Store a new plan version. Raises AlreadyExistsError if that version exists."""
        ...

    async def get(self, plan_id: str, plan_version: str) -> TestPlan | None: ...

    async def latest(self, plan_id: str) -> TestPlan | None:
        """Most recently created version. Used to *choose* a version at run creation,
        never to resolve one for a run already recorded."""
        ...

    async def list_for_story(self, story_id: str, *, limit: int) -> list[TestPlan]:
        """Plan versions compiled from a story, newest first."""
        ...
