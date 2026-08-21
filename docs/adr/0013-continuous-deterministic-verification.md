# A deterministic criterion is checked as the run goes

Status: Accepted

## Context
Criteria were evaluated once, in `verify_criteria`, against the page the run ended on —
and only if the agent had declared the goal reached. Otherwise every criterion came back
"the run did not reach this criterion".

That produced two wrong answers from one cause:

- **A story that spans pages could not pass.** Home → detail → assert-on-detail is the
  ordinary shape for a landing page, a blog or a shop. A literal shown on step 2 is
  legitimately gone by step 5, and the check reported `not_met` with kind `product` —
  the one verdict that accuses the application.
- **A run that stopped early threw away what it had seen.** Evidence showed all four
  criteria satisfied on the page the agent had loaded; the report said none was reached.

A `verification_hint` is a substring. Checking one costs no inference at all, so checking
it once was never a saving.

The reasoning behind the original short-circuit is sound and has to survive: asserting
"order confirmed" against the page where a run got stuck would report the site of the
accident as the outcome.

## Decision
Hints are evaluated on **every observation** and first sightings accumulate as
`(criterion_id → step and url)`. At verification time a sighting may only ever turn
`not_met` into `met`. It can never turn `met` into anything, and it can never produce a
`failed`.

A criterion never observed satisfied keeps today's behaviour exactly: unreached, with the
`failure_kind` that explains why.

The sighting is matched against the rendered observation — page text *and* control names,
so a literal living in a button label is found too. It is a deterministic observation of
the accessible tree, not a model's reading of it, so `model_derived` stays false.

**Ordering is deliberately not modelled.** A criterion that only makes sense after a
prerequisite step could, in principle, be credited too early. The alternative — teaching
the verifier the plan's causal order — is a larger design than this phase, and the
failure it would prevent (a criterion satisfied for the wrong reason) is strictly less
harmful than the one it replaces (a false accusation against the product). Revisit when
a plan expresses ordering explicitly.

## Consequences
`roveqa.run-report.v1` gains observation provenance on a criterion result: additive, so
existing consumers are unaffected. The wording of `observation` changes for criteria
credited from a sighting, and it names where and when.

A run that completes keeps its previous semantics unchanged. Only the two wrong answers
above move.
