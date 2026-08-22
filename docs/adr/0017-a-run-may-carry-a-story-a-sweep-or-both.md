# A run may carry a story, a sweep, or both

Status: Accepted

## Context
Three shapes of run are wanted, and only one of them answers anything today.

**With a story** works: a plan's acceptance criteria are checked, deterministically where
a hint exists, and the run comes back `passed`, `failed`, `blocked` or `inconclusive`.

**With a story and a traversal** also works, and nobody designed it. It falls out of two
decisions taken separately — exploration walks the site from what each page offers, and
ADR 0013 evaluates every hint against *every* observation rather than once at the end. A
crawl therefore credits a criterion the moment some page satisfies it, with no planner
steering there and no model call. This was unverified until now, and the first attempt to
verify it passed for the wrong reason: the exploration test's browser double answered
`succeeded=True` to a text assertion it did not implement, so every criterion came back
met against pages that said nothing. The double now answers the question it is asked.

**Without a story answers nothing.** A story-less run has no assertions, so
`verify_criteria` returns an empty tuple, `_record_results` returns early, and
`derive_verdict` is never reached — it raises on an empty `expected`. The gate-4 smoke made
this concrete: a sweep of iana.org mapped nine pages, captured a console error, and
reported `inconclusive`. "Nobody knows" was the answer to a run that knew nine things.

That is the whole gap. For a landing page, a blog, a documentation site — the applications
this phase exists to support — the QA question is not "did the actor achieve the goal". It
is *do all the reachable pages load*, and nothing could express it.

## Decision

**The sweep is a layer, not a mode.** Every run applies the same universal checks to every
page it observes, whether it is following a story, walking a frontier, or both. Adding a
third mode beside the two would have meant three code paths, three verdict rules and a
combination nobody tested; a layer means the shapes compose because there is nothing to
compose.

**One criterion per visited state**, `criterion_id = page:<route>`, using the normalised
route the state map already computes — so a hundred pages under `/orders/{id}` produce one
row, not a hundred identical ones.

**The outcome comes from the HTTP status and from nothing else.**

| observed | outcome | why |
| --- | --- | --- |
| 2xx / 3xx | `met` | the page answered |
| 5xx | `not_met`, kind `product` | the application answered, and answered wrongly |
| 4xx on a route reached from a link the site published | `not_met`, kind `product` | the site published a link it cannot serve |
| no status observed | `unverified` | a client-side route change makes no response; not knowing is not a finding |

This follows ADR 0015's provenance table. A sweep only ever visits routes the site itself
offered — the frontier takes affordances, never invented URLs — so the 4xx row applies to
every 4xx a sweep sees. A planned run can reach a URL a model invented, and there the same
status must not accuse anyone.

**Quality findings are reported, not judged.** A page with no `<title>` is a real finding
on a content site and it is not breakage. It rides in the criterion's observation text —
"200, no title" — and never changes the outcome. Making it `failed` would spend the one
verdict that accuses the application on a page that works, and a report that cries wolf
about a missing heading is one nobody reads by the third run.

The plan also asked for "has a first-level heading", and it is **not** implemented. The
snapshot parser reads a heading's name and drops its `[level=1]` attribute, so a
`PageState` cannot tell an `<h1>` from an `<h3>`. Carrying the level is a change to the
observation contract — the thing every prompt, state map and signature is built from — and
that is not worth spending on a note that cannot change a verdict. Recorded here rather
than quietly dropped.

**`criterion_results` gains a `source` column**, `plan` or `sweep`. These are genuinely
criteria — a thing checked, with an outcome — and they belong in the same table and the same
verdict machinery. But a reader seeing `criteria` in a report must never confuse "the story
asked for this" with "the sweep checks this on every page", and an `id` prefix is a
convention rather than a type. The column makes it a fact.

**Zero inference, structurally.** Every check reads `PageState`, which the browser already
produced. A sweep of three public sites ran with no model endpoint configured at all
(gate 4) — the strongest available form of "zero model calls".

## Consequences

**A story-less run gets a real verdict.** `passed` when every reachable page answered,
`failed` when one did not, `blocked` when the run could not do its job, `inconclusive` when
it genuinely could not tell. That is the useful answer for a content site and it did not
exist before.

**A run with a story now also reports the health of the pages it walked past**, which it
never did. A story about checkout that walks through a 500 on the way is a run that should
say so, and until now the 500 was invisible unless a criterion happened to name it.

**`derive_verdict`'s `expected` grows.** It raises on an empty expectation, deliberately —
silently passing a run because nothing was checked is the worst failure available. The sweep
criteria are part of what is expected, so a run that visits pages always has something to
expect and the guard keeps its meaning.

**A route that changes without a navigation reports `unverified`, not `met`.** Single-page
applications will produce these. Reporting them as healthy would be a claim nobody measured;
`inconclusive` for a run made entirely of them is the honest answer and a visible prompt to
do better.

**What this deliberately does not do.** No broken-internal-link check yet — following every
link to see if it resolves is a different cost profile and reaches URLs the frontier chose
not to take. No per-page attribution of console errors: the browser adapter accumulates them
across an episode and never clears between navigations, so attaching one to a page would be
an attribution nobody measured (ADR 0015's follow-up says the same). Both want the frontier
and the adapter to cooperate, and that is a slice of its own.
