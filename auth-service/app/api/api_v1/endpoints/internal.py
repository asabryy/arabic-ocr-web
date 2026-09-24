"""Service-to-service endpoints. Not part of the public API.

Today this carries one route: the doc-manager worker telling us a conversion
finished so the user can be emailed about it. The worker knows the outcome; only
auth-service knows the address and holds the mail credentials.

Why an endpoint and not a direct Resend call from the worker: doc-manager's mirror
of ``users`` is deliberately partial (id and plan — no email column), so a worker
that sent its own mail would need both a second copy of the templates and a copy of
the provider key, in a process that talks to an untrusted PDF pipeline. Keeping the
mail seam in one service keeps both out of it.

Why this is not an open relay, which is the obvious risk of "an endpoint that sends
email": the payload carries a **user id**, never an address. The recipient is looked
up here, from our own table. Even with the shared key in hand, the worst an attacker
can do is mail our own users a "your conversion finished" notice — there is no field
to point it at an arbitrary inbox.

Access control, defence in depth:
  1. INTERNAL_API_KEY unset => every route 404s, so an unconfigured or public-facing
     deployment exposes nothing (same posture as /admin and /billing).
  2. A constant-time comparison against the X-Internal-Key header.
  3. A per-IP rate limit, so a leaked key cannot be used to mail a user in a loop.
The intended topology is cluster-internal only: this path should not be routed by
the public ingress at all. The key is the belt for that braces.
"""
import hmac
import logging
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import send_conversion_complete_email
from app.core.rate_limit import limiter
from app.crud.crud_user import get_user_by_id
from app.db.session import get_db

router = APIRouter()
logger = logging.getLogger("auth-service.internal")

# Looked up per call rather than captured at import, so tests can set it and a
# rotation takes effect without a restart. os.environ wins over the settings value
# so the two stay consistent when something writes the env directly.
INTERNAL_KEY_ENV = "INTERNAL_API_KEY"


def _internal_key() -> str:
    return os.getenv(INTERNAL_KEY_ENV) or settings.INTERNAL_API_KEY


def require_internal_key(
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
) -> None:
    if not _internal_key():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not x_internal_key or not hmac.compare_digest(x_internal_key, _internal_key()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


class ConversionFinished(BaseModel):
    """What the worker knows when a task ends. No email address by design."""

    user_id: int
    filename: str = Field(min_length=1, max_length=255)
    outcome: str = Field(pattern="^(done|failed)$")
    pages: int | None = Field(default=None, ge=0, le=10_000)
    duration_seconds: float | None = Field(default=None, ge=0)
    # Why it failed, for the wording of the message: no_text | error.
    reason: str | None = Field(default=None, max_length=64)


@router.post(
    "/conversion",
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
    summary="Worker callback: a conversion finished (internal only)",
    dependencies=[Depends(require_internal_key)],
)
@limiter.limit("120/minute")
def conversion_finished(
    request: Request,
    body: ConversionFinished,
    db: Session = Depends(get_db),
):
    user = get_user_by_id(db, body.user_id)
    if user is None or not user.email:
        # A deleted account between "conversion started" and "conversion finished" is
        # a race, not an outage. 202 so the worker does not count it as a failure.
        logger.warning("No user %s to notify about %s", body.user_id, body.outcome)
        return {"status": "skipped", "reason": "unknown_user"}

    try:
        send_conversion_complete_email(
            user.email,
            filename=body.filename,
            outcome=body.outcome,
            pages=body.pages,
            duration_seconds=body.duration_seconds,
            reason=body.reason,
        )
    except Exception:  # noqa: BLE001 — already logged and counted inside _send
        # Surface it: the worker counts the failure, and the send is already on
        # textara_emails_total{kind="conversion",outcome="failed"}.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not send the notification.",
        )

    return {"status": "sent"}
