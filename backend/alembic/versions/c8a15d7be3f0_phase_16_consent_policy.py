"""phase_16_consent_policy

Whether a run may answer a cookie banner, and how.

`leave` for every existing row and for every new one that does not say otherwise.
Accepting cookies is a legal act performed on somebody's behalf, and a default that did
it would mean every run ever configured had silently opted in on sites their operators do
not own (ADR 0018).

Revision ID: c8a15d7be3f0
Revises: b7e40c93a512
Create Date: 2026-08-21 19:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c8a15d7be3f0"
down_revision: str | Sequence[str] | None = "b7e40c93a512"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "run_policies",
        sa.Column("consent", sa.String(length=20), nullable=False, server_default="leave"),
    )
    # The server default stays. Unlike `criterion_results.source`, where omitting the
    # column would silently claim a story asked for something, omitting this one means
    # "do not touch the banner" — the safe answer, and the one a caller that has never
    # heard of consent should get.
    op.create_check_constraint(
        "ck_run_policies_consent", "run_policies", "consent IN ('leave', 'reject', 'accept')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_run_policies_consent", "run_policies", type_="check")
    op.drop_column("run_policies", "consent")
