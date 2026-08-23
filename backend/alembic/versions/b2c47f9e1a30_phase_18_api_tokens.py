"""phase_18_api_tokens

What a CI job presents, stored as a hash and never as itself.

The unique index on `fingerprint` is the lookup path, not decoration: every authenticated
request hashes what it was given and finds the row by that, so it has to be one indexed
probe. It is also a correctness constraint — two rows sharing a fingerprint would mean the
CSPRNG repeated itself, and the database should say so rather than accept it (ADR 0020).

Revision ID: b2c47f9e1a30
Revises: e5b90a41c7d2
Create Date: 2026-08-23 06:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c47f9e1a30"
down_revision: str | Sequence[str] | None = "e5b90a41c7d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_tokens",
        sa.Column("token_id", sa.String(length=200), primary_key=True),
        sa.Column("project_id", sa.String(length=200), nullable=False),
        sa.Column("label", sa.String(length=240), nullable=False),
        # Exactly the width of a hex SHA-256. A value that is not one is a bug, not a
        # token, and the column says so.
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("issued_by", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.project_id"],
            name="fk_api_tokens_project",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("fingerprint", name="uq_api_tokens_fingerprint"),
    )
    op.create_index("ix_api_tokens_project", "api_tokens", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_api_tokens_project", table_name="api_tokens")
    op.drop_table("api_tokens")
