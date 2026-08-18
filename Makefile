# RoveQA developer commands. Everything runs in containers: the only host tools
# needed are docker compose and bash.
.PHONY: bootstrap backend-check frontend-check check shell compose-config up down logs blueprint-validate graphify-refresh migrate migrate-down

# Build the images the gates run in. Dependencies come with them.
bootstrap:
	docker compose --profile gates build

backend-check:
	docker compose --profile gates run --rm backend-tests sh -c "ruff check . && ruff format --check . && mypy && pytest -q"

# Needs `make up` first.
migrate:
	docker compose --profile gates run --rm backend-tests sh -c "alembic upgrade head && alembic check"

migrate-down:
	docker compose --profile gates run --rm backend-tests alembic downgrade -1

frontend-check:
	docker compose --profile gates run --rm frontend-tests

# A shell inside the backend toolchain, for iterating on one test.
shell:
	docker compose --profile gates run --rm backend-tests bash

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
