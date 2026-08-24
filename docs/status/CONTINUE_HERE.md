# Continue here

Written for whoever picks this up next, on a different machine, with no memory of the
session that produced it. Read this before `HANDOFF.md`: that file records what each phase
closed, this one records where the work actually stands and what to do next.

Last touched: 2026-08-23. Branch: `phase-16-slice-2`, pushed. Phases 00–17 are DONE — there is no next phase, only the release decision in section 3.

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
| 2 | Traversals with no story — exploration maps a real site | ✅ seeds itself from the policy origin |
| 3 | Reports carry analysis — what the browser saw reaches the report | ✅ `observed_failures`, in its own section |
| 4 | A smoke against ≥2 real public sites of different archetypes | ✅ three sites, `scripts/smoke-public.sh` |

Gate 4 is the one that matters most and is easiest to skip. Every serious defect in this
project so far was invisible against a local fixture that answered instantly and
completely, and only appeared against a public site nobody had used for development. A
green gate 1 with no gate 4 means "it works on the thing we built it against".

**Run on 2026-08-21** with `bash scripts/smoke-public.sh`, against three sites nobody here
chose for development, read-only, a handful of navigations each:

| site | states mapped | stopped on | observed |
| --- | --- | --- | --- |
| example.com | 1 | `frontier_exhausted` | — |
| iana.org | 9, with real titles | `max_actions` | 1 console error |
| gov.uk | 8 | `max_actions` | — |

**With no model endpoint configured at all.** That is the part worth keeping: exploration
decides from what the page offers, so a sweep costs zero inference — and running it against
a worker that has no model makes "zero model calls" structural rather than a number that
happened to come out at zero. It also fixed a documented limitation on the way (below).

The console error from iana.org travelled the whole gate-3 chain — Playwright → the
`observed_failures` table → `GET /runs/{id}/report` — on its first outing against a site
nobody controlled.

## 3. Can this be released to production?

**Yes for what it says it is, no for a network it does not own.** The distinction is one
item, and everything else follows from it.

### What is finished and measured

Phases 00–17, every gate. `bash scripts/ci-local.sh` → all green: 1227 backend tests
(5 skipped without a GPU), 172 CLI, 85 frontend, migrations clean from empty and back
down. A 90-minute soak took 91 runs to terminal with none stuck under worker kills and a
Redis flush. Backup and restore are drilled, including the case where a restore must
*not* work: a revoked session stays revoked. Four public sites of different archetypes
pass with zero model calls, and the six-shape baseline is 15/15 reachable, no timeouts.
A planted secret survived none of 165 text columns, the report, the events, the state
map or the logs.

The verdict discipline holds: `failed` only ever comes from a deterministic check, and
the last thing Phase 17 fixed was a login wall that had been producing one.

### What stops it being exposed

**There is no authentication on the API.** Not a bug — `docs/13-security.md` reserves
`AUTH_REQUIRED`/`FORBIDDEN` and exit code 3 for it and says real auth needs an ADR — but
it is the whole answer to this question. Anyone who can reach port 8000 can start runs
against any allowlisted origin, read every report, and register or revoke sessions. The
CLI sends a bearer token; nothing on the server reads it.

Three things follow, and they are properties of the same decision rather than separate
defects:

- **No TLS anywhere.** Reports and, at registration, a session travel in clear.
- **Every backing service is published on all interfaces**, not on loopback: PostgreSQL
  `5432`, Redis `6379`, Temporal `7233`, FalkorDB `6380`, vLLM `8100`–`8102`. On a laptop
  behind a firewall that is convenient. On a host with a routable address it is the
  database, not the API, that is the exposure.
- **The keyring is protected by the host and nothing else** (ADR 0019 says so where
  somebody will read it). It defends a leaked database dump and defeats
  restore-resurrection; it does not defend a compromised machine.

### So, concretely

- **Ship it** on a single trusted machine, or a private segment, operated by whoever
  installed it. That is the product it was built as, and it is finished.
- **Do not** put it on a shared network or the internet as it stands. The minimum before
  that is an ADR and an implementation for API authentication, loopback-only bindings for
  everything except the API, and TLS termination in front.

### Known limits, none of them blocking

- A session the site invalidates *mid-run* is only noticed when the page renders a
  recognisable wall — a bare 403 or an SSO bounce is a gap, stated in
  `domain/browser/authentication.py` rather than guessed at.
- The "page has a first-level heading" check is unimplemented; the parser drops the
  level (ADR 0017).
- Model calls per verified criterion are not exposed by the public API, so the baseline
  cannot report them.
- `blocked` runs with kind `model` track the 4B planner's output quality, not a defect.
- Running `ci-local.sh` while the live stack is exercising the same PostgreSQL instance
  can deadlock the suite's truncating teardown. Seen once, clean on a re-run; it is the
  test environment, not the product.

