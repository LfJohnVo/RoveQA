"""The coherent snapshot a FailureBundle is built from.

"Coherent" is the whole point. A bundle assembled from separate "latest" lookups can
end up pairing this run's screenshot with the previous run's console log, and nobody
reading it would know. So this query answers once, from one run, and every artifact it
returns is checked to belong to that run and to a single evidence set before it leaves.

Deterministic observations and model-derived hypotheses stay in separate fields all
the way out (docs/25). A reader must be able to tell which claims can be reproduced.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.artifacts import ArtifactIndex
from agentic_qa.application.ports.repositories import RunRepository
from agentic_qa.application.ports.results import CriterionResultRepository
from agentic_qa.domain.browser.evidence import EvidenceContaminationError, EvidenceRef
from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult, FailureKind
from agentic_qa.domain.runs.run import Run, Verdict

BUNDLE_SCHEMA_VERSION = "roveqa.failure-bundle.v1"

BUNDLE_VERDICTS = frozenset(
    {Verdict.FAILED, Verdict.BLOCKED, Verdict.INCONCLUSIVE, Verdict.CANCELLED}
)
"""A passing run has no failure to bundle."""


@dataclass(frozen=True)
class FailureContext:
    run: Run
    verdict: Verdict
    evidence_set_id: str
    plan_version: str
    plan_id: str | None
    results: tuple[CriterionResult, ...]
    artifacts: tuple[EvidenceRef, ...] = field(default=())

    @property
    def first_unmet(self) -> CriterionResult | None:
        """The criterion a report leads with. Deterministic failures come first,
        because a reproducible one is worth more than a model's doubt."""
        unmet = [result for result in self.results if result.outcome is CriterionOutcome.NOT_MET]
        deterministic = [result for result in unmet if not result.model_derived]
        candidates = deterministic or unmet
        return candidates[0] if candidates else None


async def load_failure_context(
    runs: RunRepository,
    results: CriterionResultRepository,
    artifacts: ArtifactIndex,
    *,
    run_id: str,
) -> FailureContext:
    """The plan is not re-read: the run recorded which version governed it, and that
    recorded value is what the manifest must carry."""
    run = await runs.get(run_id)
    if run is None:
        raise NotFoundError("run", run_id)
    if run.verdict is None or run.verdict not in BUNDLE_VERDICTS:
        # Refusing beats producing an empty bundle that looks like a finding.
        raise NotFoundError("failure_context", f"{run_id} has no failure to bundle")

    captured = tuple(await artifacts.list_for_run(run_id))
    _require_single_provenance(run_id, captured)

    return FailureContext(
        run=run,
        verdict=run.verdict,
        # Runs that captured nothing still get a stable, run-scoped identity, so the
        # manifest can never be confused with another run's evidence.
        evidence_set_id=captured[0].evidence_set_id if captured else f"evidence:{run_id}",
        plan_version=run.plan_version or "unversioned",
        plan_id=run.plan_id,
        results=tuple(await results.list_for_run(run_id)),
        artifacts=captured,
    )


def _require_single_provenance(run_id: str, artifacts: tuple[EvidenceRef, ...]) -> None:
    """One run, one evidence set. Checked here rather than trusted downstream."""
    for artifact in artifacts:
        if artifact.run_id != run_id:
            raise EvidenceContaminationError(
                f"artifact {artifact.artifact_id} belongs to run {artifact.run_id}, not {run_id}"
            )
    evidence_sets = {artifact.evidence_set_id for artifact in artifacts}
    if len(evidence_sets) > 1:
        raise EvidenceContaminationError(
            f"run {run_id} has artifacts from several evidence sets: {sorted(evidence_sets)}"
        )


def to_manifest(context: FailureContext) -> dict[str, object]:
    """Serialize to `contracts/failure-bundle.schema.json`.

    `bundle_id` is derived from the run rather than random: materializing the same
    failure twice must produce the same bundle identity, or a consumer cannot tell a
    re-download from a different failure.
    """
    leading = context.first_unmet
    hypothesis = _hypothesis(context)
    return {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "bundle_id": f"bundle:{context.run.run_id}",
        "run_id": context.run.run_id,
        "evidence_set_id": context.evidence_set_id,
        "project_id": context.run.project_id,
        "plan_id": context.plan_id,
        "plan_version": context.plan_version,
        "verdict": context.verdict.value,
        "failure_kind": leading.failure_kind.value if leading and leading.failure_kind else None,
        "failed_step_id": leading.step_id if leading else None,
        "captured_at": datetime.now(UTC).isoformat(),
        # Only a check nobody needed a model for goes in the deterministic field.
        "deterministic_observation": (
            leading.observation if leading and not leading.model_derived else None
        ),
        "root_cause_hypothesis": hypothesis,
        "artifacts": [
            {
                "artifact_id": artifact.artifact_id,
                "kind": artifact.kind,
                "relative_path": artifact.relative_path,
                "sha256": artifact.sha256,
                "size_bytes": artifact.size_bytes,
                "run_id": artifact.run_id,
                "evidence_set_id": artifact.evidence_set_id,
            }
            for artifact in context.artifacts
        ],
    }


def _hypothesis(context: FailureContext) -> dict[str, object] | None:
    """Whatever a model concluded, labelled as a model's conclusion and nothing else."""
    guesses = [
        result
        for result in context.results
        if result.model_derived and result.outcome is not CriterionOutcome.MET
    ]
    if not guesses:
        return None
    return {
        "text": "; ".join(f"{result.criterion_id}: {result.observation}" for result in guesses),
        "model_derived": True,
        "confidence": None,
    }


def failure_kinds(context: FailureContext) -> set[FailureKind]:
    return {result.failure_kind for result in context.results if result.failure_kind is not None}
