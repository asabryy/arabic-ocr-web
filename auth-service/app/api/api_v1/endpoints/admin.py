"""Operator-only endpoints, guarded by the X-Admin-Key header (see require_admin_key).

Self-serve billing exists now, so this is no longer the only way a plan changes —
it is the way a plan changes *without* Stripe: comped accounts, beta testers, and
corrections. Setting a plan here creates no subscription, so there is nothing to
bill and nothing to cancel, and the grant never expires on its own.

Two things follow from that and are worth remembering when reading revenue numbers:
a comped account is indistinguishable from a paying one in users.plan, and the
Stripe webhook remains the only thing that reacts to an actual payment.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.email import send_plan_changed_email
from app.core.rate_limit import limiter
from app.crud.crud_user import get_user_by_email, get_user_by_id, set_plan
from app.db.session import get_db
from app.schemas.user import PlanUpdate, UserOut

router = APIRouter()
logger = logging.getLogger("auth-service.admin")


@router.get(
    "/users",
    response_model=UserOut,
    summary="Look up a user by email",
)
@limiter.limit("30/minute")
def admin_get_user(
    request: Request,
    email: str = Query(..., description="Exact email address"),
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put(
    "/users/{user_id}/plan",
    response_model=UserOut,
    summary="Set a user's account tier",
)
@limiter.limit("30/minute")
def admin_set_plan(
    request: Request,
    user_id: int,
    body: PlanUpdate,
    db: Session = Depends(get_db),
):
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    old = user.plan
    user = set_plan(db, user, body.plan)
    logger.info("plan changed user_id=%s %s->%s", user_id, old, body.plan)

    if body.notify and old != body.plan:
        try:
            send_plan_changed_email(user.email, body.plan, name=user.name)
        except Exception as ex:  # noqa: BLE001
            # The plan change is already committed and is the thing that matters;
            # a mail failure must not make the caller think it did not happen.
            logger.error("Plan changed for user_id=%s but notification failed: %s", user_id, ex)

    return user
