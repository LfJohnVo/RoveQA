"""The portable TestPlan document (`contracts/test-plan.schema.json`).

Separate from the HTTP DTOs because more than one delivery path carries a plan: the
API returns it, the CLI exports and imports it as a file, and an agent may hand one in
that nothing in this system ever wrote. All of them must agree on one shape, so the
mapping lives once, above every adapter and below every delivery mechanism.

Round-tripping is a property this module owes: a plan exported and imported again must
be the same plan, including metadata value types. A document that quietly turned
`"retries": 3` into `"3"` would drift a little on every hop.
"""

from typing import Any

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.qa.test_plan import (
    SCHEMA_VERSION,
    MemoryPolicy,
    MetadataValue,
    PlanBudget,
    PlanMode,
    PlanPriority,
    PlanStep,
    PlanStepType,
    TestPlan,
)


def to_document(plan: TestPlan) -> dict[str, Any]:
    """Serialize to the public contract. Absent optionals are omitted, not nulled:
    the schema forbids unknown shapes and a null is not the same as "not stated"."""
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "plan_id": plan.plan_id,
        "plan_version": plan.plan_version,
        "project_id": plan.project_id,
        "name": plan.name,
        "mode": plan.mode.value,
        "memory_policy": plan.memory_policy.value,
        "plan_steps": [_step_document(step) for step in plan.plan_steps],
    }
    if plan.description:
        document["description"] = plan.description
    if plan.priority is not None:
        document["priority"] = plan.priority.value
    if plan.source_story_id is not None:
        document["source_story_id"] = plan.source_story_id
    if plan.environment_id is not None:
        document["environment_id"] = plan.environment_id
    if plan.run_policy_id is not None:
        document["run_policy_id"] = plan.run_policy_id
    if plan.budget is not None:
        document["budget"] = _budget_document(plan.budget)
    if plan.metadata:
        document["metadata"] = dict(plan.metadata)
    return document


def from_document(
    document: dict[str, Any], *, plan_id: str | None = None, plan_version: str | None = None
) -> TestPlan:
    """Parse a portable plan, refusing anything the contract does not describe.

    `plan_id`/`plan_version` may be supplied by the caller for a hand-authored document
    that carries no identity. What this will not do is mint one silently: importing the
    same file twice would then produce two unrelated plans that look identical.
    """
    _require_schema_version(document)

    resolved_id = document.get("plan_id") or plan_id
    resolved_version = document.get("plan_version") or plan_version
    if not resolved_id or not resolved_version:
        raise InvalidEntityError(
            "a plan document needs plan_id and plan_version, or explicit values for them"
        )

    steps = document.get("plan_steps")
    if not isinstance(steps, list):
        raise InvalidEntityError("plan_steps must be a list")

    return TestPlan(
        plan_id=str(resolved_id),
        plan_version=str(resolved_version),
        project_id=_required_str(document, "project_id"),
        name=_required_str(document, "name"),
        mode=_enum(PlanMode, document.get("mode"), field="mode"),
        plan_steps=tuple(_step_from(step) for step in steps),
        source_story_id=_optional_str(document, "source_story_id"),
        environment_id=_optional_str(document, "environment_id"),
        run_policy_id=_optional_str(document, "run_policy_id"),
        budget=_budget_from(document.get("budget")),
        description=document.get("description", "") or "",
        priority=(
            _enum(PlanPriority, document["priority"], field="priority")
            if document.get("priority") is not None
            else None
        ),
        memory_policy=(
            _enum(MemoryPolicy, document["memory_policy"], field="memory_policy")
            if document.get("memory_policy") is not None
            else MemoryPolicy.NORMAL
        ),
        metadata=_metadata_from(document.get("metadata")),
    )


def _step_document(step: PlanStep) -> dict[str, Any]:
    document: dict[str, Any] = {
        "step_id": step.step_id,
        "type": step.type.value,
        "description": step.description,
        "critical": step.critical,
    }
    if step.criterion_id is not None:
        document["criterion_id"] = step.criterion_id
    return document


def _step_from(raw: Any) -> PlanStep:
    if not isinstance(raw, dict):
        raise InvalidEntityError("each plan step must be an object")
    return PlanStep(
        step_id=_required_str(raw, "step_id"),
        type=_enum(PlanStepType, raw.get("type"), field="type"),
        description=_required_str(raw, "description"),
        criterion_id=_optional_str(raw, "criterion_id"),
        critical=bool(raw.get("critical", False)),
    )


def _budget_document(budget: PlanBudget) -> dict[str, int]:
    fields = {
        "max_actions": budget.max_actions,
        "max_duration_seconds": budget.max_duration_seconds,
        "max_model_calls": budget.max_model_calls,
    }
    return {name: value for name, value in fields.items() if value is not None}


def _budget_from(raw: Any) -> PlanBudget | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise InvalidEntityError("budget must be an object")
    return PlanBudget(
        max_actions=_optional_int(raw, "max_actions"),
        max_duration_seconds=_optional_int(raw, "max_duration_seconds"),
        max_model_calls=_optional_int(raw, "max_model_calls"),
    )


def _metadata_from(raw: Any) -> tuple[tuple[str, MetadataValue], ...]:
    if raw is None:
        return ()
    if not isinstance(raw, dict):
        raise InvalidEntityError("metadata must be an object")
    entries: list[tuple[str, MetadataValue]] = []
    for key, value in raw.items():
        if not isinstance(value, str | int | float | bool | type(None)):
            raise InvalidEntityError(f"metadata value for {key} is not a scalar")
        entries.append((str(key), value))
    return tuple(entries)


def _require_schema_version(document: dict[str, Any]) -> None:
    version = document.get("schema_version")
    if version != SCHEMA_VERSION:
        # Refusing an unknown version beats guessing: a document from a future contract
        # may mean something different by the same field names.
        raise InvalidEntityError(
            f"unsupported plan schema_version: {version!r} (expected {SCHEMA_VERSION!r})"
        )


def _required_str(document: dict[str, Any], field: str) -> str:
    value = document.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InvalidEntityError(f"{field} is required")
    return value


def _optional_str(document: dict[str, Any], field: str) -> str | None:
    value = document.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidEntityError(f"{field} must be a string")
    return value


def _optional_int(document: dict[str, Any], field: str) -> int | None:
    value = document.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidEntityError(f"{field} must be an integer")
    return value


def _enum[EnumT: PlanMode | PlanStepType | PlanPriority | MemoryPolicy](
    enum_type: type[EnumT], value: Any, *, field: str
) -> EnumT:
    try:
        return enum_type(value)
    except ValueError as error:
        raise InvalidEntityError(f"{field} has an unknown value: {value!r}") from error
