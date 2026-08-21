# The action type decides what a read-only policy forbids

Status: Accepted

## Context
`NAVIGATE` is in `READ_ONLY_ACTIONS` — "actions that cannot change the target's state" —
and a read-only policy refused it anyway. `policy_guard` keyed the ban on
`action.side_effect`, which is the model's own read of its action, and `schemas.py` lets
the model *raise* that flag but never lower it.

So an over-cautious planner marking `navigate` as state-changing — not wrong, merely
careful — made a read-only run impossible. At `temperature: 0.0` this is reproducible:
every read-only run died on its first navigation, and the verdict came back `blocked`
with kind `policy`, which reads as the user's own configuration rather than as a defect.

Read-only is also the natural mode for the cases that need it most: a public landing
page, a blog, a site nobody wants an agent typing into.

The one-way escalation was deliberate, and its stated purpose was to prevent "an
unverified click on Delete account". But `click` is not in `READ_ONLY_ACTIONS`. That case
was already refused **by type**, and always had been.

## Decision
The **type** decides what is forbidden: an action outside `READ_ONLY_ACTIONS` needs
`destructive_actions`. The model's escalation keeps its real effect — `to_domain_action`
gives an escalated action a `VERIFY_BEFORE_RETRY` strategy and a verification strategy —
but it no longer converts a read-only action into a forbidden one.

Nothing is loosened, and the chain is worth stating exactly because the first draft of
this ADR described a refusal that never actually fires. `click`, `fill`, `select`, `check`,
`uncheck` and `upload` are all outside the read-only set, and two independent things hold:

- `schemas.py` **forces** `side_effect=True` for any action outside that set, so a model
  cannot even express one of them as harmless — the flag is a one-way ratchet at the
  adapter boundary;
- `policy_guard` then denies by *type*, so the decision does not depend on the flag at all.

`BrowserAction.__post_init__` does refuse to construct a write that declares itself
harmless, and there is a test for it — but on the model path that state is unreachable,
because the adapter already set the flag. It is a belt beside the braces, not the control.

## Consequences
A read-only run can navigate, observe and verify text criteria — which is what
"the agent looks and does not touch" was always documented to mean.

The origin allowlist is untouched and still bounds every navigation, read-only or not.
`side_effect` remains a signal about retry safety rather than about permission.
