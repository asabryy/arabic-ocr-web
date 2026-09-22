"""add Stripe billing columns and stripe_events

Revision ID: f1c8d24a7b60
Revises: e4a7b2c9d1f3
Create Date: 2026-09-22 00:00:00.000000

Backward-compatible: every new column is nullable, so the previously deployed
auth-service image keeps working between `alembic upgrade head` and the rollout.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f1c8d24a7b60"
down_revision: str | Sequence[str] | None = "e4a7b2c9d1f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("stripe_subscription_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("subscription_status", sa.String(32), nullable=True))
    op.create_index(
        "ix_users_stripe_customer_id", "users", ["stripe_customer_id"], unique=True
    )
    op.create_table(
        "stripe_events",
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )


def downgrade() -> None:
    op.drop_table("stripe_events")
    op.drop_index("ix_users_stripe_customer_id", table_name="users")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("users", "stripe_customer_id")
