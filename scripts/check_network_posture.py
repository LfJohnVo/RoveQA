"""Nothing but the API may be reachable from off this host (ADR 0021).

Run from `ci-local.sh` against `docker compose config`, which is the resolved truth
rather than what the file appears to say — a variable, an override file or a profile can
all change where a port lands, and only the resolved document knows.

The failure this exists to prevent is not a subtle one. PostgreSQL, Redis, Temporal,
FalkorDB and the model server were published on all interfaces for as long as this
project existed, which on a host with a routable address makes the database a bigger
exposure than the unauthenticated API ever was. Both are fixed; this is what keeps the
second one fixed after somebody adds a service in a hurry.
"""

import json
import subprocess
import sys

LOOPBACK = {"127.0.0.1", "::1", "localhost"}

REACHABLE_BY_A_PROXY = {"api"}
"""The only service allowed a configurable bind.

One entry, and adding a second should be an argument somebody has to win: every other
port here speaks a protocol with no authentication of its own, so "reachable" and
"owned" are the same word for them.
"""


def resolved_compose() -> dict[str, object]:
    finished = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["docker", "compose", "config", "--format", "json"],  # noqa: S607 - on PATH by design
        capture_output=True,
        text=True,
        check=False,
    )
    if finished.returncode != 0:
        print(finished.stderr.strip() or "docker compose config failed", file=sys.stderr)
        raise SystemExit(1)
    document: dict[str, object] = json.loads(finished.stdout)
    return document


def main() -> int:
    services = resolved_compose().get("services", {})
    assert isinstance(services, dict)

    problems: list[str] = []
    checked = 0
    for name, definition in sorted(services.items()):
        for port in definition.get("ports", []) or []:
            checked += 1
            host_ip = port.get("host_ip") or "0.0.0.0"  # noqa: S104 - detecting it, not binding
            published = port.get("published", "?")
            if host_ip in LOOPBACK:
                continue
            if name in REACHABLE_BY_A_PROXY:
                print(f"note: {name} publishes {published} on {host_ip}, which is its own setting")
                continue
            problems.append(f"{name} publishes {published} on {host_ip}")

    if not checked:
        # A resolved document with no ports at all means this check read the wrong thing,
        # and a check that cannot fail is worse than no check.
        print("no published ports found; this check is not looking at the real compose", file=sys.stderr)
        return 1

    if problems:
        print("services reachable from off this host:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(
            "\nEverything but the API binds to loopback (ADR 0021). If this is deliberate,\n"
            "the argument belongs in that ADR, not in a compose file.",
            file=sys.stderr,
        )
        return 1

    print(f"network posture ok: {checked} published port(s), none open beyond the API")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
