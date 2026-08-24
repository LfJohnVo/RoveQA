"""The checks every run runs on every page, whatever else it is doing.

A landing page, a blog, a documentation site: the QA question is not "did the actor
achieve the goal", it is *do all the reachable pages load*. Nothing could express that,
so a sweep of nine pages reported `inconclusive` — "nobody knows" as the answer from a
run that knew nine things (ADR 0017).

This is a layer, not a mode. A story-driven run gets these too, and so learns that it
walked through a 500 on its way to the checkout page. Adding a third run shape beside
"story" and "traversal" would have meant three verdict rules and a combination nobody
tested; a layer composes because there is nothing to compose.

Zero inference by construction: every answer is read off a `PageState` the browser
already produced.
"""

from agentic_qa.domain.exploration.state import PageState
from agentic_qa.domain.qa.verification import (
    CriterionOutcome,
    CriterionResult,
    CriterionSource,
    FailureKind,
)

CRITERION_PREFIX = "page:"
"""Namespaced so a sweep criterion can never collide with one a story named.

The prefix is for readability; `CriterionSource` is what a consumer should branch on.
"""

SERVER_ERROR = 500
CLIENT_ERROR = 400


def is_checkable(state: PageState) -> bool:
    """Whether this page is part of the application at all.

    A browser opens on `about:blank`, and a planned run observes it once before it
    navigates anywhere. Checking it produced a criterion with no HTTP status, therefore
    `unverified`, therefore an `inconclusive` verdict — on a run whose story had passed.
    Caught by the story e2e the first time these checks ran beside a plan.

    The rule is the honest one: a sweep reports on pages of the site under test, and a
    page the run never navigated to is not one of them. `about:blank`, `data:` and
    `chrome-error://` all fail this for the same reason.
    """
    return state.url.startswith(("http://", "https://"))


def criterion_id_for(state: PageState) -> str:
    """One criterion per *route*, not per url.

    The state map already normalises identifier-shaped segments, so a hundred pages
    under `/orders/{id}` are one route and produce one row. Without that a catalogue
    would fill a report with a hundred identical findings and bury the one that matters.
    """
    return f"{CRITERION_PREFIX}{state.route}"


def check_page(state: PageState, *, reached_from_published_link: bool) -> CriterionResult:
    """Whether this page answered, and what else is worth saying about it.

    `reached_from_published_link` decides whether a 4xx may accuse anyone, and the caller
    is the only one who knows. A sweep takes affordances the site itself offered, so a 404
    there is the site publishing a link it cannot serve. A planned run can reach a url a
    model invented, and a 404 on *that* says nothing about the application (ADR 0015).
    """
    status = state.http_status
    notes = _notes(state)

    if status is None:
        # A client-side route change makes no navigation response. Calling it healthy
        # would be a claim nobody measured; not knowing is not a finding either.
        return CriterionResult(
            criterion_id=criterion_id_for(state),
            outcome=CriterionOutcome.UNVERIFIED,
            observation=_describe("no HTTP status was observed for this page", notes),
            source=CriterionSource.SWEEP,
        )

    if status >= SERVER_ERROR:
        return CriterionResult(
            criterion_id=criterion_id_for(state),
            outcome=CriterionOutcome.NOT_MET,
            observation=_describe(f"the page answered {status}", notes),
            # The application answered, and answered wrongly. One of the very few paths
            # that may accuse the product (ADR 0015).
            failure_kind=FailureKind.PRODUCT,
            source=CriterionSource.SWEEP,
        )

    if status >= CLIENT_ERROR:
        if reached_from_published_link:
            return CriterionResult(
                criterion_id=criterion_id_for(state),
                outcome=CriterionOutcome.NOT_MET,
                observation=_describe(
                    f"the page answered {status}, reached from a link the site offers", notes
                ),
                failure_kind=FailureKind.PRODUCT,
                source=CriterionSource.SWEEP,
            )
        return CriterionResult(
            criterion_id=criterion_id_for(state),
            outcome=CriterionOutcome.UNVERIFIED,
            observation=_describe(
                f"the page answered {status}, reached from a url the run chose itself", notes
            ),
            source=CriterionSource.SWEEP,
        )

    return CriterionResult(
        criterion_id=criterion_id_for(state),
        outcome=CriterionOutcome.MET,
        observation=_describe(f"the page answered {status}", notes),
        source=CriterionSource.SWEEP,
    )


def _notes(state: PageState) -> tuple[str, ...]:
    """Quality findings, which are reported and never judged.

    A page with no title is a real finding on a content site and it is not breakage.
    Spending `failed` — the one verdict that accuses the application — on a page that
    works is how a report starts crying wolf, and a report that cries wolf is one nobody
    reads by the third run.
    """
    return () if state.title.strip() else ("no title",)


def _describe(headline: str, notes: tuple[str, ...]) -> str:
    return headline if not notes else f"{headline}; {', '.join(notes)}"
