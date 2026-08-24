# A token names a project, and only the host can mint one

Status: Accepted

## Context

The API has no authentication. Anyone who can reach port 8000 can start runs against any
allowlisted origin, read every report, and register or revoke browser sessions. That has
been true since the first phase and it is the single thing standing between this and a
deployment somebody else can reach.

It is not an oversight. `docs/13-security.md` reserved `AUTH_REQUIRED`, `FORBIDDEN` and
exit code 3 for it and said real auth needs an ADR. The client half was built along the
way: the CLI sends `Authorization: Bearer`, the token may come only from the environment
or the user config — never from the version-controlled project config, because that would
be a token in a repository — and the exit-code contract already reserves 3. What is
missing is the server.

The thing being served is specific, and it should shape the answer rather than a generic
notion of "auth". A development team wants their CI to run tests on every feature they
ship. A CI job is not a person: it does not log in, it does not have a password to forget,
and it runs unattended in an environment where the only secret store is a repository
secret. Designing for a human and then asking a CI to pretend to be one is how systems end
up with service accounts that nobody can revoke because three pipelines share them.

## Decision

### 1. A token names a project

Not a person, not a role. The unit that matters is "this repository's CI, testing this
application", and that maps to a project.

Users and roles are deliberately out. They are a product on top of this one — account
management, an identity provider, session handling — and none of it is needed for a
pipeline to run a test. Adding it now would mean building the larger thing first and
shipping the smaller one late.

The consequence to accept: two people sharing a project share its tokens' reach. That is
the right granularity for a team testing their own application, and the wrong one for a
platform serving several tenants. When the second case appears it will need this ADR
revisited, not extended.

### 2. Hashed with SHA-256, and the reason matters

Stored as a hash, never in clear, compared in constant time.

**SHA-256 and not bcrypt or argon2**, which is the answer that looks wrong until the
reason is said out loud. Password KDFs are slow on purpose because a human-chosen password
has perhaps 30 bits of entropy and an attacker with the hash can guess the whole space. A
token here is 256 bits from the operating system's CSPRNG; there is no space to guess.
Slowing verification would add latency to every request in exchange for defending against
an attack that arithmetic already rules out.

What does matter, and is easy to get wrong, is comparison: `==` on a hash leaks its prefix
through timing, so it is `hmac.compare_digest`.

The token carries a `roveqa_` prefix. Not for parsing — the server hashes the whole string
and looks it up — but because a prefixed secret is greppable in a log that should not have
had it and matchable by the secret-scanning most forges run.

### 3. Only the host can issue one

There is no HTTP route that creates a token. Issuing is a command run on the machine:

```
docker compose exec api python -m agentic_qa.admin token issue --project <id> --label ci
```

This is the same trust boundary the keyring already draws (ADR 0019): whoever has the host
has everything, and pretending otherwise is how a system claims a guarantee it cannot
keep. Drawing it here buys three things. There is no endpoint to leak, no endpoint to
brute-force, and — most importantly — **no administrative super-credential exists**, so
there is nothing whose theft escalates from one project to all of them.

The value is printed once, at issue, and never exists anywhere again. The mirror of the
session rule: a session goes in and never comes out; a token comes out once and never
goes back in.

### 4. The scope check is structural, not per-route

Every route that names a project — or a run, or an environment, which belong to one — must
check that the caller's token covers it. Written as a check inside each handler, that rule
survives until the twelfth handler.

So it is a dependency, and a test walks the OpenAPI document and fails on any route that
is neither covered nor on the exemption list. The exemption list lives in one place and
the same test reads it, so exempting something is a visible edit rather than an omission.
A deliberately planted uncovered route proves the test bites.

`/health` is the exemption. The container's healthcheck and any proxy in front need it,
and it says nothing but whether the process is up.

### 5. Refusal speaks the vocabulary the client already knows

`401` with `AUTH_REQUIRED` when there is no token or it is unknown; `403` with `FORBIDDEN`
when the token is valid and does not cover the resource. Both in the existing error
envelope, so the CLI exits 3 without a line of change, and the two are kept apart because
"you did not authenticate" and "you authenticated as someone who may not do that" send a
person to different places.

## Consequences

- A CI job needs one secret and a URL. Nothing else.
- Revoking one pipeline's token does not touch another's.
- A leaked database gives no usable token.
- There is no credential in the system that grants access to every project.
- Issuing requires shell access to the host, which is a real operational cost and the
  point: minting a credential should not be something a network request can do.
- Two people on one project share its tokens' reach. Multi-tenant isolation is not solved
  here and this ADR is the place to revisit when it is needed.
