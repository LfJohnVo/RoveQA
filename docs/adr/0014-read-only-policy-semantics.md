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

Nothing is loosened. `click`, `fill`, `select`, `check`, `uncheck` and `upload` are all
outside the read-only set, and the domain refuses to *construct* one of them that claims
to be harmless, so the guard never sees such an action in the first place.

## Consequences
A read-only run can navigate, observe and verify text criteria — which is what
"the agent looks and does not touch" was always documented to mean.

The origin allowlist is untouched and still bounds every navigation, read-only or not.
`side_effect` remains a signal about retry safety rather than about permission.
