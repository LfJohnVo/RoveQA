"""Compiling a story into a plan, and the plan surviving a round trip.

Two properties carry the phase: every acceptance criterion is traceable to a step (or a
failed run cannot say *what* is not met), and an exported plan re-imports as the same
plan (or a plan drifts a little on every hop between the API, the CLI and an agent).
"""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from agentic_qa.application.contracts.test_plan import from_document, to_document
from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.qa.test_plan import (
    MemoryPolicy,
    PlanBudget,
    PlanMode,
    PlanPriority,
    PlanStep,
    PlanStepType,
    compile_story,
)
from agentic_qa.domain.qa.test_plan import TestPlan as Plan  # pytest collects Test*
from agentic_qa.domain.qa.user_story import AcceptanceCriterion, UserStory


def contract_path() -> Path:
    """Find the published schema, whichever layout the suite runs in.

    Mounted at /app/contracts in the gates container, and at the repository root when
    someone runs the suite from a checkout. Searching upward beats hard-coding a depth
    that is right in one of those and silently wrong in the other.
    """
    for directory in Path(__file__).resolve().parents:
        candidate = directory / "contracts" / "test-plan.schema.json"
        if candidate.exists():
            return candidate
    raise AssertionError("contracts/test-plan.schema.json not found")


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    """The published schema, not a copy of it: drift between them must show up here."""
    return Draft202012Validator(json.loads(contract_path().read_text(encoding="utf-8")))


def story(**overrides: Any) -> UserStory:
    defaults: dict[str, Any] = {
        "story_id": "story-checkout",
        "project_id": "project-1",
        "actor": "a signed-in shopper",
        "goal": "check out with a saved card",
        "acceptance_criteria": (
            AcceptanceCriterion(
                criterion_id="ac-1",
                description="the order confirmation page shows an order number",
            ),
            AcceptanceCriterion(
                criterion_id="ac-2",
                description="the cart is empty afterwards",
                verification_hint="the cart badge shows 0",
            ),
        ),
    }
    return UserStory(**{**defaults, **overrides})


def compiled(**overrides: Any) -> Plan:
    return compile_story(
        story(**overrides), plan_id="plan-1", plan_version="1", run_policy_id="policy-1"
    )


class TestCompilation:
    def test_every_acceptance_criterion_becomes_a_traceable_assertion(self) -> None:
        plan = compiled()

        assert plan.covered_criteria == {"ac-1", "ac-2"}
        for criterion_id in ("ac-1", "ac-2"):
            steps = plan.steps_for(criterion_id)
            assert len(steps) == 1
            assert steps[0].type is PlanStepType.ASSERTION

    def test_compiling_the_same_story_twice_gives_the_same_plan(self) -> None:
        """Reproducibility is a property of compilation, not of the weather.

        No model participates here, so a story that passed yesterday is compiled into
        the same plan today.
        """
        assert compiled() == compiled()

    def test_preconditions_become_action_steps_before_the_goal(self) -> None:
        plan = compiled(preconditions=("a product is in the cart", "a card is saved"))

        kinds = [(step.step_id, step.type) for step in plan.plan_steps]
        assert kinds[:3] == [
            ("pre-1", PlanStepType.ACTION),
            ("pre-2", PlanStepType.ACTION),
            ("goal", PlanStepType.ACTION),
        ]

    def test_the_goal_step_names_the_actor(self) -> None:
        plan = compiled()

        goal_step = next(step for step in plan.plan_steps if step.step_id == "goal")
        assert goal_step.description == "As a signed-in shopper, check out with a saved card"

    def test_forbidden_outcomes_are_carried_into_the_plan(self) -> None:
        """A constraint the story stated must not be lost by compiling it."""
        plan = compiled(forbidden_outcomes=("charging the card twice",))

        assert "charging the card twice" in plan.description

    def test_the_plan_records_where_it_came_from(self) -> None:
        plan = compiled()

        assert plan.source_story_id == "story-checkout"
        assert plan.mode is PlanMode.STORY


