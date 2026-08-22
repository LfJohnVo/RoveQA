"""phase_16_runs_by_project_index

An index for the question the runs list asks: one project's runs, newest first.

`ix_runs_project_id` is dropped rather than kept alongside. A composite whose leading
column is `project_id` answers every lookup the single-column index answered, so keeping
both means paying for two write-time updates to get one read.

Revision ID: a3f81c02d7b4
Revises: c8a15d7be3f0
Create Date: 2026-08-22 12:40:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "a3f81c02d7b4"
down_revision: str | Sequence[str] | None = "c8a15d7be3f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Created before the old one is dropped, so no window exists in which a by-project
    # lookup has no index to use.
    op.create_index(
        "ix_runs_project_created",
        "runs",
        ["project_id", "created_at", "run_id"],
        postgresql_ops={"created_at": "DESC", "run_id": "DESC"},
    )
    op.drop_index("ix_runs_project_id", table_name="runs")


def downgrade() -> None:
    op.create_index("ix_runs_project_id", "runs", ["project_id"])
    op.drop_index("ix_runs_project_created", table_name="runs")
