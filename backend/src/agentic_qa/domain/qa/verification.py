"""Criterion results and how a run's verdict is derived from them.

Two rules shape this module, both from docs/06 and docs/13:

**A deterministic observation and a model's opinion are different things.** A
`CriterionResult` records what was observed and, separately, whether a model was the one
who judged it. A report can then say "the confirmation page did not contain an order
number" without dressing up "the model thought this looked wrong" as the same claim.

**Not every failure is the product's fault.** A run that ran out of actions, hit a
policy refusal or was handed an ambiguous plan has *not* found a defect. Collapsing
those into "failed" is how a QA system loses its credibility: the first time it blames
the product for a bad plan, every later report gets read with suspicion.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.runs.run import Verdict
from agentic_qa.domain.validation import require_identifier, require_text


class CriterionOutcome(StrEnum):
    MET = "met"
    NOT_MET = "not_met"
    UNVERIFIED = "unverified"
    """Nobody could tell. Never counted as met, never reported as a defect."""


class FailureKind(StrEnum):
    """Why a criterion is not met — the classification docs/00 asks a report to make."""

    PRODUCT = "product"
    """The system under test did not do what the story promised. The only kind that
    means "there is a bug"."""

    PLAN = "plan"
    """The plan is ambiguous, contradictory or unverifiable as written."""

    ENVIRONMENT = "environment"
    """The target was unreachable, broken or not in the expected state."""

    POLICY = "policy"
    """The RunPolicy refused an action the criterion needed."""

    AGENT_BUDGET = "agent_budget"
    """The run hit its action/duration/model budget before finishing."""

    MODEL = "model"
    """Inference was unavailable or produced nothing usable."""

    UNKNOWN = "unknown"


PRODUCT_DEFECT_KINDS = frozenset({FailureKind.PRODUCT})
"""Only these justify a `failed` verdict. Everything else is inconclusive or blocked."""

BLOCKING_KINDS = frozenset(
    {FailureKind.ENVIRONMENT, FailureKind.POLICY, FailureKind.AGENT_BUDGET, FailureKind.MODEL}
)
"""The run could not do its job. `blocked` says that honestly."""


@dataclass(frozen=True)
class CriterionResult:
    criterion_id: str
    outcome: CriterionOutcome
    observation: str
    """What was deterministically observed. Never a model's paraphrase of it."""

    failure_kind: FailureKind | None = None
    model_derived: bool = False
    """True when a model produced this judgement rather than a deterministic check."""

    evidence_refs: tuple[str, ...] = field(default=())
    step_id: str | None = None

    model_invocation_id: str | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    """Which model and prompt produced a model-derived judgement (docs/08).

    Absent on a deterministic result, and that absence is itself information: a
    result with no invocation is one nobody needed a model for.
    """

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "criterion_id", require_identifier(self.criterion_id, field="criterion_id")
        )
        object.__setattr__(
            self,
            "observation",
            require_text(self.observation, field="observation", max_length=4000),
        )
        if self.outcome is CriterionOutcome.MET and self.failure_kind is not None:
            raise InvalidEntityError("a met criterion has no failure kind")
        if not self.model_derived and self.model_invocation_id is not None:
            raise InvalidEntityError("a deterministic result cannot name a model invocation")
        if self.outcome is CriterionOutcome.NOT_MET and self.failure_kind is None:
            # Without a kind, a report cannot tell a product defect from a bad plan, and
            # the safe reading (blame the product) is the damaging one.
            raise InvalidEntityError("a criterion that is not met must say what kind of failure")

    @property
    def is_product_defect(self) -> bool:
        return (
            self.outcome is CriterionOutcome.NOT_MET and self.failure_kind in PRODUCT_DEFECT_KINDS
        )


def derive_verdict(results: Sequence[CriterionResult], *, expected: Sequence[str]) -> Verdict:
    """Turn criterion results into the run's QA verdict.

    Ordering matters and is deliberate:

    1. A confirmed product defect is a `failed` run — that is the finding worth having,
       and a blocked-looking symptom elsewhere must not hide it.
    2. Otherwise, anything that stopped the run from checking (environment, policy,
       budget, model) makes it `blocked`.
    3. A criterion nobody could verify, or one never reached at all, is `inconclusive`.
    4. Only when every expected criterion was actually met does the run pass.

    A missing result is treated as unverified rather than ignored: silently passing a
    run because a criterion was never evaluated is the worst failure mode available.
    """
    by_criterion = {result.criterion_id: result for result in results}
    if not expected:
        raise InvalidEntityError("a verdict needs at least one expected criterion")

    if any(result.is_product_defect for result in results):
        return Verdict.FAILED

    if any(
        result.outcome is CriterionOutcome.NOT_MET and result.failure_kind in BLOCKING_KINDS
        for result in results
    ):
        return Verdict.BLOCKED

    missing = [criterion_id for criterion_id in expected if criterion_id not in by_criterion]
    if missing or any(
        result.outcome is CriterionOutcome.UNVERIFIED for result in by_criterion.values()
    ):
        return Verdict.INCONCLUSIVE

    # Whatever is left is either met or a non-product, non-blocking failure (a plan
    # problem), and a plan we cannot trust cannot certify a pass.
    if all(result.outcome is CriterionOutcome.MET for result in by_criterion.values()):
        return Verdict.PASSED
    return Verdict.INCONCLUSIVE
