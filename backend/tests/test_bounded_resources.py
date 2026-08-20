"""Every bound this system relies on, exercised with an input that would break it.

The failure mode this file exists to prevent is quiet. A limit that gets deleted, or
one that was never wired to the code path it was written for, breaks nothing visible —
until an adversarial or merely large input arrives and the answer is a prompt nobody can
pay for, a page nobody can render, or a process that runs out of memory.

Two rules for every test here:

- **Feed something that would actually break the bound.** Asserting that a small input
  stays small proves nothing.
- **Name the constant in the assertion.** Deleting `MAX_GOAL_CHARS` has to fail this
  file, not silently uncap a prompt.

Bounds already covered where they live are not repeated: the working step window
(`tests/agent/`), affordance and snapshot caps (`tests/exploration/test_affordances.py`),
observation normalisation (`tests/triage/test_clustering.py`), redaction payloads and
memory context size (`tests/knowledge/`).
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest

from agentic_qa.application.ports.events import DEFAULT_EVENT_PAGE_SIZE, MAX_EVENT_PAGE_SIZE
from agentic_qa.application.ports.models import PlanningRequest
from agentic_qa.bootstrap.container import Container
from agentic_qa.domain.agent.state import MAX_RECENT_STEPS, AgentState, StepOutcome, StepRecord
from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.knowledge.compatibility import Compatibility
from agentic_qa.domain.knowledge.memory_context import MemoryItem
from agentic_qa.domain.qa.test_plan import (
    MAX_PLAN_STEPS,
    PlanMode,
    PlanStep,
    PlanStepType,
)
from agentic_qa.domain.qa.test_plan import TestPlan as Plan  # pytest would collect the name
from agentic_qa.domain.validation import MAX_IDENTIFIER_LENGTH, MAX_TEXT_LENGTH, require_text
from agentic_qa.infrastructure.inference.prompts import (
    MAX_DETAIL_CHARS,
    MAX_GOAL_CHARS,
    MAX_MEMORY_CHARS,
    MAX_OBSERVATION_CHARS,
    build_planning_prompt,
)
from agentic_qa.interfaces.http.app import create_app
from tests.fakes.repositories import InMemoryStore
from tests.fakes.unit_of_work import InMemoryUnitOfWork

HOSTILE = 200_000
"""Bigger than any bound here, and the size a real page of generated content reaches."""

# Filler uses letters that do not occur in the prompt's own framing, so counting a
# letter measures the clipped value rather than the labels around it.


def plan_of(steps: int) -> Plan:
    return Plan(
        plan_id="plan-1",
        plan_version="v1",
        project_id="proj-1",
        name="everything",
        mode=PlanMode.STORY,
        plan_steps=tuple(step(index) for index in range(steps)),
        run_policy_id="pol-1",
    )


def remembered(candidate_id: str, summary: str) -> MemoryItem:
    return MemoryItem(
        memory_id=f"m-{candidate_id}",
        candidate_id=candidate_id,
        kind="acceptance_fact",
        summary=summary,
        observed=True,
        model_derived=False,
        reliability=0.9,
        freshness=1.0,
        compatibility=Compatibility.EXACT,
        source_run_id="run-0",
        valid_from=datetime(2026, 8, 20, tzinfo=UTC),
    )


def step(index: int) -> PlanStep:
    return PlanStep(
        step_id=f"s{index}",
        type=PlanStepType.ACTION,
        description=f"do thing {index}",
    )


class TestThePromptCannotGrowWithThePage:
    """A page is untrusted input of unbounded size. The prompt built from it is not."""

    def test_a_huge_observation_is_clipped(self) -> None:
        prompt = build_planning_prompt(
            PlanningRequest(goal="place an order", observation="x" * HOSTILE)
        )

        assert len(prompt) < MAX_OBSERVATION_CHARS + MAX_GOAL_CHARS + 500
        assert "[truncated]" in prompt

    def test_a_huge_goal_is_clipped(self) -> None:
        prompt = build_planning_prompt(
            PlanningRequest(goal="Q" * HOSTILE, observation="a normal page")
        )

        assert prompt.count("Q") <= MAX_GOAL_CHARS

    def test_a_huge_step_detail_is_clipped(self) -> None:
        prompt = build_planning_prompt(
            PlanningRequest(
                goal="place an order",
                observation="a normal page",
                recent_steps=(
                    StepRecord(
                        index=1,
                        intent="click",
                        outcome=StepOutcome.FAILED,
                        detail="W" * HOSTILE,
                    ),
                ),
            )
        )

        assert prompt.count("W") <= MAX_DETAIL_CHARS

    def test_a_huge_memory_summary_is_clipped(self) -> None:
        # Memory is derived from earlier runs of the page under test, so it inherits the
        # page's ability to be enormous.
        prompt = build_planning_prompt(
            PlanningRequest(
                goal="place an order",
                observation="a normal page",
                memory=(remembered("c-1", "Z" * HOSTILE),),
            )
        )

        assert prompt.count("Z") <= MAX_MEMORY_CHARS

    def test_the_whole_prompt_stays_flat_under_every_pressure_at_once(self) -> None:
        """The property that matters: prompt size does not grow with run length, page
        size, memory size or step history."""
        agent = AgentState(run_id="run-1", goal="Q" * HOSTILE)
        for index in range(500):
            agent.record_step(
                StepRecord(
                    index=index,
                    intent="i" * 1000,
                    outcome=StepOutcome.SUCCEEDED,
                    detail="W" * 1000,
                )
            )

        prompt = build_planning_prompt(
            PlanningRequest(
                goal=agent.goal,
                observation="x" * HOSTILE,
                recent_steps=agent.recent_steps,
                memory=tuple(remembered(f"c-{index}", "Z" * 1000) for index in range(50)),
            )
        )

        # Every part is capped, so the total is a sum of caps rather than of inputs.
        ceiling = (
            MAX_GOAL_CHARS
            + MAX_OBSERVATION_CHARS
            + MAX_RECENT_STEPS * MAX_DETAIL_CHARS * 2
            + 50 * MAX_MEMORY_CHARS
            + 5_000  # framing, labels and delimiters
        )
        assert len(prompt) < ceiling


class TestPlansAndTextAreBoundedByTheDomain:
    def test_a_plan_larger_than_the_contract_allows_is_refused(self) -> None:
        with pytest.raises(InvalidEntityError, match=str(MAX_PLAN_STEPS)):
            plan_of(MAX_PLAN_STEPS + 1)

    def test_a_plan_at_the_limit_is_accepted(self) -> None:
        # The bound is a limit, not an off-by-one that rejects a legal plan.
        plan = plan_of(MAX_PLAN_STEPS)

        assert len(plan.plan_steps) == MAX_PLAN_STEPS

    def test_unbounded_text_is_refused_rather_than_stored(self) -> None:
        # Refused, not truncated: silently storing half of what somebody sent is a
        # different value than the one they sent.
        with pytest.raises(InvalidEntityError):
            require_text("t" * (MAX_TEXT_LENGTH + 1), field="observation")

    def test_an_identifier_cannot_be_a_document(self) -> None:
        with pytest.raises(InvalidEntityError):
            require_text(
                "i" * (MAX_IDENTIFIER_LENGTH + 1),
                field="criterion_id",
                max_length=MAX_IDENTIFIER_LENGTH,
            )


class TestPagesOfResultsAreBounded:
    def test_the_event_page_size_has_a_ceiling_and_a_default(self) -> None:
        """A client asking for a million events is asking the API to buffer a million
        events. The cap is the contract's, so the HTTP layer and the CLI agree."""
        assert DEFAULT_EVENT_PAGE_SIZE <= MAX_EVENT_PAGE_SIZE
        assert MAX_EVENT_PAGE_SIZE <= 1000


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    store = InMemoryStore()
    transport = httpx.ASGITransport(
        app=create_app(Container(unit_of_work=lambda: InMemoryUnitOfWork(store))),
        raise_app_exceptions=True,
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://api") as opened:
        yield opened


async def test_the_api_refuses_an_unbounded_event_page(client: httpx.AsyncClient) -> None:
    """The ceiling is enforced at the boundary, not trusted to callers.

    A client asking for a million events is asking the API to buffer a million events.
    """
    response = await client.get(
        "/api/v1/runs/does-not-matter/events", params={"limit": MAX_EVENT_PAGE_SIZE + 1}
    )

    assert response.status_code == 422
