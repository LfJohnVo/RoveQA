#!/usr/bin/env bash
# The gate. Every check runs inside a container, so a green result means the same
# thing on any machine — and the runtime the code is tested on is the Linux runtime
# it is deployed on, not whatever the developer happens to have installed.
#
# Requires the dependencies to be up: `make up`.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== compose config =="
docker compose config --quiet

echo "== blueprint =="
docker compose --profile gates run --rm --quiet-pull blueprint-check

echo "== backend: ruff, mypy, migrations, pytest =="
docker compose --profile gates run --rm --quiet-pull backend-tests sh -c "
  set -e
  ruff check .
  ruff format --check .
  mypy
  alembic upgrade head
  alembic check
  # The suite has its own database, and it is migrated the same way. Relying on
  # create_all leaves it on whatever schema existed when a table was first made:
  # a new column never appears, and the failure surfaces as a missing column in a
  # test rather than as the schema drift it is.
  #
  # Reset first. pytest still falls back to create_all when the schema is missing, so
  # running the suite before the gate leaves tables no migration created — and the
  # upgrade below then fails on a table it is about to create. The test database is
  # disposable; the gate's reproducibility is not.
  python scripts/reset_test_schema.py
  POSTGRES_DSN=\"\$POSTGRES_TEST_DSN\" alembic upgrade head
  pytest -q
"

echo "== cli: eslint, typecheck, contract tests =="
docker compose --profile gates run --rm --quiet-pull cli-tests

echo "== frontend: eslint, typecheck, vitest, build =="
docker compose --profile gates run --rm --quiet-pull frontend-tests

echo "ci-local: all green"
