# Continue here

Written for whoever picks this up next, on a different machine, with no memory of the
session that produced it. Read this before `HANDOFF.md`: that file records what each phase
closed, this one records where the work actually stands and what to do next.

Last touched: 2026-08-21. Branch: `phase-16-slice-2`.

---

## 1. What this is trying to be

An agent that can be pointed at **any URL** and produce a QA report — with a user story or
without one — and whose verdicts are believable.

The believability is the hard part and it is the whole design. `failed` is the only verdict
that accuses the application under test, and it may only come from a deterministic check
that actually ran. Everything else — `blocked`, `inconclusive` — says the run could not do
its job and why. A single false accusation makes every later report suspect, so the bias is
always toward admitting ignorance.

## 2. The four exit gates

The work is not finished until all four hold, **measured, not asserted**.

| | Gate | State |
| --- | --- | --- |
| 1 | Story-driven runs pass on the fixture app | ✅ **9 of 9** with `BASELINE_REPEATS=3` |
| 2 | Traversals with no story — exploration maps a real site | ❌ R1: exploration cannot leave `about:blank` |
| 3 | Reports carry analysis — per-page findings reach the report | ❌ collected in the adapter, never surfaced |
| 4 | A smoke against ≥2 real public sites of different archetypes | ❌ not started |

Gate 4 is the one that matters most and is easiest to skip. Every serious defect in this
project so far was invisible against a local fixture that answered instantly and
completely, and only appeared against a public site nobody had used for development. A
green gate 1 with no gate 4 means "it works on the thing we built it against".

## 3. Where to start, concretely

**Gate 2 is next**, and its blocker is already removed. Phase 16 slice 2 in
`plans/phase-16-any-site.md`: exploration goes `START → explore`, which describes the page
the browser is *currently* on, and nothing in the production path ever navigates to the
application. The Phase 12 gate passes only because the test itself calls
`page.goto(base_url)` — see `backend/tests/browser/test_exploring_a_real_app.py:60`. Delete
that line as part of the fix, or the gate goes on hiding it.

It needed two things that now exist: a read-only policy that can navigate (ADR 0014) and a
navigation timeout that survives a real site (ADR 0011).

Then gate 3, then gate 4.

## 4. Bring it up on a new machine

```bash
docker compose up -d          # migrations run themselves now; see ADR 0011 slice notes
docker compose ps             # everything healthy
```

`docker compose up -d` used to leave every service healthy and the API answering 500,
because nobody had run Alembic and `/health` does not touch a table. A one-shot `migrate`
service fixed that; if the API 500s on a fresh volume, that service is the first suspect.

**The model.** If the GPU is 16GB or larger, `.env.example` already sizes for it. If it is
smaller, read `infra/model-env.example.sh` before trying anything — it records the three
ways of shrinking the model that each fail differently, with the error each one produces.
Source it before every compose call touching `vllm` or `worker`; the served name and the
requested name must match or every run comes back inconclusive.

**Measure before changing anything:**

```bash
BASELINE_REPEATS=3 bash scripts/agent-baseline.sh > baseline.json
```

One JSON value on stdout, progress on stderr. Diff it against the next one — that is the
whole point. With no model endpoint it reports `model: absent` and exits 3 rather than
printing zeros that look like a result.

**Use three repeats, not one.** A single run per shape cannot tell a cause from variance,
and it did mislead this session: an `after-a-form` pass at n=1 looked like a fix working and
vanished at n=3.

## 5. Lessons that cost real time

These are not style notes. Each one was a defect that shipped or nearly did.

**The same bug three times: reconstructing "what the page says".** Sightings were matched
against a rebuilt string, and it was wrong by including the url (a criterion for `records`
matched `/records`), then wrong by including accessible names (a criterion for `Email`
matched an `aria-label` that renders as an icon), then wrong by excluding all control names
(a button label is genuinely rendered text). Each produced a criterion reported `met` that
`assert_text` would have failed — a false pass, the worst direction. The fix was not a third
patch: `PageState.body_text` is the string `assert_text` reads. **When two answers must
agree, give them one source.**

**Prose in the prompt does not steer this model.** Told outright to prefer navigating over
clicking, the 4B model's behaviour did not change across two measured passes. What worked
was structural: the observation naming the action each element takes, and a schema in which
the invalid shape cannot be generated (ADR 0012). Budget for that: a rule that matters
belongs in the contract, not the wording.

**The observation is the bottleneck, not the model.** Almost every failure traced to
something the browser had already captured and thrown away: the page's text, `[disabled]`,
whether a field already had a value, the HTTP status, console errors. The pattern is so
consistent it is worth checking first — before blaming the model, ask what the process
already knows and does not pass on.

**Instrument before diagnosing.** Two blockers were guesses for hours. Publishing one event
per action (R5) turned both into two-line diagnoses, visible in the trace. If something is
opaque, the fix is usually to make it say what it did.

**Suspect the harness.** With the loop broken, one shape still failed — because the fixture
refuses a duplicate reference and the baseline reused one. The measurement had been
contaminating that shape in every earlier number. Test data must be unique per run; a real
QA run does not assume a clean database either.

## 6. Branch and PR state

| Branch | Commit | State |
| --- | --- | --- |
| `main` | `0b2b7ae` | PRs #1 and #2 merged |
| `phase-16-slice-2` | `3c7ad55` | **this branch** — pushed, PR not yet opened |

`bash scripts/ci-local.sh` → `ci-local: all green` on `3c7ad55`.

To open the PR, the body is ready at `docs/status/pr-phase-16-slice-2.md`.

## 7. Blocked on tooling, not on decisions

Three things this session could not do. None needs a design decision, all need something
installed or granted.

**No `gh`, no `GH_TOKEN`.** Pull requests could not be opened and review threads could not
be answered from here. `winget install --id GitHub.cli && gh auth login`, or export a `repo`
scoped PAT. Until then the replies accumulate as files — see
`docs/status/REVIEW_LOG.md`, which carries the disposition of all 28 CodeRabbit findings
from PRs #1 and #2 and is what should be posted.

**No `graphify` CLI, no `uv`.** `make graphify-refresh` cannot run. `pip` exists but points
at the system Python, and installing a tool there is a change nobody asked for.
`uv tool install graphifyy` on a machine that has `uv`.

**The committed graph is stale, and specifically so.** `graphify-out/` was regenerated from
the code as it stood *before* Phase 15 — a commit named `grafiphy` was made on a `main` that
had not yet pulled the merges. So the graph describes the architecture without any of the
Phase 15 or 16 work. Regenerate it before trusting it for orientation, and commit that on
its own: a refresh is ~360k lines and swamps any review it is mixed into.

## 8. Reading order for a new session

1. `CLAUDE.md` — the invariants. They are not negotiable and several are load-bearing.
2. This file.
3. `docs/status/AGENT_FINDINGS.md` — every defect with the run that produced it, including
   the ones that were rejected and why.
4. `plans/phase-16-any-site.md` — the next slice, with its gates.
5. `docs/adr/0011`–`0015` — the decisions taken, including what each one deliberately does
   *not* do. ADR 0012 and 0015 both carry a paragraph correcting an earlier overclaim; those
   paragraphs are the useful part.
