"""Durable record of every /convert decision.

Why a table and not just the Prometheus counter: ``textara_quota_rejections`` is
retained for 15 days and aggregates to ``(reason, plan)`` only, so a refusal leaves
behind no page count, no document length and no user — exactly the three things
needed to tell whether a limit is set anywhere near where the work is. One row per
decision answers all of them, and keeps answering months later.

The table is attached to ``app.db.tables.metadata`` (rather than getting its own
MetaData) so the test harness's ``metadata.create_all`` picks it up. The schema is
owned by auth-service's Alembic, same as ``users`` and ``usage_daily``; this is the
Core mirror doc-manager writes through.
"""

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    func,
)

from app.db.tables import metadata

# outcome values (kept in sync with auth-service/app/models/conversion_attempt.py)
OUTCOME_ACCEPTED = "accepted"
OUTCOME_DOC_PAGES_EXCEEDED = "doc_pages_exceeded"
OUTCOME_DAILY_PAGES_EXCEEDED = "daily_pages_exceeded"
OUTCOME_ENQUEUE_FAILED = "enqueue_failed"

conversion_attempts = Table(
    "conversion_attempts",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    # Pages this attempt asked for (the slice), not the document's length.
    Column("pages", Integer, nullable=False),
    # The document's length, so a refusal records how big the thing actually was.
    Column("total_pages", Integer, nullable=True),
    Column("start_page", Integer, nullable=True),
    Column("end_page", Integer, nullable=True),
    Column("outcome", String(32), nullable=False),
    Column("plan", String(16), nullable=False),
    Index("ix_conversion_attempts_user_created", "user_id", "created_at"),
    Index("ix_conversion_attempts_outcome_created", "outcome", "created_at"),
)
