# Navigation and element waits are different scales

Status: Accepted

## Context
`DEFAULT_ACTION_TIMEOUT_MS = 10_000` served every browser action, navigation included,
and `page.goto()` waits for `load` by default. Measured against a public marketing site:

| `wait_until` | Time |
| --- | --- |
| `load` (Playwright's default) | 23.1 s |
| `networkidle` | 23.9 s |
| `domcontentloaded` | 0.3 s |

Every run against that site died in `Page.goto: Timeout 10000ms exceeded` without ever
seeing the page. The content the agent reads was ready in three tenths of a second; the
remaining 23 were images and third-party tags. The defect is invisible against a local
fixture and fatal against the real web, which is why it survived fourteen phases.

## Decision
Navigation gets its own budget (`DEFAULT_NAVIGATION_TIMEOUT_MS`, 45 s) and waits for
`domcontentloaded` rather than `load`. Element interaction keeps the 10 s budget.

Waiting for the network stays available as something an action *asks for* — `wait_for` —
rather than a condition imposed on every navigation. A site that needs it says so; a site
that does not is not held hostage to its own analytics.

The number is overridable through `BROWSER_NAVIGATION_TIMEOUT_MS`, and `Settings` holds
`int | None` rather than a second copy of the default: a navigation budget is a browser
concern, the adapter owns it, and two literals would drift.

## Consequences
A page whose DOM is ready but whose images are not is now observed, which is the correct
reading for an agent that reads the accessible tree. A test that relied on navigation
implying a fully settled network must ask for that explicitly.

Phase 15 slice 10 classifies a navigation timeout as `environment`; before that it fell out as
`inconclusive` with no kind at all.
