# Agent findings — Phase 15

What the agent could not do before this phase, why, and what each fix cost. Every number
here was measured against a running stack, not estimated.

## How these were found

By pointing the agent at two unrelated sites and reading what it actually did:

- an internal authenticated application (a React SPA behind a login);
- a public marketing site nobody had used while building this.

The second produced two defects the first could not reveal. Neither is visible against a
local fixture, which is why both survived fourteen phases with green gates.

## The diagnosis that was wrong

`README.md` attributed the ceiling to model capacity — *"un modelo mayor es la variable"*.
It was not. With the criteria in the goal and the whole page in front of it, the planner
emitted:

```json
{"action_type": "assert_text",
 "target": {"text": "Iniciar sesión"},
 "rationale": "…the page observation clearly includes the text 'Iniciar sesión' under a
   heading level 4, so asserting its presence confirms the goal is met."}
```

Right action, right literal, sound reasoning — and the literal in `target.text`, a field
`assert_text` does not read. A larger model emits the same near-miss, because nothing in
the contract said which field was the one.

## The findings

| | Finding | Fix | ADR |
| --- | --- | --- | --- |
| A1 | `BrowserDecision` was flat with every field optional, so `required` was empty and guided decoding could not enforce the one rule that mattered | union with one member per action, generated from the domain's frozensets | 0012 |
| A2 | `describe_page()` captured the accessible tree and `parse_affordances()` kept only the controls: the text was discarded by the method that fetched it | `PageState.content`, rendered as its own section | — |
| A3 | The plan's literals reached only the final verification node; `PlanningRequest` had no field for them | `criteria` on the request, `<acceptance_criteria>` in the prompt | — |
| A4 | `button "Sign in" [disabled]` was parsed and the state dropped, so the agent paid a locator timeout to learn what the observation knew | `Affordance.disabled`, and out of `key` | — |
| A5 | Criteria were checked once, against the page the run ended on — so a story spanning pages could not pass | sightings accumulated on every observation, one-directional | 0013 |
| R2 | `NAVIGATE` is read-only by type, yet a read-only policy refused it: the guard keyed on the model's own `side_effect` flag | the type decides what is forbidden | 0014 |
| R3 | `docker compose up -d` left every service healthy and the API answering 500: nobody ran Alembic | one-shot `migrate` service the readers wait for | — |
| R4 | Three unrelated causes all came back `inconclusive` with `failure_kind: null`, with the reason printed beside them | `failure_kind_for_action` | — |
| N1 | One 10 s timeout served both "click this button" and "load this website", and `goto` waited for `load` | navigation gets its own budget and waits for `domcontentloaded` | 0011 |
| N2 | Playwright quotes values that need it; the quotes were kept, so every anchor link became an unopenable path | one `unquote_snapshot_value`, used by both readings | — |

## Measurements

**Page load, public marketing site.** The reason N1 is fatal rather than untidy:

