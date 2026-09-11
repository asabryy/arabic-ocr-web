"""SQLAlchemy Core mirrors of the auth-service tables doc-manager touches.

Deliberately partial (only the columns used here) and Core rather than ORM: the
schema and migrations live in auth-service, so a duplicated ORM model would just
drift. These definitions also serve as DDL for the test database.
"""

from sqlalchemy import Column, Date, Integer, MetaData, String, Table

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("plan", String(16), nullable=False, server_default="free"),
)

usage_daily = Table(
    "usage_daily",
    metadata,
    Column("user_id", Integer, primary_key=True),
    Column("day", Date, primary_key=True),
    Column("pages", Integer, nullable=False, server_default="0"),
)
