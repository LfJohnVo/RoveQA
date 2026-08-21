# What the gateway learns from an HTTP response

Status: Accepted

## Context
`page.goto()` returns a `Response`, and the gateway discarded it. Three consequences, one
of them a security hole:

**A run cannot tell a 200 from a 404 or a 500.** `ActionOutcome` has no field for the
status, and `succeeded` only reports whether the Playwright call threw. So an agent
navigates to an error page, observes whatever it renders, and takes that for the site. For
a landing page or a blog, "no page is broken" *is* the QA question, and it could not be
asked. It is also the mechanism behind the scar `docs/GUIDE.md` records — ninety minutes
spent looking at a Vite "Blocked request" page. The status was in the response.

**Console errors and failed requests are collected and never read.**
`ObservedFailures` accumulates both in the gateway and has no consumer outside that file.
A script that throws or an image that 404s is first-class QA signal on any site, and it
was already being measured.

**Redirects are never re-checked against the allowlist.** `GuardedBrowserGateway`
validates the URL a run *asks* for; `page.goto` then follows redirects with no
interception. A navigation to an allowed origin that redirects to a disallowed one —
`127.0.0.1`, `169.254.169.254`, any internal service — arrives, and the observation is
taken from it. `docs/13` documents the allowlist as the control against exactly that, so
the control does not hold as documented. Raised in review of Phase 15; it predates it.

## Decision

**The response is part of the outcome.** `ActionOutcome` carries the HTTP status of a
navigation, and the episode result carries the console errors and failed requests observed
during it — bounded, and redacted before they leave the adapter, because a failed request
URL can carry a token in its query string.

**The allowlist is enforced on where the browser ended up, not only on what was asked
for.** A navigation whose final URL is outside the run's allowed origins is refused as a
policy violation rather than as a browser error: the run did not fail, it was stopped. The
check covers `back` as well as `navigate`, because history can walk into an origin the
allowlist no longer permits.

**What this does not do, said plainly.** The check reads the response, so the request has
already been made. It stops the run from *observing* or acting on a disallowed origin and
ends the episode; it does not prevent the browser from reaching that host. Aborting the
request itself needs interception below this layer — a route handler that refuses document
requests to disallowed origins while letting sub-resources through — and that is a separate
change with its own cost. The hole this closes is a corrupted observation; the narrower hole
of a request reaching an internal host stays open and is recorded rather than implied shut.
ADR 0012 overclaimed in exactly this way, which is why this paragraph exists.

**A 5xx from the application under test is a product defect**, and therefore one of the
very few paths that may justify `failed`. Three cases are deliberately separated:

| observation | verdict | why |
| --- | --- | --- |
| 5xx on a url the run was told to visit | may accuse the product | the application answered, and answered wrongly |
| 4xx on a link the site itself offers | may accuse the product | the site published a link it cannot serve |
| 4xx on a url a model invented | never accuses the product | the planner guessed; the application is fine |

The third is why status alone cannot decide a verdict: provenance decides who is
responsible, and the run knows the provenance because it knows whether the URL came from
an affordance or from a decision.

## Consequences
`ActionOutcome` and the episode result gain fields; `roveqa.run-report.v1` gains observed
failures. Additive, so existing consumers are unaffected.

A redirect that used to be followed silently now ends the episode with a policy violation.
That is a behaviour change and it is the point — but it means a site that legitimately
redirects between two of its own origins must list both, which is a configuration change
some deployments will notice. Named here so it is a decision rather than a surprise.

The status is not consulted by `wait_for` or by the deterministic text check: a criterion
still passes or fails on what the page says. Status is evidence beside it, not a
replacement for it.
