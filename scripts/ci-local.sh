#!/usr/bin/env bash
# Local CI gate: run every Phase-00 check. Fails fast on the first red gate.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== blueprint =="
bash scripts/validate-blueprint.sh

echo "== backend: ruff =="
(cd backend && uv run ruff check . && uv run ruff format --check .)
echo "== backend: mypy =="
(cd backend && uv run mypy)
echo "== backend: pytest =="
(cd backend && uv run pytest)

echo "== frontend: eslint =="
(cd frontend && pnpm lint)
echo "== frontend: typecheck =="
(cd frontend && pnpm typecheck)
echo "== frontend: vitest =="
(cd frontend && pnpm test)
echo "== frontend: build =="
(cd frontend && pnpm build)

echo "== compose config =="
docker compose config --quiet

echo "ci-local: all green"
