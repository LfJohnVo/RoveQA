"""Story and TestPlan endpoints.

Compiling is a command with a durable result, so it returns the plan version it
created rather than a job id: compilation is deterministic and fast, and there is
nothing to poll.

Plans are returned as the portable contract document (`contracts/test-plan.schema.json`),
not as a bespoke API shape. The same bytes an agent gets from this endpoint can be
saved to a file and handed back in.
"""

from typing import Any

from fastapi import APIRouter, status

from agentic_qa.application.commands.compile_plan import CompilePlanCommand, compile_plan
from agentic_qa.application.commands.create_story import CreateStoryCommand, create_story
from agentic_qa.application.contracts.test_plan import to_document
from agentic_qa.application.errors import NotFoundError
from agentic_qa.domain.qa.test_plan import PlanBudget
from agentic_qa.domain.qa.user_story import AcceptanceCriterion
from agentic_qa.interfaces.http.dependencies import UnitOfWorkDep
from agentic_qa.interfaces.http.schemas import (
    CompilePlanRequest,
    CreateStoryRequest,
    StoryResponse,
)

router = APIRouter(prefix="/api/v1", tags=["plans"])


@router.post(
    "/projects/{project_id}/stories",
    response_model=StoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_story(
    project_id: str, payload: CreateStoryRequest, uow: UnitOfWorkDep
) -> StoryResponse:
    story = await create_story(
        uow,
        CreateStoryCommand(
            project_id=project_id,
            actor=payload.actor,
            goal=payload.goal,
            acceptance_criteria=tuple(
                AcceptanceCriterion(
                    criterion_id=criterion.criterion_id,
                    description=criterion.description,
                    verification_hint=criterion.verification_hint,
                )
                for criterion in payload.acceptance_criteria
            ),
            preconditions=tuple(payload.preconditions),
            forbidden_outcomes=tuple(payload.forbidden_outcomes),
        ),
    )
    return StoryResponse.from_domain(story)


@router.post(
    "/stories/{story_id}/plans",
    status_code=status.HTTP_201_CREATED,
)
async def post_plan(
    story_id: str, payload: CompilePlanRequest, uow: UnitOfWorkDep
) -> dict[str, Any]:
    """Compile the story into a new immutable plan version."""
    budget = (
        PlanBudget(
            max_actions=payload.max_actions,
            max_duration_seconds=payload.max_duration_seconds,
            max_model_calls=payload.max_model_calls,
        )
        if any(
            value is not None
            for value in (
                payload.max_actions,
                payload.max_duration_seconds,
                payload.max_model_calls,
            )
        )
        else None
    )
    plan = await compile_plan(
        uow,
        CompilePlanCommand(
            story_id=story_id,
            run_policy_id=payload.run_policy_id,
            environment_id=payload.environment_id,
            budget=budget,
            plan_id=payload.plan_id,
        ),
    )
    return to_document(plan)


@router.get("/plans/{plan_id}/versions/{plan_version}")
async def read_plan(plan_id: str, plan_version: str, uow: UnitOfWorkDep) -> dict[str, Any]:
    plan = await uow.plans.get(plan_id, plan_version)
    if plan is None:
        raise NotFoundError("test_plan", f"{plan_id}@{plan_version}")
    return to_document(plan)
