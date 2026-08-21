# The decision schema is a union generated from the domain's own sets

Status: Accepted

## Context
`BrowserDecision` was one flat object with every field optional, so
`model_json_schema()["required"]` came back empty and `response_format: json_schema` had
nothing to hold the model to. The rule that `assert_text` needs a `value` lived only as
prose in the system prompt and as a rejection in the domain — after a model call had
already been spent.

The observed failure, at `temperature: 0.0` and therefore reproducible:

```json
{"action_type": "assert_text",
 "target": {"text": "Sign in"},
 "rationale": "…the page observation clearly includes the text 'Sign in' under a
   heading level 4, so asserting its presence confirms the goal is met."}
```

Right action, right literal, sound reasoning — and the literal in `target.text`, a field
`assert_text` does not read. The domain refused it, `recover` returned to `plan`, and the
loop consumed the whole budget: twenty-five calls to land one field away, twenty-five
times. A larger model emits the same near-miss, because nothing in the contract says
which field is the one.

## Decision
`BrowserDecision` becomes a `RootModel` over a union with one member per action type,
plus a `finished` member. Each member's required fields are **generated from
`NEEDS_TARGET`, `NEEDS_VALUE` and `READ_ONLY_ACTIONS`**, and a member does not expose a
`target` at all when its action does not read one.

Generated rather than hand-written for the reason `prompts.py` already renders those same
frozensets: a copy drifts, and the drift is silent. A test asserts that every member of
`BrowserActionType` has a variant, so an action added to the domain either becomes
requestable in the same commit or fails the suite.

Static typing is given the common base under `TYPE_CHECKING` — a checker cannot name the
members of a union assembled at import time, and the base is precisely the interface the
class exposes.

## Consequences
The combination that cost the runs — an action missing the value or the target its type
requires — is unrepresentable rather than refused.

**What this does not do, stated because the first draft of this ADR overclaimed it.** A
union narrows shapes, not contents. `DecisionTarget` still permits `{}` and empty locator
fields, so a `NEEDS_TARGET` action can satisfy the schema and be refused by the domain a
moment later — `InvalidEntityError`, through recovery, one model call spent. The repo's own
test asserts exactly that path, which is how the overclaim was caught in review.

Closing it would mean requiring "at least one non-empty locator", which a JSON Schema can
only say as a branch per field. Nine target-bearing actions make that a much larger
grammar for a case the domain already refuses safely, and the measurement below is the
reason not to spend it blind. Documented rather than inflated; revisit with a number if
empty targets turn out to be common in practice.

Measured cost, which the plan required before committing: 15 members, an 11,364-byte
schema, **20.05 s on the first call** while xgrammar compiles the grammar, then **0.57 s
median** — faster than the 1.2 s the flat schema achieved, because the constrained
grammar emits fewer tokens. The compile is once per schema per server, not per run, but a
run whose whole budget is 300 s pays 7% of it on a cold worker. Pre-warming is worth
considering and is not part of this phase.

The domain remains the authority on what is legal. This narrows what can be *asked for*.
