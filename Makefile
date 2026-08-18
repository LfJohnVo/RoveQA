# RoveQA developer commands. Requires: uv, pnpm, docker compose, bash.
.PHONY: bootstrap backend-check frontend-check check compose-config up down logs blueprint-validate graphify-refresh migrate migrate-down

bootstrap:
	cd backend && uv sync
	cd frontend && pnpm install

backend-check:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest

# Needs `make up` first. POSTGRES_DSN overrides the default local DSN.
migrate:
	cd backend && uv run alembic upgrade head && uv run alembic check

migrate-down:
	cd backend && uv run alembic downgrade -1

frontend-check:
	cd frontend && pnpm lint && pnpm typecheck && pnpm test && pnpm build

check:
	bash scripts/ci-local.sh

compose-config:
	docker compose config --quiet

up:
	docker compose up -d postgres redis temporal temporal-ui falkordb

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

blueprint-validate:
	bash scripts/validate-blueprint.sh

graphify-refresh:
	graphify update .
