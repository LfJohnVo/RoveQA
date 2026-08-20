"""Turn a finished run into knowledge candidates.

Only *verified* outcomes become candidates (ADR 0008). A run that ended inconclusive
learned that it could not tell — which is worth recording as a failure signature, and
is never worth recording as a fact about the application.

The distinction that governs every branch below: a deterministic result produces an
`observed` candidate that can eventually be trusted; a model-derived result produces a
`model_derived` one that never can. Collapsing them would let a model's guess become,
after enough repetitions, something a later run treats as established.

Redaction runs before anything is built, and an item that cannot be safely redacted is
dropped rather than stored — a run must not fail because something it saw was
unlearnable.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit
from uuid import uuid4

from agentic_qa.domain.knowledge.experience import (
    CandidateKind,
    KnowledgeExperienceCandidate,
    Provenance,
    Quality,
    Validity,
)
from agentic_qa.domain.knowledge.redaction import UnsafeKnowledgeError, redact_payload
from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult
from agentic_qa.domain.runs.run import Run, Verdict

logger = logging.getLogger(__name__)

DEFAULT_ENVIRONMENT = "default"
"""Runs without an explicit environment still need a scope to be filtered by; an
empty one would make retrieval compare against nothing."""

LEARNABLE_VERDICTS = frozenset({Verdict.PASSED, Verdict.FAILED})
"""A run that could not conclude has nothing verified to teach. `blocked` and
`inconclusive` mean the run failed to answer, not that the answer was no."""


@dataclass(frozen=True)
class ConsolidationInput:
    run: Run
    results: Sequence[CriterionResult]
    observed_url: str | None
    evidence_set_id: str | None
    page_fingerprint: str | None = None
    app_version: str | None = None
    origin: str | None = None
    """Left unset, it is derived from the URL the run actually ended on: knowledge
    observed against one origin says nothing about another."""

    at: datetime | None = None


@dataclass(frozen=True)
class ConsolidationOutcome:
    candidates: tuple[KnowledgeExperienceCandidate, ...]
    skipped: tuple[str, ...]
    """Why each dropped item was dropped. Silence here would hide a redaction that
    is quietly discarding everything the system tries to learn."""


def consolidate(request: ConsolidationInput, *, now: datetime) -> ConsolidationOutcome:
    run = request.run
    if run.verdict not in LEARNABLE_VERDICTS:
        return ConsolidationOutcome(
            candidates=(),
            skipped=(f"verdict {run.verdict} carries nothing verified to learn",),
        )

    environment_id = run.environment_id or DEFAULT_ENVIRONMENT
    validity = Validity(
        valid_from=now,
        app_version=request.app_version,
        page_fingerprint=request.page_fingerprint,
        origin=request.origin or _origin_of(request.observed_url),
        # The policy is part of the context: knowledge captured under a read-only run
        # says nothing about what happens when writes are allowed.
        policy_id=run.run_policy_id,
    )

    built: list[KnowledgeExperienceCandidate] = []
    skipped: list[str] = []

    for result in request.results:
        candidate = _from_result(
            request, result, environment_id=environment_id, validity=validity, now=now
        )
        if isinstance(candidate, str):
            skipped.append(candidate)
        elif candidate is not None:
            built.append(candidate)

    route = _route_candidate(request, environment_id=environment_id, validity=validity, now=now)
    if isinstance(route, str):
        skipped.append(route)
    elif route is not None:
        built.append(route)

    return ConsolidationOutcome(candidates=tuple(built), skipped=tuple(skipped))


def _origin_of(url: str | None) -> str | None:
    """Scheme and host, without the path. The origin is the part that decides whether
    two observations are about the same application at all."""
    if not url:
        return None
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return None
    return f"{parts.scheme}://{parts.netloc}"


def _from_result(
    request: ConsolidationInput,
    result: CriterionResult,
    *,
    environment_id: str,
    validity: Validity,
    now: datetime,
) -> KnowledgeExperienceCandidate | str | None:
    """One criterion's verified outcome, or a reason it taught nothing."""
    if result.outcome is CriterionOutcome.UNVERIFIED:
        # Nobody could tell. Recording it as knowledge would record the absence of
        # knowledge as knowledge.
        return None

    met = result.outcome is CriterionOutcome.MET
    kind = CandidateKind.ACCEPTANCE_FACT if met else CandidateKind.FAILURE_SIGNATURE
    payload = {
        "criterion_id": result.criterion_id,
        "step_id": result.step_id,
        "summary": result.observation,
        "failure_kind": result.failure_kind.value if result.failure_kind else None,
    }

    try:
        redacted = redact_payload(payload)
    except UnsafeKnowledgeError as error:
        return f"{result.criterion_id}: {error.reason}"

    return KnowledgeExperienceCandidate(
        candidate_id=str(uuid4()),
        project_id=request.run.project_id,
        environment_id=environment_id,
        kind=kind,
        # The labels come straight from how the result was reached, and are the
        # reason a model's opinion can never become trusted knowledge.
        observed=not result.model_derived,
        model_derived=result.model_derived,
        created_at=now,
        provenance=Provenance(
            source_run_id=request.run.run_id,
            evidence_set_id=request.evidence_set_id,
            test_plan_version=request.run.plan_version,
            model_invocation_id=result.model_invocation_id,
        ),
        validity=validity,
        payload=redacted.payload,
        # One run is one piece of support. Promotion happens when a second run agrees.
        quality=Quality(support_count=1, success_count=1 if met else 0, last_verified_at=now),
    )


def _route_candidate(
    request: ConsolidationInput, *, environment_id: str, validity: Validity, now: datetime
) -> KnowledgeExperienceCandidate | str | None:
    """Where the run ended up. Observed by definition — a URL is not an opinion."""
    if not request.observed_url or request.observed_url == "about:blank":
        return None

    try:
        redacted = redact_payload(
            {"url": request.observed_url, "summary": f"reachable: {request.observed_url}"}
        )
    except UnsafeKnowledgeError as error:
        return f"route: {error.reason}"

    return KnowledgeExperienceCandidate(
        candidate_id=str(uuid4()),
        project_id=request.run.project_id,
        environment_id=environment_id,
        kind=CandidateKind.ROUTE,
        observed=True,
        model_derived=False,
        created_at=now,
        provenance=Provenance(
            source_run_id=request.run.run_id,
            evidence_set_id=request.evidence_set_id,
            test_plan_version=request.run.plan_version,
        ),
        validity=validity,
        payload=redacted.payload,
        quality=Quality(support_count=1, success_count=1, last_verified_at=now),
    )
