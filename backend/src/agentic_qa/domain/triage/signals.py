"""The structural facts a failure carries before anyone interprets it.

Triage happens *before* a model sees anything (`plans/phase-11-airllm-deep-analysis.md`).
That ordering is the whole point: twenty runs that failed because the login page was
down are one problem, and discovering that by sending twenty transcripts to a large
model is both slow and a way to receive twenty differently-worded answers to the same
question.

So a failure is first reduced to signals that can be compared exactly — the kind, the
criterion, the route, the fingerprint, a normalised observation. Everything here is
derived from what was deterministically observed. A model's hypothesis is deliberately
not a signal: clustering on a guess would produce groups nobody can justify afterwards.
"""

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult, FailureKind

SETUP_KINDS = frozenset({FailureKind.ENVIRONMENT, FailureKind.POLICY, FailureKind.MODEL})
"""Kinds that stop a run from doing its job rather than describing the product.

When one of these is present, whatever failed afterwards may have failed *because of
it* — which is what cascade detection is for. `AGENT_BUDGET` is excluded on purpose:
running out of actions is a consequence of everything before it, not a cause of it.
"""

_HTTP_STATUS = re.compile(r"\b(?:HTTP\s*)?([45]\d{2})\b")
_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE
)
_LONG_NUMBER = re.compile(r"\b\d{4,}\b")
_QUOTED = re.compile(r"[\"'`][^\"'`]{1,80}[\"'`]")
_WHITESPACE = re.compile(r"\s+")

MAX_NORMALIZED_CHARS = 300


@dataclass(frozen=True)
class FailureSignal:
    """One failed criterion, reduced to what can be compared exactly.

    Carries `run_id` so a cluster can name its members: the point of grouping is to say
    *which* runs share a problem, and a cluster that cannot list them is a summary
    nobody can check.
    """

    run_id: str
    criterion_id: str
    failure_kind: FailureKind
    normalized_observation: str
    """The observation with the parts that differ per run removed. Two runs that hit
    the same wall usually describe it with different ids and timings."""

    http_status: str | None = None
    route: str | None = None
    """Path only, without the query string: the same broken page reached with different
    parameters is the same broken page."""

    origin: str | None = None
    page_fingerprint: str | None = None
    step_id: str | None = None
    evidence_refs: tuple[str, ...] = field(default=())

    @property
    def is_setup_failure(self) -> bool:
        """Whether this could be the cause of other failures in the same run."""
        return self.failure_kind in SETUP_KINDS

    @property
    def grouping_key(self) -> tuple[str, ...]:
        """What makes two failures the same problem.

        Deliberately exact rather than fuzzy. A similarity threshold would put the
        boundary of a cluster somewhere nobody can point at, and the first time it
        merged two unrelated failures the whole grouping would stop being trusted.
        Anything that needs judgement is left for the model — on the representative,
        not on the grouping.
        """
        return (
            self.failure_kind.value,
            self.criterion_id,
            self.http_status or "",
            self.route or "",
            self.page_fingerprint or "",
            self.normalized_observation,
        )


def signal_from(
    result: CriterionResult,
    *,
    run_id: str,
    observed_url: str | None = None,
    page_fingerprint: str | None = None,
) -> FailureSignal | None:
    """Reduce one criterion result to a signal, or decline.

    Returns `None` for anything that is not a deterministic failure. A met criterion
    has no problem to group, and a model-derived judgement is an opinion — clustering
    on it would build groups whose membership nobody could defend.
    """
    if result.outcome is not CriterionOutcome.NOT_MET or result.model_derived:
        return None

    route, origin = _split_url(observed_url)
    return FailureSignal(
        run_id=run_id,
        criterion_id=result.criterion_id,
        failure_kind=result.failure_kind or FailureKind.UNKNOWN,
        normalized_observation=normalize(result.observation),
        http_status=_status_in(result.observation),
        route=route,
        origin=origin,
        page_fingerprint=page_fingerprint,
        step_id=result.step_id,
        evidence_refs=result.evidence_refs,
    )


def normalize(observation: str) -> str:
    """Strip the parts of an observation that differ between two runs of one problem.

    Ids, timestamps and quoted values change every run; the sentence around them does
    not. Without this, "order 8821 was not confirmed" and "order 8822 was not
    confirmed" are two clusters of one — which is exactly the duplication triage exists
    to remove.
    """
    text = observation.lower()
    text = _UUID.sub("<id>", text)
    text = _QUOTED.sub("<value>", text)
    text = _LONG_NUMBER.sub("<n>", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text[:MAX_NORMALIZED_CHARS]


def _status_in(observation: str) -> str | None:
    match = _HTTP_STATUS.search(observation)
    return match.group(1) if match else None


def _split_url(url: str | None) -> tuple[str | None, str | None]:
    if not url:
        return None, None
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return None, None
    return parts.path or "/", f"{parts.scheme}://{parts.netloc}"
