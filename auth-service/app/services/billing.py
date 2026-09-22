"""Subscription state -> account tier.

All the branching that decides whether someone is Pro lives here, free of FastAPI and
of the Stripe SDK, so it can be tested against plain dicts.
"""
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.billing import StripeEvent
from app.models.user import User

logger = logging.getLogger("auth-service.billing")

# Statuses that keep a paid tier. `past_due` is deliberately included: Stripe's Smart
# Retries keep attempting a failed renewal for days, and yanking access on the first
# failed charge punishes people whose card simply expired. Stripe moves the
# subscription to `canceled` or `unpaid` once recovery gives up, and that revokes here.
ACTIVE_STATUSES = frozenset({"active", "trialing", "past_due"})

# The events we act on. Everything else Stripe sends is acknowledged and ignored.
HANDLED_EVENTS = frozenset(
    {
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }
)


def _product_of(subscription: dict) -> str | None:
    """The product id on a subscription's first line item, if the payload carries it."""
    items = (subscription.get("items") or {}).get("data") or []
    if not items:
        return None
    price = items[0].get("price") or {}
    product = price.get("product")
    # `product` is an id unless the caller expanded it into an object.
    return product.get("id") if isinstance(product, dict) else product


def plan_for_subscription(subscription: dict) -> str:
    """"pro" | "free" for a Stripe Subscription payload.

    Gates on the *product*, not the price, so changing what Pro costs means creating a
    new Price in the Dashboard rather than shipping code.
    """
    if subscription.get("status") not in ACTIVE_STATUSES:
        return "free"
    wanted = settings.STRIPE_PRODUCT_PRO
    if wanted:
        product = _product_of(subscription)
        if product and product != wanted:
            logger.info("Subscription for unrecognised product %s — not granting Pro", product)
            return "free"
    return "pro"


def claim_event(db: Session, event_id: str, event_type: str) -> bool:
    """Reserve an event id. False if we've already applied this event.

    Caller must commit: the claim and the plan change share one transaction, so a
    handler that raises rolls back the claim too and Stripe's retry can still land.
    """
    db.add(StripeEvent(event_id=event_id, event_type=event_type))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return False
    return True


def apply_subscription(db: Session, user: User, subscription: dict) -> str:
    """Write a subscription's state onto the user row. Returns the resulting plan.

    Does not commit — the webhook handler commits once, together with the event claim.
    """
    plan = plan_for_subscription(subscription)
    status = subscription.get("status")
    previous = user.plan

    user.plan = plan
    user.subscription_status = status
    sub_id = subscription.get("id")
    if plan == "free" and user.stripe_subscription_id == sub_id:
        # Subscription ended; drop the pointer but keep the customer id so a
        # re-subscribe reuses their billing history rather than making a second customer.
        user.stripe_subscription_id = None
    elif sub_id:
        user.stripe_subscription_id = sub_id

    if previous != plan:
        logger.info(
            "plan changed user_id=%s %s->%s (subscription=%s status=%s)",
            user.id, previous, plan, sub_id, status,
        )
    return plan