class TestInvariants:
    def test_an_assertion_must_name_a_criterion(self) -> None:
        """An assertion tracing back to nothing can pass or fail without meaning."""
        with pytest.raises(InvalidEntityError, match="must name a criterion"):
            PlanStep(step_id="a", type=PlanStepType.ASSERTION, description="something is true")

    def test_a_plan_that_bounds_nothing_and_names_no_policy_is_refused(self) -> None:
        with pytest.raises(InvalidEntityError, match="run_policy_id or a budget"):
            compile_story(story(), plan_id="plan-1", plan_version="1")

    def test_a_budget_alone_is_enough(self) -> None:
        plan = compile_story(
            story(), plan_id="plan-1", plan_version="1", budget=PlanBudget(max_actions=20)
        )

        assert plan.budget is not None

    def test_an_empty_budget_is_not_a_budget(self) -> None:
        with pytest.raises(InvalidEntityError, match="bound at least one thing"):
            PlanBudget()

    def test_duplicate_step_ids_are_refused(self) -> None:
        with pytest.raises(InvalidEntityError, match="duplicate plan step id"):
            Plan(
                plan_id="plan-1",
                plan_version="1",
                project_id="project-1",
                name="dupes",
                mode=PlanMode.STORY,
                run_policy_id="policy-1",
                plan_steps=(
                    PlanStep(step_id="s1", type=PlanStepType.ACTION, description="one"),
                    PlanStep(step_id="s1", type=PlanStepType.ACTION, description="two"),
                ),
            )

    def test_step_ids_stay_within_the_contract_alphabet(self) -> None:
        """Step ids end up in file names and report anchors."""
        with pytest.raises(InvalidEntityError, match="step_id must match"):
            PlanStep(step_id="../etc/passwd", type=PlanStepType.ACTION, description="nope")


class TestPortability:
    def test_a_compiled_plan_validates_against_the_published_schema(
        self, validator: Draft202012Validator
    ) -> None:
        errors = sorted(validator.iter_errors(to_document(compiled())), key=str)

        assert errors == [], [error.message for error in errors]

    def test_a_fully_populated_plan_validates_too(self, validator: Draft202012Validator) -> None:
        plan = Plan(
            plan_id="plan-9",
            plan_version="3.1",
            project_id="project-1",
            name="regression sweep",
            mode=PlanMode.REGRESSION,
            plan_steps=(
                PlanStep(step_id="goal", type=PlanStepType.ACTION, description="do the thing"),
                PlanStep(
                    step_id="assert-1",
                    type=PlanStepType.ASSERTION,
                    description="it happened",
                    criterion_id="ac-1",
                    critical=True,
                ),
            ),
            source_story_id="story-1",
            environment_id="env-1",
            run_policy_id="policy-1",
            budget=PlanBudget(max_actions=50, max_duration_seconds=600, max_model_calls=20),
            description="everything set",
            priority=PlanPriority.P0,
            memory_policy=MemoryPolicy.FROZEN,
            metadata=(("owner", "qa"), ("retries", 3), ("flaky", False), ("note", None)),
        )

        errors = sorted(validator.iter_errors(to_document(plan)), key=str)

        assert errors == [], [error.message for error in errors]

    def test_export_then_import_returns_the_same_plan(self) -> None:
        plan = compiled(preconditions=("a product is in the cart",))

        assert from_document(to_document(plan)) == plan

    def test_a_round_trip_keeps_metadata_value_types(self) -> None:
        """`3` must not come back as `"3"`: a plan drifting on every hop is not portable."""
        plan = Plan(
            plan_id="plan-1",
            plan_version="1",
            project_id="project-1",
            name="typed metadata",
            mode=PlanMode.STORY,
            run_policy_id="policy-1",
            plan_steps=(PlanStep(step_id="goal", type=PlanStepType.ACTION, description="go"),),
            metadata=(("retries", 3), ("flaky", True), ("ratio", 0.5), ("note", None)),
        )

        assert from_document(to_document(plan)).metadata == plan.metadata

    def test_a_round_trip_survives_json(self) -> None:
        """The real hop is a file or an HTTP body, not a dict in the same process."""
        plan = compiled()

        assert from_document(json.loads(json.dumps(to_document(plan)))) == plan

    def test_a_document_from_an_unknown_contract_version_is_refused(self) -> None:
        document = to_document(compiled())
        document["schema_version"] = "roveqa.test-plan.v2"

        with pytest.raises(InvalidEntityError, match="unsupported plan schema_version"):
            from_document(document)

    def test_a_hand_authored_document_may_be_given_an_identity_but_never_invents_one(self) -> None:
        document = to_document(compiled())
        del document["plan_id"]
        del document["plan_version"]

        with pytest.raises(InvalidEntityError, match="needs plan_id and plan_version"):
            from_document(document)

        adopted = from_document(document, plan_id="plan-imported", plan_version="1")
        assert adopted.plan_id == "plan-imported"

    def test_an_unknown_mode_is_refused_rather_than_defaulted(self) -> None:
        document = to_document(compiled())
        document["mode"] = "freestyle"

        with pytest.raises(InvalidEntityError, match="mode has an unknown value"):
            from_document(document)
