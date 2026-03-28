"""remove is_active column

Revision ID: b3e9f1a2c4d5
Revises: d7911c4ffe4c
Create Date: 2026-03-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3e9f1a2c4d5"
down_revision: Union[str, Sequence[str], None] = "d7911c4ffe4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "is_active")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=True),
    )
