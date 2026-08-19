"""Import a plan document as an immutable version.

The version is the content hash of the normalized document, which docs/12 fixes as
normative for plans that arrive inline rather than compiled from a story. That choice
is what makes submitting a plan naturally idempotent: the same bytes are the same
version, so a client that lost the response and retried gets the plan it already
created instead of a second copy of it.

It also makes the reference in a finished run meaningful. `plan_id@a1b2c3` names
exactly one document forever; a sequential version would name whatever was published
under that number.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from agentic_qa.application.contracts.test_plan import from_document, to_document
from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.qa.test_plan import TestPlan

CONTENT_VERSION_LENGTH = 16


@dataclass(frozen=True)
class ImportPlanResult:
    plan: TestPlan
    created: bool
    """False when the same content was already stored under this version."""


@dataclass(frozen=True)
class ImportPlanCommand:
    document: dict[str, Any]
    plan_id: str
    """Supplied by the caller (or minted by the interface); identity is never invented
    from the content alone, or two unrelated plans with the same steps would merge."""


async def import_plan(uow: UnitOfWork, command: ImportPlanCommand) -> ImportPlanResult:
    """Store the document, or return the existing version with the same content."""
    document = dict(command.document)
    document["plan_id"] = command.plan_id
    document.setdefault("plan_version", content_version(document))

    plan = from_document(document)

    if plan.run_policy_id is not None and await uow.policies.get(plan.run_policy_id) is None:
        raise NotFoundError("run_policy", plan.run_policy_id)
    if await uow.projects.get(plan.project_id) is None:
        raise NotFoundError("project", plan.project_id)

    existing = await uow.plans.get(plan.plan_id, plan.plan_version)
    if existing is not None:
        if existing != plan:
            # Same identity, different content: the version is a content hash, so this
            # can only mean the caller pinned a version by hand and then changed the
            # document under it.
            raise InvalidEntityError(
                f"plan {plan.plan_id}@{plan.plan_version} already exists with different content"
            )
        return ImportPlanResult(plan=existing, created=False)

    await uow.plans.add(plan)
    await uow.commit()
    return ImportPlanResult(plan=plan, created=True)


def content_version(document: dict[str, Any]) -> str:
    """Hash the document without its identity fields.

    Identity is excluded so the same plan content imported under a new id keeps a
    recognisable version, and so the hash cannot depend on the value it produces.
    """
    payload = {
        key: value
        for key, value in to_document(_with_placeholder_identity(document)).items()
        if key not in {"plan_id", "plan_version"}
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:CONTENT_VERSION_LENGTH]


def _with_placeholder_identity(document: dict[str, Any]) -> TestPlan:
    """Parse with stand-in identity so hashing sees a validated, normalized plan.

    Hashing the raw dict would make key order and absent-versus-null change the
    version, and two documents that mean the same thing would import as two plans.
    """
    staged = dict(document)
    staged["plan_id"] = "hash"
    staged["plan_version"] = "hash"
    return from_document(staged)
