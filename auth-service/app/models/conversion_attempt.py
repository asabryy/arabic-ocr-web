from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)

from app.db.base import Base


class ConversionAttempt(Base):
    """One row per /convert decision, written by doc-manager.

    Owned here so the schema/migration has a single source of truth (same
    arrangement as ``usage_daily``). Prometheus only keeps 15 days of
    ``(reason, plan)`` counts; this keeps the page counts and the user behind
    every acceptance and every refusal.
    """

    __tablename__ = "conversion_attempts"

    # SQLite (used by the auth-service test harness) only auto-increments INTEGER.
    id = Column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    pages = Column(Integer, nullable=False)
    total_pages = Column(Integer, nullable=True)
    start_page = Column(Integer, nullable=True)
    end_page = Column(Integer, nullable=True)
    # accepted | doc_pages_exceeded | daily_pages_exceeded | enqueue_failed
    outcome = Column(String(32), nullable=False)
    plan = Column(String(16), nullable=False)

    __table_args__ = (
        Index("ix_conversion_attempts_user_created", "user_id", "created_at"),
        Index("ix_conversion_attempts_outcome_created", "outcome", "created_at"),
    )
