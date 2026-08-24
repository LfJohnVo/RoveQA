"""phase_16_observed_failures

A durable home for what the browser saw go wrong that belongs to no acceptance
criterion.

Until now every findings surface in the schema was keyed to a `criterion_id`:
`criterion_results` requires one, and so do `failure_clusters` and its members. A
JavaScript exception or an image answering 404 is first-class QA signal on any site and
had no row it could occupy — so it was collected by the Playwright adapter, carried as
far as `EpisodeResult.page_problems`, and dropped. ADR 0015 said the run report would
gain observed failures; this is the column that lets it.

One row per problem, not an array per run. The grain will get finer — a site sweep needs
to say which page each one came from — and a column added to a narrow table is a smaller
change than unpacking a JSONB array afterwards.

`detail` is already redacted when it arrives: a failed-request URL carries tokens in its
query string and a console message can print one. The cleaning happens in the adapter,
beside the code that knows which of the two it is looking at.

Revision ID: d41f7c2a9e08
Revises: 8b3ac8f35fa4
Create Date: 2026-08-21 17:52:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d41f7c2a9e08"
down_revision: str | Sequence[str] | None = "8b3ac8f35fa4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "observed_failures",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=200), nullable=False),
        sa.Column("episode_index", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "kind IN ('console_error', 'failed_request')", name="ck_observed_failures_kind"
        ),
    )
    op.create_index("ix_observed_failures_run", "observed_failures", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_observed_failures_run", table_name="observed_failures")
    op.drop_table("observed_failures")
