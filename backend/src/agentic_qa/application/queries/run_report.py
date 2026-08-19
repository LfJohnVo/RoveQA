"""Build a run report from durable results.

Two properties this module owes the reader of a report:

**It never depends on a model transcript.** Everything here comes from rows: the run,
the plan version it was judged by, and the criterion results. A report that had to
replay an LLM conversation to explain itself could not be regenerated a month later,
and could not be trusted when it was.

**It never mixes what was observed with what was guessed.** Deterministic findings and
model-derived judgements are rendered in separate sections, each labelled. A reader
must be able to tell, without knowing how this system works, which claims someone can
reproduce.
"""

from dataclasses import dataclass
from typing import Any

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.plans import TestPlanRepository
from agentic_qa.application.ports.repositories import RunRepository
from agentic_qa.application.ports.results import CriterionResultRepository
from agentic_qa.domain.qa.test_plan import TestPlan
from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult
from agentic_qa.domain.runs.run import Run

REPORT_VERSION = "roveqa.run-report.v1"


@dataclass(frozen=True)
class RunReport:
    run: Run
    plan: TestPlan | None
    results: tuple[CriterionResult, ...]

    @property
    def deterministic(self) -> tuple[CriterionResult, ...]:
        return tuple(result for result in self.results if not result.model_derived)

    @property
    def model_derived(self) -> tuple[CriterionResult, ...]:
        return tuple(result for result in self.results if result.model_derived)

    @property
    def defects(self) -> tuple[CriterionResult, ...]:
        """Only reproducible product failures. This is what a bug report may cite."""
        return tuple(result for result in self.results if result.is_product_defect)


async def build_run_report(
    runs: RunRepository,
    plans: TestPlanRepository,
    results: CriterionResultRepository,
    *,
    run_id: str,
) -> RunReport:
    run = await runs.get(run_id)
    if run is None:
        raise NotFoundError("run", run_id)

    # The plan version recorded on the run, never the latest: the report has to explain
    # the run under the rules it actually ran under.
    plan = (
        await plans.get(run.plan_id, run.plan_version)
        if run.plan_id is not None and run.plan_version is not None
        else None
    )
    return RunReport(run=run, plan=plan, results=tuple(await results.list_for_run(run_id)))


def to_document(report: RunReport) -> dict[str, Any]:
    """Machine-readable report. Every criterion says who decided it."""
    return {
        "schema_version": REPORT_VERSION,
        "run_id": report.run.run_id,
        "project_id": report.run.project_id,
        "status": report.run.status.value,
        "verdict": report.run.verdict.value if report.run.verdict else None,
        "plan": (
            {
                "plan_id": report.plan.plan_id,
                "plan_version": report.plan.plan_version,
                "name": report.plan.name,
                "source_story_id": report.plan.source_story_id,
            }
            if report.plan
            else None
        ),
        "criteria": [
            {
                "criterion_id": result.criterion_id,
                "step_id": result.step_id,
                "outcome": result.outcome.value,
                "failure_kind": result.failure_kind.value if result.failure_kind else None,
                # Two distinct keys rather than one "message": a consumer that wants
                # only reproducible claims can filter on the key, not on a convention.
                "deterministic_observation": None if result.model_derived else result.observation,
                "root_cause_hypothesis": result.observation if result.model_derived else None,
                "model_derived": result.model_derived,
                "evidence_refs": list(result.evidence_refs),
            }
            for result in report.results
        ],
    }


def render_markdown(report: RunReport) -> str:
    """Human-readable report, with the same separation the document makes."""
    verdict = report.run.verdict.value if report.run.verdict else "pending"
    lines = [
        f"# Run {report.run.run_id}",
        "",
        f"- Status: `{report.run.status.value}`",
        f"- Verdict: **{verdict}**",
    ]
    if report.plan:
        lines.append(f"- Plan: `{report.plan.plan_id}` version `{report.plan.plan_version}`")
        if report.plan.source_story_id:
            lines.append(f"- Story: `{report.plan.source_story_id}`")
    lines.append("")

    lines.append("## Observed")
    lines.append("")
    if report.deterministic:
        lines.append("Reproducible checks. Each one can be repeated without a model.")
        lines.append("")
        for result in report.deterministic:
            lines.append(f"- {_status(result)} **{result.criterion_id}** — {result.observation}")
    else:
        lines.append("_No deterministic check ran for this run._")
    lines.append("")

    if report.model_derived:
        lines.append("## Model hypotheses")
        lines.append("")
        lines.append(
            "Generated by a model and **not** verified. These are leads to investigate, "
            "not findings."
        )
        lines.append("")
        for result in report.model_derived:
            lines.append(f"- {_status(result)} **{result.criterion_id}** — {result.observation}")
        lines.append("")

    lines.append("## Defects")
    lines.append("")
    if report.defects:
        for result in report.defects:
            lines.append(f"- **{result.criterion_id}**: {result.observation}")
    else:
        lines.append("_No reproducible product defect was found._")
    lines.append("")
    return "\n".join(lines)


def _status(result: CriterionResult) -> str:
    marks = {
        CriterionOutcome.MET: "PASS",
        CriterionOutcome.NOT_MET: "FAIL",
        CriterionOutcome.UNVERIFIED: "UNVERIFIED",
    }
    mark = marks[result.outcome]
    if result.failure_kind is not None:
        return f"[{mark}/{result.failure_kind.value}]"
    return f"[{mark}]"