| `wait_until` | Time |
| --- | --- |
| `load` (Playwright's default) | 23.1 s |
| `networkidle` | 23.9 s |
| `domcontentloaded` | 0.3 s |

**Observation delivered to the planner**, before and after A2:

| Page | Accessible tree | Delivered before | Delivered after |
| --- | --- | --- | --- |
| application screen | 883 ch | 235 ch, no text | whole page |
| marketing landing | 9,183 ch | 2,462 ch, 41 controls, no text | text + controls |

**Malformed URLs**, before N2: 3 of 41 affordances on the landing page, all three of them
its anchor navigation.

**Guided decoding cost**, after A1 — the risk the plan required measuring before
committing to it:

| | |
| --- | --- |
| union members | 15 |
| schema size | 11,364 bytes |
| first call (grammar compile) | 20.05 s |
| warm median | 0.57 s |

Warm decisions got *faster* — the flat schema averaged ~1.2 s — because a constrained
grammar stops emitting fields the action does not have. The compile is once per schema per
server; a run whose whole budget is 300 s pays 7% of it on a cold worker, so pre-warming
is worth considering and is not part of this phase.

## Before and after, same story, same site, same model

A four-criterion story against the public landing page, `Qwen3-4B-Instruct-2507-AWQ-4bit`
throughout:

| | Before Phase 15 | After |
| --- | --- | --- |
| verdict | `inconclusive` | **`passed`** |
| cause | `Page.goto: Timeout 10000ms exceeded`, repeatedly | — |
| criteria met | 0 of 4 | 4 of 4 |
| `invalid_action` | present | 0 |
| wall clock | ~50 s to fail | ~40 s to pass |

The four criteria were credited as *"observed satisfied earlier in the run: step 1"* —
A5 doing exactly what it was added for.

## One calibration this phase got wrong first

`MAX_CONTENT_CHARS` started at 2,000, from the two pages measured at the time. Against the
landing page that truncated the text before three of its four section headings, and the
run met one criterion and never saw the rest. The truncation marker said so in the
observation, which is why this was a diagnosis rather than a mystery — a silent slice
would have looked like a page that simply lacked the content.

Now 6,000: a long landing arrives whole, and a data grid is still refused.

## The baseline

`bash scripts/agent-baseline.sh` runs four story shapes against the bundled target app,
served as a container so the *worker* can reach it. It emits one JSON value on stdout;
diff it against the previous one.

Measured after Phase 15, `Qwen3-4B-Instruct-2507-AWQ-4bit`, one pass:

| shape | verdict | criteria met | cause |
| --- | --- | --- | --- |
| one-page | **`passed`** | 2 / 2 | — |
| multi-page | `blocked` | 1 / 2 | `policy` |
| after-a-form | `blocked` | 0 / 1 | `agent_budget` |
| unreachable | `blocked` | 0 / 1 | `environment` |

Two properties hold, and they are the ones worth stating:

- **the minimum case works** — a text criterion on the first page, which was impossible;
- **the unreachable story never came back `failed`.** That is the safety property the
  whole design rests on, and the baseline asserts it explicitly
  (`unreachable_never_failed`).

Three of four shapes still stop short. Read the table as the honest state of the agent,
not as a phase that failed: before this work, all four were `inconclusive` and no
criterion was ever met.

### A6 — the planner clicks a link it could navigate to

The `multi-page` shape dies on `policy denied click` under a read-only policy. The guard
is right: `click` is write-typed. What is wrong is the choice — the link was listed *with
its url*, and `Affordance.url` exists for exactly this reason, as its own docstring says:
"a link with a url can be followed by navigating, which is a read-only action, while a
button can only be clicked".

**A negative result, recorded because it is the useful part.** The prompt now says so
outright — *"an element listed with a url can be reached with navigate… prefer the url
when one is shown"* — and the 4B model's behaviour did not change. Two measured passes,
identical outcome.

That is the same lesson A1 taught: with this model a rule carried only in prose does not
reliably change the action chosen, and the rule has to live where generation cannot
escape it. The structural fix — making a click on a link-with-a-url unrepresentable, or
having the adapter prefer navigation — changes what an action *means* and needs an ADR
rather than a patch at the end of a phase. It is the next lever, and now it has a number
behind it.

## What guards this from coming back

`backend/tests/browser/test_the_real_web.py`, against real Chromium, on a fixture page
that carries the hazards a public page carries: an image pointing at a resource that never
answers, anchor hrefs the snapshot quotes, a consent overlay, and a submit disabled until
its form is filled.

The first test in that file asserts the *hazard*, not the fix: waiting for `load` on that
page must still time out. If it ever passes, the fixture stopped reproducing the real web
and every test under it is worthless.

That file is the reason N1 and N2 cannot return silently. Every fixture before it was a
local server that answered instantly and completely — the one environment in which both
defects are invisible.
