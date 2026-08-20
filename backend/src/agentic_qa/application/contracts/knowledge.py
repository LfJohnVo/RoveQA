"""The portable knowledge document (`contracts/knowledge-experience.schema.json`).

Knowledge leaves this system by more than one path — an admin API, a CLI export, a
graph projection rebuilt somewhere else — and every one of them must agree on the
same shape. So the mapping lives once, above every adapter and below every delivery
mechanism, exactly as the TestPlan document does.

The labels that matter travel with the document. A consumer that receives a candidate
without `observed`/`model_derived` and without `quality` cannot tell a verified fact
from a model's guess, and would have no basis for refusing to act on the guess.
"""

from datetime import datetime
from typing import Any

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.knowledge.experience import (
    SCHEMA_VERSION,
    CandidateKind,
    CandidateStatus,
    KnowledgeExperienceCandidate,
    Provenance,
    Quality,
    Validity,
)


def to_document(candidate: KnowledgeExperienceCandidate) -> dict[str, Any]:
    """Serialize to the public contract.

    Optionals inside `provenance` and `validity` are emitted as explicit nulls because
    the schema requires the keys: "we know this was not recorded" and "we forgot to
    send it" must not look alike to a consumer deciding whether knowledge applies.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": candidate.candidate_id,
        "project_id": candidate.project_id,
        "environment_id": candidate.environment_id,
        "kind": candidate.kind.value,
        "observed": candidate.observed,
        "model_derived": candidate.model_derived,
        "created_at": candidate.created_at.isoformat(),
        "provenance": {
            "source_run_id": candidate.provenance.source_run_id,
            "source_episode_id": candidate.provenance.source_episode_id,
            "evidence_set_id": candidate.provenance.evidence_set_id,
            "test_plan_version": candidate.provenance.test_plan_version,
            "model_invocation_id": candidate.provenance.model_invocation_id,
        },
        "validity": {
            "valid_from": candidate.validity.valid_from.isoformat(),
            "valid_to": (
                candidate.validity.valid_to.isoformat() if candidate.validity.valid_to else None
            ),
            "app_version": candidate.validity.app_version,
            "page_fingerprint": candidate.validity.page_fingerprint,
            "role": candidate.validity.role,
            "origin": candidate.validity.origin,
            "policy_id": candidate.validity.policy_id,
        },
        "payload": dict(candidate.payload),
        "status": candidate.status.value,
        "quality": {
            "support_count": candidate.quality.support_count,
            "success_count": candidate.quality.success_count,
            "failure_count": candidate.quality.failure_count,
            "contradiction_count": candidate.quality.contradiction_count,
            # Derived on the way out, never stored as an independent field: a number a
            # consumer ranks by must not be able to disagree with the counts beside it.
            "reliability": candidate.quality.reliability,
            "last_verified_at": (
                candidate.quality.last_verified_at.isoformat()
                if candidate.quality.last_verified_at
                else None
            ),
        },
    }


def from_document(document: dict[str, Any]) -> KnowledgeExperienceCandidate:
    """Parse a document from outside this system.

    Everything is re-validated by the entity — a document is an assertion by whoever
    wrote it, not a fact. In particular a document claiming a model-derived candidate
    is `trusted` is refused rather than imported, which is the one thing an attacker
    with write access to an export would most want to say.
    """
    version = document.get("schema_version")
    if version != SCHEMA_VERSION:
        raise InvalidEntityError(f"unsupported knowledge schema_version: {version}")

    provenance = document.get("provenance") or {}
    validity = document.get("validity") or {}
    quality = document.get("quality") or {}

    return KnowledgeExperienceCandidate(
        candidate_id=str(document.get("candidate_id", "")),
        project_id=str(document.get("project_id", "")),
        environment_id=str(document.get("environment_id", "")),
        kind=_enum(CandidateKind, document.get("kind"), field="kind"),
        observed=bool(document.get("observed")),
        model_derived=bool(document.get("model_derived")),
        created_at=_timestamp(document.get("created_at"), field="created_at"),
        provenance=Provenance(
            source_run_id=str(provenance.get("source_run_id", "")),
            source_episode_id=provenance.get("source_episode_id"),
            evidence_set_id=provenance.get("evidence_set_id"),
            test_plan_version=provenance.get("test_plan_version"),
            model_invocation_id=provenance.get("model_invocation_id"),
        ),
        validity=Validity(
            valid_from=_timestamp(validity.get("valid_from"), field="valid_from"),
            valid_to=_optional_timestamp(validity.get("valid_to"), field="valid_to"),
            app_version=validity.get("app_version"),
            page_fingerprint=validity.get("page_fingerprint"),
            role=validity.get("role"),
            origin=validity.get("origin"),
            policy_id=validity.get("policy_id"),
        ),
        payload=dict(document.get("payload") or {}),
        status=_enum(CandidateStatus, document.get("status"), field="status"),
        quality=Quality(
            support_count=int(quality.get("support_count", 0)),
            success_count=int(quality.get("success_count", 0)),
            failure_count=int(quality.get("failure_count", 0)),
            contradiction_count=int(quality.get("contradiction_count", 0)),
            last_verified_at=_optional_timestamp(
                quality.get("last_verified_at"), field="last_verified_at"
            ),
        ),
    )


def _enum[EnumT: (CandidateKind, CandidateStatus)](
    enum: type[EnumT], value: object, *, field: str
) -> EnumT:
    if not isinstance(value, str):
        raise InvalidEntityError(f"{field} must be a string, got {type(value).__name__}")
    try:
        return enum(value)
    except ValueError as error:
        raise InvalidEntityError(f"unknown {field}: {value}") from error


def _timestamp(value: object, *, field: str) -> datetime:
    parsed = _optional_timestamp(value, field=field)
    if parsed is None:
        raise InvalidEntityError(f"{field} is required")
    return parsed


def _optional_timestamp(value: object, *, field: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidEntityError(f"{field} must be an ISO-8601 string")
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise InvalidEntityError(f"{field} is not a valid timestamp: {value}") from error
