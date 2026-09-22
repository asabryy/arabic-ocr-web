"""Self-serve billing: send the user to Stripe's hosted Checkout or Customer Portal.

Both routes 404 when STRIPE_SECRET_KEY is unset, so an unconfigured deployment exposes
nothing. Neither route grants Pro — only the webhook does, after Stripe confirms payment.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from stripe import StripeError

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.core.stripe_client import billing_enabled, get_stripe
from app.crud.crud_billing import set_stripe_customer_id
from app.db.session import get_db
from app.models.user import User
from app.schemas.billing import CheckoutSessionOut, PortalSessionOut

router = APIRouter()
logger = logging.getLogger("auth-service.billing")

# Tags sessions in the Dashboard so checkout flows can be compared. Stable by design.
INTEGRATION_IDENTIFIER = "textara_pro_checkout_kwrjhdpz"


def require_billing() -> None:
    if not billing_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


def _ensure_customer(db: Session, user: User) -> str:
    """The user's Stripe customer id, creating the Customer on first upgrade.

    The idempotency key means a double-clicked Upgrade button can't create two
    customers for the same account.
    """
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = get_stripe().v1.customers.create(
        {
            "email": user.email,
            "name": user.name or None,
            # Lets us recover the account from the Stripe side, and survives the
            # customer being looked at in the Dashboard.
            "metadata": {"user_id": str(user.id)},
        },
        {"idempotency_key": f"textara-customer-user-{user.id}"},
    )
    set_stripe_customer_id(db, user, customer.id)
    logger.info("Created Stripe customer %s for user_id=%s", customer.id, user.id)
    return customer.id


@router.post(
    "/checkout-session",
    response_model=CheckoutSessionOut,
    dependencies=[Depends(require_billing)],
    summary="Start a Pro subscription checkout",
)
@limiter.limit("10/minute")
def create_checkout_session(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not settings.STRIPE_PRICE_PRO:
        logger.error("STRIPE_PRICE_PRO is not configured")
        raise HTTPException(status_code=503, detail="Billing is not configured yet.")

    if current_user.plan == "pro":
        # Already paying — the portal is where they change or cancel it.
        raise HTTPException(status_code=409, detail="You are already on the Pro plan.")

    customer_id = _ensure_customer(db, current_user)
    base = settings.FRONTEND_BASE_URL.rstrip("/")

    try:
        session = get_stripe().v1.checkout.sessions.create(
            {
                "mode": "subscription",
                "customer": customer_id,
                "line_items": [{"price": settings.STRIPE_PRICE_PRO, "quantity": 1}],
                # Two independent ways back to the account, because this is what the
                # webhook keys off when the customer lookup is somehow missing.
                "client_reference_id": str(current_user.id),
                "metadata": {"user_id": str(current_user.id)},
                "subscription_data": {"metadata": {"user_id": str(current_user.id)}},
                "success_url": f"{base}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
                "cancel_url": f"{base}/pricing",
                "allow_promotion_codes": True,
                "integration_identifier": INTEGRATION_IDENTIFIER,
            }
        )
    except StripeError as ex:
        logger.error("Checkout session failed for user_id=%s: %s", current_user.id, ex)
        raise HTTPException(status_code=502, detail="Could not reach Stripe. Please try again.")

    return CheckoutSessionOut(url=session.url)


@router.post(
    "/portal-session",
    response_model=PortalSessionOut,
    dependencies=[Depends(require_billing)],
    summary="Open the Stripe Customer Portal",
)
@limiter.limit("10/minute")
def create_portal_session(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No billing account yet.")

    base = settings.FRONTEND_BASE_URL.rstrip("/")
    try:
        session = get_stripe().v1.billing_portal.sessions.create(
            {"customer": current_user.stripe_customer_id, "return_url": f"{base}/settings"}
        )
    except StripeError as ex:
        logger.error("Portal session failed for user_id=%s: %s", current_user.id, ex)
        raise HTTPException(status_code=502, detail="Could not reach Stripe. Please try again.")

    return PortalSessionOut(url=session.url)
