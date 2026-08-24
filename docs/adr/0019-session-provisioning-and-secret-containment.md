# A run borrows a session it cannot read

Status: Accepted

## Context

Everything RoveQA can test today is what an anonymous browser can reach. `storage_state`
exists in the codebase but only for *recovery* — restoring the context a crashed worker
lost — and `browser_factory` opens an anonymous context every time. There is no concept of
a credential anywhere in the domain.

A login is one archetype among the several Phase 16 opened up, not the gate to the rest. A
landing page, a documentation site, a blog, a shop with guest checkout: none of them need a
session, and all of them work now. This phase is last on purpose. It is the most expensive
archetype — durable credentials, verified redaction, policy scope inside an authenticated
application — and the one that adds the least generality per unit of work. An anonymous
context stays a first-class path after this, not a degraded case.

Four things make it expensive, and they are worth naming before deciding anything.

**A secret has more exits than a value.** This system writes a prompt, a durable event per
action, an artifact, a state map, a knowledge graph and a report. A password that enters at
one end can leave through six. Redaction at each exit is six chances to forget one.

**An authenticated run can reach more than a destructive one.** `destructive_actions: true`
lets an agent click. A valid session lets it click *as somebody*, and that somebody may be
an administrator. The origin allowlist — the only scope control that exists — says nothing
about which parts of an application are in bounds.

**A session expires, and an expired session looks like a broken product.** The page comes
back as a login form, the criterion's literal is absent, and a deterministic check would
report `failed`: an accusation against an application that is working correctly.

**Revocation has to survive a restore, and encryption does not give you that.** If the
record that says "revoked" lives next to the credential, restoring last week's backup
brings back both the ciphertext and a row that no longer says revoked. Add an expiry and
you get the same problem with a delay. Anything restorable can be restored.

## Decision

### 1. A session is borrowed; a password is referenced

Two kinds of thing, deliberately unequal.

**An `EnvironmentSession` is an already-established `storage_state`** — cookies and origin
storage captured from a browser somebody logged into themselves. Provisioning it into a
context puts no password anywhere near the agent loop, because there is no password. This
is the supported path and the one the documentation leads with.

**A named secret is a reference, never a value.** `BrowserAction` gains `secret_ref`, which
names a secret the *environment* declared; it is mutually exclusive with `value`. The
domain carries the name, and only the Playwright adapter — the last few lines before the
keystroke — resolves it. A planner can therefore ask to type a password it has no way to
read, and cannot invent one that was not registered.

This second path exists so that logging in can itself be the story under test. It is not
the way to reach an authenticated page; the first path is.

### 2. PostgreSQL holds ciphertext and nothing else

Sealed with AES-GCM from `cryptography` — a new dependency, and the right kind. Rolling
authenticated encryption by hand is the one place where the smallest diff is the wrong
answer.

The key is never in the database, never in a migration, never in a fixture and never in an
environment variable that a `docker compose config` would print.

### 3. One key per session, in a keyring outside the database

This is what makes revocation survive a restore, and it is the whole reason for the shape.

Each session's data key lives in a keyring the database cannot see. `secrets_keyring`
holds one entry per session id. PostgreSQL holds only the sealed bytes.

**Revoking a session deletes its key.** Not a flag, not a status column — the key. The
ciphertext may be restored from any backup ever taken and it decrypts to nothing, because
what was destroyed was never in the backup. The gate is exactly this: revoke, restore an
earlier dump, confirm the session is still dead.

A tombstone row would have been simpler and would have failed the gate. An epoch counter
in the database would have failed it for the same reason. The mechanism has to be the
absence of something, held somewhere a `pg_restore` cannot reach.

`scripts/backup.sh` does not include the keyring, and its manifest says so rather than
leaving it to be noticed. That is a deliberate asymmetry with a cost: **a restore cannot
bring sessions back**, and someone has to re-provision them. That is the correct trade —
losing a session costs one login, and resurrecting a revoked one costs whatever the
revocation was protecting against.

What this does not protect against is stated plainly: an attacker with the host has the
keyring. This defends against a leaked database dump and against restore-resurrection, not
against a compromised machine. A single-node self-hosted deployment cannot honestly claim
more, and claiming more is how people stop being careful.

### 4. An expired session blocks the run and says so

`FailureKind.SESSION` — distinct from `ENVIRONMENT`, because "your session expired" and
"the site is down" lead to different actions by different people. The run comes back
`blocked` with that cause, and no criterion is judged against the login page it landed on.

### 5. Policy scope reaches inside the application

`RunPolicy` gains `forbidden_paths`: path prefixes a run may not visit, checked in the same
domain guard that already checks the origin.

Denied prefixes rather than an allowlist, and the reason is exploration. An allowlist would
have to enumerate every path worth crawling, which is precisely the thing the crawler is
for; the first unlisted page would end the episode. A denylist expresses what an
authenticated run actually needs to say — *you can now reach `/admin`, and you must not
go there* — and leaves everything else discoverable.

It does not weaken anything. The origin allowlist still bounds the run, `destructive_actions`
still gates every write, and consent still needs its own permission. This is a fourth fence
inside the first, not a gate in it.

## Consequences

- A story only reachable behind a login can be verified, and the operator's password never
  enters the process that plans.
- A leaked database dump yields no usable session.
- A restore cannot resurrect a revoked session, and cannot restore a live one either.
  Re-provisioning after a restore is a documented step, not a surprise.
- An expired session is `blocked` with a cause. It never accuses the product.
- Registering or rotating a session touches neither the repository nor the running stack.
- The secret-reference path is narrow by construction: an action carries a name, the
  adapter resolves it, and no layer in between can print what it resolved.
