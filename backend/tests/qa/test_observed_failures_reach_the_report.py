"""What the browser saw goes into the report, and stays out of the verdict.

Console errors and failed requests were collected by the Playwright adapter, carried as
far as `EpisodeResult.page_problems`, and dropped — that field was the only one of the
result nothing read. ADR 0015 said the run report would gain them; it had not.

Two properties are worth more than the plumbing, and both are asserted here:

- an observation reaches a reader **in its own section**, never folded into `criteria`;
- an observation **cannot change a verdict**. Only a deterministic check against a
  criterion may accuse the application, and a broken image is not an accusation.
"""

from typing import Any

import pytest

from agentic_qa.application.ports.browser import PageProblems
from agentic_qa.application.ports.episodes import EpisodeResult
from agentic_qa.application.queries.run_report import build_run_report, render_markdown, to_document
from agentic_qa.domain.qa.observations import (
    MAX_DETAIL_CHARS,
    ObservedFailure,
    ObservedFailureKind,
)
from agentic_qa.domain.qa.verification import (
    CriterionOutcome,
    CriterionResult,
    FailureKind,
    derive_verdict,
)
from agentic_qa.domain.runs.run import Run, Verdict
from tests.fakes.repositories import InMemoryStore
from tests.fakes.unit_of_work import InMemoryUnitOfWork

RUN_ID = "run-observed"
PROJECT_ID = "proj-observed"


async def report_for(
    failures: list[ObservedFailure], results: list[CriterionResult] | None = None
) -> dict[str, Any]:
    uow = InMemoryUnitOfWork(InMemoryStore())
    async with uow:
        await uow.runs.add(Run(run_id=RUN_ID, project_id=PROJECT_ID))
        await uow.observed_failures.record(RUN_ID, failures)
        if results:
            await uow.criterion_results.record(RUN_ID, results)
        await uow.commit()

    async with uow:
        report = await build_run_report(
            uow.runs, uow.plans, uow.criterion_results, uow.observed_failures, run_id=RUN_ID
        )
    return to_document(report)


class TestTheyReachAReader:
    async def test_the_document_carries_them_in_their_own_section(self) -> None:
        document = await report_for(
            [
                ObservedFailure(
                    kind=ObservedFailureKind.CONSOLE_ERROR, detail="TypeError: x is not a function"
                ),
                ObservedFailure(
                    kind=ObservedFailureKind.FAILED_REQUEST, detail="https://cdn.test/logo.png"
                ),
            ]
        )

        observed = document["observed_failures"]
        assert observed == [
            {
                "kind": "console_error",
                "detail": "TypeError: x is not a function",
                "episode_index": 0,
            },
            {"kind": "failed_request", "detail": "https://cdn.test/logo.png", "episode_index": 0},
        ]
        # Not folded into the criteria array: these answer nothing the plan asked.
        assert document["criteria"] == []

    async def test_a_run_with_no_criteria_still_reports_what_it_saw(self) -> None:
        # The case that matters most. A landing page has no story, so `_record_results`
        # returns early and every existing findings surface stays empty — which used to
        # mean a sweep of a broken site produced a completely blank report.
        document = await report_for(
            [ObservedFailure(kind=ObservedFailureKind.CONSOLE_ERROR, detail="boom")]
        )

        assert document["criteria"] == []
        assert len(document["observed_failures"]) == 1

    async def test_the_markdown_says_they_are_not_verdicts(self) -> None:
        uow = InMemoryUnitOfWork(InMemoryStore())
        async with uow:
            await uow.runs.add(Run(run_id=RUN_ID, project_id=PROJECT_ID))
            await uow.observed_failures.record(
                RUN_ID,
                [ObservedFailure(kind=ObservedFailureKind.CONSOLE_ERROR, detail="boom")],
            )
            await uow.commit()
        async with uow:
            report = await build_run_report(
                uow.runs, uow.plans, uow.criterion_results, uow.observed_failures, run_id=RUN_ID
            )

        rendered = render_markdown(report)

        assert "What the browser saw" in rendered
        assert "none of them is a verdict" in rendered
        # And nowhere near the section a bug report is allowed to cite.
        assert rendered.index("What the browser saw") < rendered.index("## Defects")


class TestTheyCannotAccuseTheProduct:
    async def test_a_page_full_of_errors_does_not_make_a_run_fail(self) -> None:
        # A verdict comes from criterion results and from nothing else. If an observation
        # could reach it, every site with a noisy console would be reported broken.
        met = CriterionResult(
            criterion_id="ac-loaded",
            outcome=CriterionOutcome.MET,
            observation="the page says RoveQA",
        )

        document = await report_for(
            [
                ObservedFailure(kind=ObservedFailureKind.CONSOLE_ERROR, detail=f"boom {index}")
                for index in range(20)
            ],
            [met],
        )

        assert len(document["observed_failures"]) == 20
        assert derive_verdict((met,), expected=["ac-loaded"]) is Verdict.PASSED

    def test_only_a_criterion_carries_a_failure_kind(self) -> None:
        # `ObservedFailure` has no `failure_kind` field and no outcome. The type makes
        # the rule rather than a convention holding it: there is nothing to set.
        assert not hasattr(
            ObservedFailure(kind=ObservedFailureKind.CONSOLE_ERROR, detail="boom"), "failure_kind"
        )
        assert FailureKind.PRODUCT.value == "product"


class TestTheDetailIsBounded:
    def test_a_giant_stack_trace_is_truncated_rather_than_refused(self) -> None:
        # The opposite of the domain's usual rule, and deliberately: an over-long console
        # message is the finding, not a mistake. Raising would lose it.
        failure = ObservedFailure(kind=ObservedFailureKind.CONSOLE_ERROR, detail="x" * 50_000)

        assert len(failure.detail) == MAX_DETAIL_CHARS + 1  # the ellipsis says it was cut
        assert failure.detail.endswith("…")

    def test_a_blank_detail_is_refused(self) -> None:
        with pytest.raises(Exception, match="blank"):
            ObservedFailure(kind=ObservedFailureKind.CONSOLE_ERROR, detail="   ")


class TestTheEpisodeIsTheGrain:
    def test_page_problems_are_attributed_to_an_episode_not_a_page(self) -> None:
        # Said out loud because the plan asks for per-page findings and this is not that.
        # The adapter accumulates across a whole episode and never clears between
        # navigations, so naming a page here would be an attribution nobody measured.
        result = EpisodeResult(
            more_work=False,
            page_problems=PageProblems(console_errors=("boom",), failed_requests=()),
        )

        assert result.page_problems.console_errors == ("boom",)
        assert not hasattr(result.page_problems, "url")
