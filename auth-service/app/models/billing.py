from sqlalchemy import Column, DateTime, String, func

from app.db.base import Base


class StripeEvent(Base):
    """One row per webhook event we've applied.

    Stripe re-delivers events (retries, and `customer.subscription.updated` fires on
    every lifecycle nudge), so the handler claims the id and applies the plan change in
    a single transaction: a duplicate hits the primary-key constraint and is skipped,
    and a handler that raises rolls the claim back so Stripe's retry can succeed.
    """

    __tablename__ = "stripe_events"

    event_id = Column(String(255), primary_key=True)
    event_type = Column(String(100), nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
