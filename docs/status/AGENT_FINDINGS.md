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
