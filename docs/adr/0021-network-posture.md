# Everything binds to loopback except the API

Status: Accepted

## Context

For as long as this project has existed, `compose.yaml` published every port on every
interface: PostgreSQL `5432`, Redis `6379`, Temporal `7233`, its UI `8233`, FalkorDB
`6380`, the console `5173`, the model servers `8100`–`8102`, and the API `8000`.

On a laptop behind a firewall that is convenient and harmless. On a host with a routable
address it is the exposure that matters more than the one everybody talks about. The API
at least *is* a designed interface with a policy model; PostgreSQL on port 5432 with the
default credentials from `.env.example` is the whole system, and Redis and FalkorDB
authenticate nobody at all. Fixing authentication (ADR 0020) and leaving these open would
have been putting a lock on the front door of a house with no back wall.

The operator for this deployment runs an internal network and terminates TLS with their
own proxy. That decides the shape: this repository should not carry certificates, proxy
configuration, or a reverse proxy nobody asked for.

## Decision

**Every published port binds to `127.0.0.1` except the API's.**

The API's is `${ROVEQA_API_BIND:-127.0.0.1}`, configurable because the proxy may be on
this host or on another one. Defaulting to loopback means a deployment that forgets to
think about it is closed rather than open — the direction a default should fail in.

Everything else uses `${BIND_LOOPBACK:-127.0.0.1}`. The variable exists so a developer
can knowingly open a port to debug from another machine, and is never set in a
deployment. Naming it rather than hard-coding `127.0.0.1` is what makes the override an
act somebody performs instead of an edit somebody makes to a tracked file and forgets to
revert.

**`scripts/check_network_posture.py` runs in the gate**, against `docker compose config`
rather than the file — a variable, an override file or a profile can each change where a
port lands, and only the resolved document knows. It runs with every profile active,
because a port exists in that document only when its service's profile does, and three of
the ten live behind the model-server profiles.

Two things the check refuses to do quietly. It fails when it finds no ports at all, since
a check that cannot fail is worse than no check. And it allows exactly one service a
non-loopback bind, by name: adding a second should be an argument somebody has to win,
because every other port here speaks a protocol with no authentication of its own.

## What the proxy has to do

Stated as a contract rather than shipped as configuration, because it is the operator's
infrastructure:

- **Terminate TLS.** The API speaks plain HTTP and will keep doing so.
- **Forward `Authorization` untouched.** The bearer token is the whole authentication
  model; a proxy that strips or rewrites it makes every request a `401`.
- **Preserve `X-Request-Id` when present, and generate one when absent.** It is how a
  report is traced back through the logs.
- **Not buffer responses indefinitely.** `run wait` is a bounded long poll; a proxy with a
  short read timeout turns a working wait into a client error, and one that buffers turns
  a stream into a stall.
- **Leave `/health` reachable** for its own checks, and optionally close `/openapi.json`,
  `/docs` and `/redoc` if it prefers not to publish the API's shape. Those are open by
  decision (ADR 0020) and the proxy is the right place to disagree.

## Consequences

- A leaked or guessed database credential is no longer reachable from the network.
- A deployment that forgets to configure anything is closed, not open.
- Anyone running the console from another machine has to say so with `BIND_LOOPBACK`, and
  that is the point.
- TLS and certificate lifecycle stay out of this repository, where they would have been
  one operator's infrastructure living in everybody's source tree.
- The API is still plain HTTP on its own. Without a proxy in front, a token crosses the
  network in clear — which is why the proxy contract above is a contract and not advice.
