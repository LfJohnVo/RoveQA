# Closing a consent overlay is a decision, not a click

Status: Accepted

## Context
A consent banner is the first thing an agent meets on the public web. The gate-4 smoke
made it concrete rather than theoretical: gov.uk's home page came back with
`button:accept additional cookies` and `button:reject additional cookies` as its first
two affordances, and the frontier declined both — correctly, under a read-only policy,
because a button may change the world.

So the agent sees the banner and cannot get past it. On a site whose overlay covers the
content and intercepts clicks, that is the run over before it started.

The obvious fix is to click something. That is where this stops being a browser problem.

**Accepting cookies is a legal act performed on somebody's behalf.** Under the GDPR and
the ePrivacy directive, consent must be freely given, specific, informed and unambiguous.
An agent that clicks "Accept all" because it was the biggest button has manufactured an
unambiguous-looking signal that nobody gave, against a third party's site, from the
operator's IP address. The site records it as a person consenting. It was not.

There is a second, quieter problem. "Accept all" is usually the *easiest* button — larger,
higher contrast, first in the DOM. Any heuristic that optimises for "get past the overlay"
will find it. The path of least resistance and the most-conceding option are the same
button, by design, on most of the web.

## Decision

**A run closes a consent overlay only when its policy says it may.** A new
`consent: ConsentPolicy` field on `RunPolicy`, defaulting to `LEAVE`:

| value | behaviour |
| --- | --- |
| `leave` (default) | Never touch it. The run reports the overlay as an observation and carries on, blocked by it if the site is built that way. |
| `reject` | Take the least-conceding option the overlay offers. |
| `accept` | Take the accepting option. Never a default, never inferred. |

Defaulting to `LEAVE` costs runs, and that is the correct trade. A run that fails because
a banner was in the way is a visible, diagnosable failure with an obvious remedy. A run
that quietly accepted tracking on the operator's behalf, on a site they do not own, is a
thing nobody finds out about until somebody else does.

**`reject` is the recommended setting and not the default.** Recommending it in the
documentation and requiring it in the policy are different acts: the first is advice, the
second is the operator saying "yes, on my behalf, do this". Only the operator can say that.

**The least-conceding option is chosen by matching the overlay's own labels**, in order:
reject-shaped ("reject", "only essential", "necessary only", "decline"), then
manage-shaped, and only under `accept` the accepting ones. When nothing matches, the run
does not guess — it reports the overlay unhandled. A banner whose buttons say "Sure" and
"Maybe later" is one a person should look at.

**Closing it is an action in the log, never a side effect of observing.** It goes through
`act` like any other action: counted against the budget, checked by the policy guard,
published as a `run.action.taken` event. An agent that quietly clicked things during
observation would be an agent whose trace does not explain what happened to the site.

**Detection is by label, and that is a heuristic — said plainly, because the first draft
of this ADR claimed otherwise.** It asserted that `dialog` and `alertdialog` are
interactive roles whose buttons carry their container, so an overlay could be recognised
structurally. They are not: `INTERACTIVE_ROLES` holds neither, and the observation
flattens a dialog's buttons into ordinary affordances with nothing saying where they came
from. The gov.uk smoke shows exactly that — `button:accept additional cookies` sits beside
every other button on the page.

So recognition works on the affordance labels the page already offers, and its limits are
real: a banner whose buttons say "Sure" and "Maybe later" is not recognised, and a page
with an unrelated button named "Accept" could be. Both fail toward doing nothing, which is
the safe direction here. No vendor list of CMP selectors either — that is a maintenance
treadmill that fails silently on the site it does not know.

Carrying the container role through the observation would make this structural, and it is
a change to the contract every prompt, state map and signature is built from. Worth doing;
not worth doing tacitly inside this slice.

## Consequences

**A default run against a banner-gated site still fails**, and says why. That is the
intended behaviour, not a gap: the remedy is one policy field, named in the report.

**`reject` can be wrong.** A "reject" button that actually accepts, an overlay that
reappears, a wall that refuses the site without consent — all real on the public web. The
run reports what it clicked and what happened next; it does not promise the site honoured
it. Claiming otherwise would be asserting something the agent cannot observe.

**Nothing here applies to the application under test being your own.** A team pointing
this at their own staging site can set `accept` and never think about it again. The
default protects the case where the target belongs to someone else, which is the case
Phase 16 exists for.

**Not decided here:** what a run does about a login wall, a paywall, or an age gate. They
look similar — an overlay between the agent and the content — and they are not the same
question. A cookie banner is a consent decision; a paywall is a payment decision and a
login is an identity one. Each deserves its own answer and none of them should inherit
this one by accident.
