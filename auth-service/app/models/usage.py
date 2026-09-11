from sqlalchemy import Column, Date, ForeignKey, Integer

from app.db.base import Base


class UsageDaily(Base):
    """Pages consumed per user per UTC day. Written by doc-manager (atomic reserve);
    owned here so the schema/migration has a single source of truth."""

    __tablename__ = "usage_daily"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    day = Column(Date, primary_key=True)
    pages = Column(Integer, nullable=False, server_default="0")
