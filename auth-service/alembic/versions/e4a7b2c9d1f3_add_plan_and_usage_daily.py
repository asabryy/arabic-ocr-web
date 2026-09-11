"""add users.plan, users.created_at and usage_daily

Revision ID: e4a7b2c9d1f3
Revises: c9f1a3b2e8d7
Create Date: 2026-09-11 00:00:00.000000

Backward-compatible: both new columns carry server defaults, so the previously
deployed auth-service image keeps working between `alembic upgrade head` and the
rollout. Existing rows get created_at = migration time (true dates were never
recorded before this migration).
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e4a7b2c9d1f3"
down_revision: str | Sequence[str] | None = "c9f1a3b2e8d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("plan", sa.String(16), nullable=False, server_default="free"),
    )
    op.add_column(
        "users",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "usage_daily",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("pages", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "day"),
    )


def downgrade() -> None:
    op.drop_table("usage_daily")
    op.drop_column("users", "created_at")
    op.drop_column("users", "plan")
