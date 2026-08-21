# Story-driven runs work, nine of nine

Phase 16 slices 1 and 5, plus the three findings that were standing between the agent and
a passing story. Point it at a URL, give it a story, and it verifies — measured rather than
asserted.

## The measurement

`BASELINE_REPEATS=3`, nine reachable runs, every one of them:

| shape | verdict | criteria |
| --- | --- | --- |
| one-page | **`passed` 3/3** | 6 / 6 |
| multi-page | **`passed` 3/3** | 6 / 6 |
| after-a-form | **`passed` 3/3** | 3 / 3 |
| unreachable | `blocked` 3/3 | never `failed` |

Three repeats, not one. The earlier numbers in `AGENT_FINDINGS.md` were a single run per
shape, and that misled me: an `after-a-form` pass at n=1 looked like a fix working and
vanished at n=3. Recorded in the doc rather than quietly corrected.

## R5 first, because it is why the rest could be found

A run that took twenty-five actions left three events in the durable log — `run.created`
and two status changes. For an operator with a stuck run that is the verdict and a
screenshot and nothing in between, and it is why two of the three findings below were
guesses.

One event per action now: type, intent, outcome, url, HTTP status, and the browser's own
first line on failure. `ActionRecord` has **no field for a typed value at all** — a `fill`
carries what was typed, and that is the one thing in an action that can be a credential.
The intent says what the step was for, which is what a diagnosis needs. URLs go through
`safe_url`.

Swallowed on failure, unlike the state map: a run whose trace could not be written still
produced a verdict, and refusing to report the verdict because the audit of it failed would
trade the answer for the record of it.

With the trace, two guesses became two two-line diagnoses.

## A7 — a refusal that carries the correction

```text
1 ok   navigate   go_to_home_page
2 FAIL click      navigate_to_records_page
       click has side effects and this policy forbids them
```

The intent was `navigate_to_records_page`. The agent knew where it wanted to go and was
told only that it could not go that way — while the element sat on the page with its url,
and the graph was holding the page.

A refusal now names the action the policy *does* allow for the element the planner named,
**verified with the same guard that refused the original** rather than assumed. And such a
refusal is no longer terminal.

That last part is a policy-semantics change and deserves the argument: ending on any
refusal is what stops an agent hunting for a way around a policy, and that stance is right.
But taking the path the policy allows is not hunting for a way around it — it is the
policy's own answer. Bounded by `MAX_RECOVERY_ATTEMPTS` either way, so it cannot become
probing under another name.

multi-page went 0/3 → 3/3.

## A8 — a control that already has something in it

The trace again, unmistakably: **twenty-four consecutive `fill` actions on the same field,
every one succeeding.** The observation is identical before and after a `fill`, and at
temperature zero an unchanged observation gives an unchanged decision — forever, until the
budget runs out.

The snapshot had always said it: `textbox "Reference": BASELINE`. `Affordance.filled` keeps
the **fact** and never the value, because a password field carries one and an observation is
rendered into a prompt, stored in a state map and read by a person. Out of the signature
key, like `disabled`: a field with something in it is the same field, and in the key every
keystroke would be a new state.

## Each element names the action that takes it

`link: Records -> url` read as something to click, because that is what a link is
everywhere else, and the url beside it was information the planner had and did not use. The
rule already existed — `exploration_action`'s own docstring says a link whose destination
the page gave is followed by navigating, which is read-only — but only the frontier knew
it. It lives on `Affordance.reached_by` now, which the frontier and the observation both
read, so they cannot disagree.

A textbox was worse than unhelpful: labelled `click`. It is filled. `ACTION_FOR_ROLE` maps
each role to the action that operates it, in the action set's own vocabulary.

## A sighting reads the same source the check reads

Reconstructing "what the page says" from the accessible tree got it wrong twice: once by
including the url, so a criterion for `records` matched `/records`; once by including
accessible names, so a criterion for `Email` matched an `aria-label` that renders as an
icon. Both produced `met` for a literal `assert_text` would have failed.

`PageState.body_text` is the string `assert_text` reads. One source, so the two answers
cannot diverge — the class of bug is closed rather than its third instance patched. That
also fixed a blind spot the second attempt had opened: `Create record` is a button label
and genuinely rendered text, so excluding every control name had made a legitimate
criterion unmatchable.

## A defect in the harness, not the agent

With the loop broken, `after-a-form` still failed — on `assert_text: Created BASELINE`. The
fixture refuses a duplicate reference and answers "already exists", so a fixed reference
passes on the first run of the day and never again. **The baseline was not idempotent**, and
it had been quietly contaminating that shape in every measurement recorded in
`AGENT_FINDINGS.md` before this one.

The reference is unique per attempt now. A real QA run does not assume a clean database
either, so unique data is the honest shape rather than a workaround for the fixture.

## For a reviewer

- **ADR 0015** covers HTTP status, observed failures and the redirect check, and says
  plainly what the redirect check does *not* do: it reads the response, so the request has
  already been made. It stops the run observing a disallowed origin; it does not stop the
  browser reaching that host. Request-level interception is a separate change.
- **The policy-semantics change in A7** is the one to argue with if any. The reasoning is
  above and in the code comment.
- **Two metrics the Phase 15 plan asked for are absent from the baseline** — model calls per
  verified criterion and the `invalid_action` rate. Neither is exposed by the public API,
  and the script speaks only to that API on purpose. Said in the script's header so nobody
  infers the agent makes no model calls; getting them properly is a public contract change
  and belongs in its own slice.
- `scripts/agent-baseline.sh` and the injection test's closing-tag case carry edits made in
  the working tree by another session addressing CodeRabbit findings; they were swept up in
  the final commit. Both are covered by the gate below.

## Still open — three of four exit gates

- **traversals without a story** (R1): exploration still cannot leave `about:blank`;
- **reports with analysis**: observed failures are collected and do not reach the report;
- **a smoke against real public sites**: the only gate that catches a fix tuned to the
  fixture.

## Gates

`bash scripts/ci-local.sh` → `ci-local: all green`, run against the pushed commit. Backend
suite, CLI 156, frontend 51, compose config, blueprint, migrations up and reverse.
