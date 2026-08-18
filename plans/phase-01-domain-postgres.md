# Phase 01 — Domain + PostgreSQL Foundation

## Objective
Modelar Projects, Stories y Runs mínimos con repository ports y Postgres adapters.

## Tasks
1. Domain entities/value objects y state transitions de Run.
2. Repository ports.
3. SQLAlchemy models y explicit mappers.
4. Alembic baseline y migraciones pequeñas.
5. Application use cases create/get project, create story, create run draft.
6. Integration tests contra PostgreSQL container.

## Gates
- Domain unit tests cubren run state invariants.
- DB limpia puede migrar a head.
- No ORM imports en Domain/Application.
- Repository contract tests verdes.
## Required skills
- `backend-slice`
- `postgresql`
- `error-handling-patterns` when mapping DB/transaction failures

