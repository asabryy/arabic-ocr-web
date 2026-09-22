"""Support / feedback intake — forwards to the team inbox over SendGrid.

Deliberately accepts anonymous submissions: the people most likely to report that
something is broken are the ones who could not sign up or could not convert.
"""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import send_feedback_email
from app.core.rate_limit import limiter
from app.crud.crud_user import get_user_by_id
from app.db.session import get_db
from app.models.user import User
from app.schemas.feedback import FeedbackIn

router = APIRouter()
logger = logging.getLogger("auth-service.feedback")


def optional_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    """The signed-in user, or None. Never raises — an expired token on a bug report
    should not stop the bug report."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None or payload.get("scope"):
            return None
    except JWTError:
        return None
    return get_user_by_id(db, int(user_id))


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send feedback or a support request",
)
@limiter.limit(settings.FEEDBACK_RATE_LIMIT)
def submit_feedback(
    request: Request,
    body: FeedbackIn,
    current_user: User | None = Depends(optional_current_user),
):
    if body.website:
        # Honeypot tripped. Answer exactly as success so the bot learns nothing.
        logger.info("Discarded honeypot feedback submission")
        return {"status": "accepted"}

    reply_to = current_user.email if current_user else body.email
    if not reply_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An email address is required so we can reply.",
        )

    try:
        send_feedback_email(
            category=body.category,
            message=body.message,
            reply_to=reply_to,
            user_id=current_user.id if current_user else None,
            plan=current_user.plan if current_user else None,
            page=body.page,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception:  # noqa: BLE001 — already logged; surface a retryable error
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not send your message. Please try again, or email us directly.",
        )

    return {"status": "accepted"}
