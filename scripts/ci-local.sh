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
  pytest -q
"

echo "== cli: eslint, typecheck, contract tests =="
docker compose --profile gates run --rm --quiet-pull cli-tests

echo "== frontend: eslint, typecheck, vitest, build =="
docker compose --profile gates run --rm --quiet-pull frontend-tests

echo "ci-local: all green"