## 4. Where the work stands

**All four gates hold, and every slice of Phase 16 is closed.**

### The archetype smoke (2026-08-22, `scripts/smoke-archetypes.sh`)

Four public sites chosen to disagree with each other, read-only, **with no model endpoint
configured at all** — a traversal decides from what the page offers, so zero inference is
structural here rather than a number that came out at zero.

| archetype | origin | consent | verdict | pages | seconds |
| --- | --- | --- | --- | --- | --- |
| minimal | `https://example.com` | leave | **passed** | 1/1 | 6 |
| institutional | `https://www.iana.org` | leave | **passed** | 11/11 | 18 |
| government, consent banner | `https://www.gov.uk` | reject | **passed** | 10/10 | 13 |
| machine-facing | `https://httpbin.org` | leave | **passed** | 2/2 | 7 |

24 pages in 44 seconds. It found three defects nothing else could:

1. **`consent: reject` and `destructive_actions: false` contradicted each other** — the
   pair a careful operator picks for somebody else's site. The consent click is
   side-effecting, read-only refused it, a refusal ends the episode, and gov.uk mapped
   **zero** pages. `BrowserAction.answers_consent` makes the permission narrow and named;
   0 pages became 10.
2. **Three graph-state types could not be rebuilt from a checkpoint** — `CriterionSource`,
   `ActionRecord`, `EvidenceRef`. Strict msgpack does not raise, it returns a plain
   `dict`, so a resumed episode would lose its action trace and evidence refs silently.
   The round-trip test could not catch it because its "everything in state" object had
   stopped being everything; the new test walks `GraphState`'s annotations.
3. **Every healthy run showed a red alert** — a passing run has no failure context, the
   server says 404, and the UI called it an error.

### The baseline, measured twice (2026-08-22, `scripts/agent-baseline.sh`)

Six shapes, 3 repeats each, the real model, zero timeouts. Two fixes landed between the
two columns and both are the same fix: the process knew something and did not tell the
part that decides.

| shape | before | after |
| --- | --- | --- |
| `one-page` | 3 passed, 26 s | 3 passed, **6 s** |
| `multi-page` | 3 passed, 26 s | 3 passed, **10 s** |
| `after-a-form` | 1 passed / 2 blocked, 42 s | **3 passed**, **11 s** |
| `unreachable` | 3 blocked, 32 s | 3 blocked, **6 s** |
| `sweep-only` | 3 passed, 5 s | 3 passed, 5 s |
| `story-and-sweep` | 3 passed, 5 s | 3 passed, 6 s |

`reachable_passed` went 13/15 → **15/15**, no criterion lost. The two shapes that already
made no model calls did not move, which is the whole reading: what cost time was
inference nobody needed. `PERFORMANCE_PROFILE.md` has both action logs.

1. A planner invented a form field the page does not have and asked for it **three
   identical times**, ten seconds of locator timeout each. `PlanningRequest.failed_targets`
   now carries what did not resolve, rendered as `<targets_that_did_not_work>`.
2. With that fixed, the same log showed the bigger waste: the criterion was asserted at
   action 5 and **twenty more times** after that, until the budget ran out. `criteria_seen`
   had known since step 0. `story_is_done` ends the episode once every criterion a
   substring can answer has been seen.

### The console can reach a report again

`GET /api/v1/projects/{id}/runs` and a runs table on the project page. Before this, a run
was reachable only while the tab that started it stayed open — everything from a schedule,
the CLI, or yesterday had a report in the database and no route to it. Verified against
the 22 real runs this session left behind.

### One background leak, closed

Every CI run left three `AgentRunWorkflow` executions open forever: the durability tests
asserted a *row* said `completed`, exited the worker block with a workflow task still
pending, and nothing polled that queue again. They now wait for the workflow. **Ten
orphans from before the fix are still open** — terminating them is destructive and is
waiting on someone to ask:

```bash
docker compose exec temporal tctl --address temporal:7233 workflow list --open
```


### What gate 4 found

**A sweep needed a GPU in order not to use one.** `build_model_router` returned `None` with
nothing configured, so `with_agent_runtime` left `container.episodes` unset and *every* run
on that worker "executed no episode" and came back `inconclusive`, with the only
explanation in a log line. It is now an empty router: it exists, serves nothing, and raises
`NoEndpointConfiguredError` the first time somebody actually asks — which the gateway
already turns into a reported failure. A planned run on a model-less worker now ends
`blocked` with kind `model` and the reason attached, instead of silently doing nothing.

**Every sweep reports `inconclusive`,** including the one that mapped nine pages and found
a console error. A story-less run has no criteria, `_record_results` returns early, and the
verdict falls through to "nobody knows". That is slice 3's job (a run mode with its own
reporting), and the smoke turns it from a design note into a thing you can see.

