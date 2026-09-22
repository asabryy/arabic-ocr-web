"""Stripe webhook — the only thing in this codebase that grants or revokes Pro.

Public by necessity (Stripe calls it unauthenticated), so the signature check is the
whole security boundary: an unsigned or mis-signed body is rejected before it can touch
a user row. Signature verification needs the *raw* body, so this handler reads
`await request.body()` and never lets FastAPI parse the payload first.
"""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session
from stripe import SignatureVerificationError, Webhook

from app.core.config import settings
from app.core.stripe_client import get_stripe
from app.crud.crud_billing import get_user_by_stripe_customer_id
from app.db.session import get_db
from app.services import billing

router = APIRouter()
logger = logging.getLogger("auth-service.webhook")


def _as_dict(value):
    """Deep-convert Stripe SDK objects to plain dicts.

    StripeObject is neither a dict nor iterable — `.get()` and `dict()` both raise on
    it — and `to_dict()` only unwraps the top level. Everything downstream works in
    plain dicts so the logic stays testable against literal payloads.
    """
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if isinstance(value, dict):
        return {k: _as_dict(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_as_dict(v) for v in value]
    return value


def _subscription_from(event_type: str, obj: dict) -> dict | None:
    """The Subscription payload an event refers to.

    `customer.subscription.*` carries it directly. `checkout.session.completed` only
    carries the subscription *id*, so we fetch it — that round trip is also what
    confirms the session actually resulted in a live subscription.
    """
    if event_type.startswith("customer.subscription."):
        return obj

    # checkout.session.completed
    if obj.get("mode") != "subscription" or obj.get("payment_status") == "unpaid":
        return None
    sub_id = obj.get("subscription")
    if not sub_id:
        return None
    return _as_dict(get_stripe().v1.subscriptions.retrieve(sub_id))


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    summary="Stripe event receiver",
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.error("Webhook received but STRIPE_WEBHOOK_SECRET is not set")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    payload = await request.body()
    try:
        event = Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, SignatureVerificationError) as ex:
        logger.warning("Rejected webhook: %s", ex)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    event_type = event["type"]
    event_id = event["id"]

    if event_type == "invoice.payment_failed":
        # Informational: Smart Retries is still working on it, and the subscription's
        # own status change is what actually moves the plan. Logged so a spike is visible.
        obj = _as_dict(event["data"]["object"])
        logger.warning(
            "Payment failed for customer=%s invoice=%s — Stripe will retry",
            obj.get("customer"), obj.get("id"),
        )
        return {"status": "noted"}

    if event_type not in billing.HANDLED_EVENTS:
        return {"status": "ignored"}

    if not billing.claim_event(db, event_id, event_type):
        logger.info("Duplicate event %s (%s) — already applied", event_id, event_type)
        return {"status": "duplicate"}

    obj = _as_dict(event["data"]["object"])
    subscription = _subscription_from(event_type, obj)
    if subscription is None:
        db.commit()  # keep the claim: nothing to do for this one
        return {"status": "ignored"}

    customer_id = subscription.get("customer")
    user = get_user_by_stripe_customer_id(db, customer_id) if customer_id else None
    if user is None:
        # Fall back to the id we stamped on the way out. Covers a customer created
        # outside this flow, or a row that lost its customer id.
        user_id = (subscription.get("metadata") or {}).get("user_id") or obj.get(
            "client_reference_id"
        )
        if user_id:
            from app.crud.crud_user import get_user_by_id

            user = get_user_by_id(db, int(user_id))
            if user is not None and customer_id and not user.stripe_customer_id:
                user.stripe_customer_id = customer_id

    if user is None:
        logger.error(
            "No user for customer=%s on %s — acknowledging so Stripe stops retrying",
            customer_id, event_type,
        )
        db.commit()
        return {"status": "no_user"}

    plan = billing.apply_subscription(db, user, subscription)
    db.commit()  # event claim + plan change land together
    return {"status": "ok", "plan": plan}
