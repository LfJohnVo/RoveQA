"""`python -m agentic_qa.admin` — the host-only entry point.

A module rather than a console script so it works with nothing installed but the package
itself, which is the situation inside the container where it is meant to be run:

    docker compose exec api python -m agentic_qa.admin token issue --project <id> --label ci
"""

from agentic_qa.interfaces.admin.tokens import main

if __name__ == "__main__":  # pragma: no cover - the process entry point
    raise SystemExit(main())
