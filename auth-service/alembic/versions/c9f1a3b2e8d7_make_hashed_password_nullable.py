"""make hashed_password nullable for Google OAuth users

Revision ID: c9f1a3b2e8d7
Revises: b3e9f1a2c4d5
Create Date: 2026-03-18 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9f1a3b2e8d7"
down_revision: Union[str, Sequence[str], None] = "b3e9f1a2c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=False)
