"""add conversion_attempts

Revision ID: a4d2f7e91b03
Revises: f1c8d24a7b60
Create Date: 2026-09-24 00:00:00.000000

Purely additive: a new table nobody reads yet, so the currently deployed images
keep working between `alembic upgrade head` and the rollout.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a4d2f7e91b03"
down_revision: str | Sequence[str] | None = "f1c8d24a7b60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversion_attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Pages this attempt asked for; total_pages is the document's length, so a
        # refusal records how long the document actually was.
        sa.Column("pages", sa.Integer(), nullable=False),
        sa.Column("total_pages", sa.Integer(), nullable=True),
        sa.Column("start_page", sa.Integer(), nullable=True),
        sa.Column("end_page", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("plan", sa.String(16), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversion_attempts_user_created",
        "conversion_attempts",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_conversion_attempts_outcome_created",
        "conversion_attempts",
        ["outcome", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversion_attempts_outcome_created", table_name="conversion_attempts")
    op.drop_index("ix_conversion_attempts_user_created", table_name="conversion_attempts")
    op.drop_table("conversion_attempts")