**The consent banner is real and the agent sees it.** gov.uk's first state carries
`button:accept additional cookies` and `button:reject additional cookies` as affordances the
frontier *declined* — correctly, under a read-only policy. Slice 4's input already exists;
what is missing is the decision about closing one, which is a consent decision and belongs
in an ADR before any code.

---

Gate 3 is done.

Gate 3, in one paragraph: `EpisodeResult.page_problems` was the only field of the episode
result that nothing read. Console errors and failed requests were collected by the
Playwright adapter, carried across two layers, and dropped — ADR 0015 had already said the
report would carry them. They now land in a new `observed_failures` table (migration
`d41f7c2a9e08`) and come back in the run report under their own key, with their own section
in the markdown and in the UI, saying in words that **none of them is a verdict**.

The shape of it is worth keeping in mind if you extend it:

- **No findings surface in the schema could hold this.** `criterion_results` and
  `failure_clusters` both require a `criterion_id`. A landing page has no criteria, so a
  sweep of a completely broken site produced a blank report. The new table is the first
  place an observation about a *page* can live.
- **The grain is the episode, not the page**, and the code says so. The adapter accumulates
  across a whole episode and never clears between navigations, so attributing a problem to
  a page would be inventing a measurement. A site sweep needs that grain and will have to
  earn it — `ObservedFailure` has an `episode_index` and no url, deliberately.
- **They cannot reach a verdict**, and the type enforces it rather than a convention:
  `ObservedFailure` has no outcome and no `failure_kind`. There is nothing to set.

Three defects fell out of doing it, all found by writing the thing that used them:

1. **The redaction was written and never exercised.** A console line saying
   `auth failed for token sk-live-…` went through untouched: the patterns covered query
   strings, userinfo, `Bearer` and JWTs — every shape a *machine* emits — and not the shape
   a person types. Fixed with vendor-prefixed key patterns and a prose rule keyed on the
   vocabulary `_SECRET_KEYS` already had, bounded so it does not eat "session expired".
2. **`page_problems()` deduplicated after capping**, so twenty-five retries of one broken
   image reported one finding and hid the twenty-six distinct URLs behind it. The code's own
   comment described the correct behaviour; the code did the opposite.
3. **The episode runner asked the raw gateway, not the guarded one** it had handed the
   graph, leaving `GuardedBrowserGateway.page_problems` with no caller at all.

---

**Gate 3 is done.** Gate 2 is done: the `explore` node seeds itself from the run policy's
origin (`seed_action` in `domain/exploration/actions.py`), through the guarded browser and
counted as an action like any other step. The two `page.goto` calls the tests were making
on production's behalf are gone — including
`backend/tests/browser/test_exploring_a_real_app.py:60`, which was the only reason the
Phase 12 gate had ever passed.

Two details of that fix are worth not re-deriving:

- **The seed condition is "nothing described yet **and** the last action did not succeed",
  not a `seeded` flag.** A flag set when the navigation is *requested* stays true when it
  fails, and the retry then describes `about:blank`, finds nothing, and reports a complete
  map — the exact lie the seed exists to prevent. The first entry has no last action, which
  reads as "not succeeded", so it seeds; a resumed crawl has a frontier, so it does not.
- **An unreachable origin re-seeds until Recover's bound**, and Recover already classifies a
  navigation that will not complete as `environment` → `blocked`. No new code path was
  needed for the second gate; it fell out once the seed stopped lying about success.

Also: `test_it_cannot_wander_outside_the_allowed_origin` had to change its setup. It used to
point the policy at a host that was not the target, which only tested the frontier while
nothing navigated on its own. Now that a run seeds from that same policy, such a setup tests
a run that never arrives. The fixture's home page carries a link to `elsewhere.test`
instead, which is what a real page looks like anyway.

Then gate 4.

## 5. Bring it up on a new machine

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

## 6. Lessons that cost real time

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

## 7. Branch and PR state

| Branch | Commit | State |
| --- | --- | --- |
| `main` | `0b2b7ae` | PRs #1 and #2 merged |
| `phase-16-slice-2` | `9b21a79` | **this branch**, pushed |

`bash scripts/ci-local.sh` → `ci-local: all green` on `9b21a79`.

To open the PR, the body is ready at `docs/status/pr-phase-16-slice-2.md`.

## 8. Blocked on tooling, not on decisions

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

## 9. Reading order for a new session

1. `CLAUDE.md` — the invariants. They are not negotiable and several are load-bearing.
2. This file.
3. `docs/status/AGENT_FINDINGS.md` — every defect with the run that produced it, including
   the ones that were rejected and why.
4. `plans/phase-16-any-site.md` — the next slice, with its gates.
5. `docs/adr/0011`–`0015` — the decisions taken, including what each one deliberately does
   *not* do. ADR 0012 and 0015 both carry a paragraph correcting an earlier overclaim; those
   paragraphs are the useful part.
