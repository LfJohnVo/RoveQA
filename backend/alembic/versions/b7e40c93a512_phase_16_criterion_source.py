"""phase_16_criterion_source

Where a criterion came from: the run's plan, or the universal page sweep every run now
applies to every page it observes (ADR 0017).

Both are genuinely criteria — a thing checked, with an outcome — so they share this table
and the same verdict machinery. What they do not share is provenance, and a reader seeing
a `criteria` array must never confuse "the story asked for this" with "the sweep checks
this on every page". The criterion ids are namespaced `page:<route>`, but a prefix is a
convention where this is a fact.

Backfilled to `plan`, which is what every existing row means: before this, the only way a
criterion result existed was a plan assertion.

Revision ID: b7e40c93a512
Revises: d41f7c2a9e08
Create Date: 2026-08-21 18:41:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7e40c93a512"
down_revision: str | Sequence[str] | None = "d41f7c2a9e08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Added with a server default so existing rows get `plan` without a separate backfill
    # pass, then dropped: a default that stays would let a future insert omit the column
    # and silently claim a story asked for something.
    op.add_column(
        "criterion_results",
        sa.Column("source", sa.String(length=20), nullable=False, server_default="plan"),
    )
    op.alter_column("criterion_results", "source", server_default=None)
    op.create_check_constraint(
        "ck_criterion_results_source", "criterion_results", "source IN ('plan', 'sweep')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_criterion_results_source", "criterion_results", type_="check")
    op.drop_column("criterion_results", "source")
