"""phase_17_environment_sessions

A borrowed browser session: who it belongs to, until when, and the sealed bytes.

There is deliberately **no `revoked_at` column**. A revocation stored beside the ciphertext
restores along with it, and the gate this phase has to pass is that revoking survives a
restore. Revocation destroys the key, which lives outside this database and outside any
dump taken from it (ADR 0019).

Revision ID: e5b90a41c7d2
Revises: a3f81c02d7b4
Create Date: 2026-08-22 18:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5b90a41c7d2"
down_revision: str | Sequence[str] | None = "a3f81c02d7b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "environment_sessions",
        sa.Column("session_id", sa.String(length=200), primary_key=True),
        sa.Column("environment_id", sa.String(length=200), nullable=False),
        sa.Column("label", sa.String(length=240), nullable=False),
        sa.Column("established_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("established_by", sa.Text(), nullable=False, server_default=""),
        sa.Column("sealed_state", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(
            ["environment_id"],
            ["environments.environment_id"],
            name="fk_environment_sessions_environment",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until > established_at",
            name="ck_environment_sessions_validity_ordered",
        ),
    )
    # The only query a run makes: this environment's most recent session. Rotating adds a
    # row rather than editing one, so "most recent" is the whole resolution rule and
    # `session_id` breaks the tie for two rotations in the same transaction.
    op.create_index(
        "ix_environment_sessions_env_established",
        "environment_sessions",
        ["environment_id", "established_at", "session_id"],
        postgresql_ops={"established_at": "DESC", "session_id": "DESC"},
    )


def downgrade() -> None:
    op.drop_index("ix_environment_sessions_env_established", table_name="environment_sessions")
    op.drop_table("environment_sessions")
