# Review log

What was done with each review finding, and why — including the ones not taken.

Kept in the repository rather than only in the pull-request threads for two reasons. A
thread is answered once and then scrolls away, while the reasoning behind a rejection is the
part somebody needs six months later. And this session had no `gh` and no token, so nothing
below was ever posted: **these are replies still owed.** Post them when the tooling exists,
then leave this file as the record.

Findings are CodeRabbit's, on PRs #1 and #2.

---

# Replies to the CodeRabbit review — PR #1

Paste the top block as a PR comment; the per-thread lines go on their own threads if you
want them resolved individually. Full disposition of all sixteen findings, with reasoning,
is in `docs/status/AGENT_FINDINGS.md` under **What the review caught** (in the branch).

---

## Top-level comment

Thanks — this caught a real false-pass and two gaps in the work. Eight findings fixed in
`e9e89dd`, two rejected with reasons, one recorded as out of scope. Full disposition with
reasoning is in `docs/status/AGENT_FINDINGS.md`.

**The one that mattered:** `criteria_seen` matched `PageState.describe()`, which opens with
`url:`. A criterion whose literal appeared only in the address — `records` in `/records` —
would have been reported `met` by a page that never said it. That is a false pass in exactly
the direction ADR 0013 claims is impossible, so thank you for it. Sightings now match
`PageState.visible_text` — content and control names, no url and no title — which is what
`body.inner_text()` would find, so the two paths can no longer diverge.

**Two gaps in the work, both fair:** `validateAgainst` had no test at all (it compiled,
type-checked and built, and nothing called it — a runtime failure in `plan lint` would have
been invisible), and the planner-level injection test that this phase's own gate promised was
not delivered. Both now exist: 7 tests and
`tests/browser/test_injection_reaches_the_planner_as_data.py`.

**One recorded rather than fixed, and it is the most important thing in the review:**
`page.goto` follows redirects without interception, so a navigation to an allowed origin that
redirects to a disallowed one is never re-checked. The allowlist is documented as the control
against reaching internal services, so that is a real hole in it. Nothing in this branch
touched redirect handling, and closing it is a decision about where the fence lives — it is
now the first slice of Phase 16, with its own ADR.

Gates: `bash scripts/ci-local.sh` → `ci-local: all green` (CLI 156, frontend 51).

---

## Per-thread replies

**`graph.py` — match criterion hints against page content, not the planner serialization**
Fixed. Correct, and it was a false-pass path rather than a cosmetic one. `_sightings` now
matches `PageState.visible_text`, which excludes the url *and* the title so it agrees with
`body.inner_text()`, the source the deterministic check uses. Regression tests in
`TestASightingCannotComeFromTheUrl`.

**`graph.py` — record criterion sightings during exploration**
Fixed. `explore` now merges sightings on the same terms as `observe`, and carries them
through both of its exits.

**`graph.py` — classify exhausted planner rejections as `FailureKind.MODEL`**
Fixed, and the diagnosis was exact: a rejection never reaches the browser, LangGraph keeps
the untouched key, so the classification came from an earlier action. A rejection is now
`model` directly rather than derived from `last_action_type`.

**`gateway.py` — preserve the configured timeout after context recovery**
Fixed. `BrowserSession` carries `navigation_timeout_ms` and `rebuild_context()` passes it, so
a raised budget survives a dead context instead of silently reverting to 45s.

**`affordances.py` — count the serialized text cost**
Fixed. The budget now counts `len(text) + _BULLET_OVERHEAD`, so the parser's limit and the
rendered size mean the same thing.

**`prompts.py` — bound criteria to `MAX_CRITERIA` or batch the planner input**
Fixed by saying so rather than by raising the cap: the prompt now appends
`- and N more, not shown`, matching how `folded_episodes` already handles a partial history.
Silent truncation was the defect; twenty is still the right number to render.

**`schemas.py` — reject empty semantic targets in generated variants**
Correct, and the ADR was overclaiming — the repo's own test asserts the very path you
describe. ADR 0012 now states precisely what the union prevents and what it does not, and why
requiring "at least one non-empty locator" (a branch per field, across nine target-bearing
actions) is not worth the grammar for a case the domain already refuses safely. Revisit with
a measurement if empty targets turn out to be common.

**`test_schemas.py` — make the missing-value tests fail only for a missing value**
Fixed. `target` is now added only for `NEEDS_TARGET` actions, so `extra="forbid"` cannot raise
in place of the missing value.

**`state.py` — add a planner-level prompt-injection integration test**
Fixed, and this was a gate this phase promised and did not deliver. The new test asserts the
property rather than the model's judgement: the payload arrives as delimited data, cannot
close its own block, the rules precede it in a separate message, and neither the origin it
names nor the destructive action it asks for is permitted.

**`policy_guard.py` — block disallowed redirect destinations in the Playwright gateway**
Agreed, and recorded rather than patched. It is a genuine hole in a control documented as the
defence against reaching internal services, and it predates this branch — no change here
touched redirect handling. Adding request interception moves where the fence lives, so it
gets an ADR and is the first slice of Phase 16.

**`prompts.py` — preserve empty deterministic literals**
Not taking this one. `_sightings` and `verify_criteria` both treat an empty hint as no hint
(`if hint:`), so rendering `expected_text=""` as a deterministic literal would have the prompt
promise a check the verifier does not perform. The prompt is currently consistent with the
verifier; the suggestion would make it lie.

**`cli/src/contracts/schemas.ts` — instantiate the imported Ajv constructor directly**
Checked by running it in the CLI container: `typeof default.default` is `function` and both
`new d(...)` and `new d.default(...)` construct successfully. `ajv/dist/2020.js` is CJS with a
self-referencing `default`, and the repo's own `contract-examples.test.ts` has used `.default`
since it was written. So the finding is incorrect as stated — but it pointed at a module with
no tests at all, which was the real problem, so thank you for it either way.

**`README.md` — keep the pending Phase 15 test-harness limitation visible**
Stale by the time it was written: it describes the first commit. The harness landed in
`1cc03a7` (real-web fixture, `scripts/agent-baseline.sh`, reference story set) and
`docs/status/HANDOFF.md` records the resulting state, including the three shapes that still
stop short.

**`plans/phase-15-agent-reliability.md` — add a language identifier to the fenced block**
Fixed, `text`.

**`plans/phase-17-authenticated-runs.md` — define rollback-resistant revocation**
Fixed, and a good catch on a gate the plan asserted without a mechanism. The ADR now has to
define a non-restorable revocation — tombstone, epoch or key version held outside the backup —
and the test is revoke, restore, still revoked.
