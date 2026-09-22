import logging

from fastapi import APIRouter, Body, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy.orm import Session

from app import metrics
from app.core.config import settings
from app.core.security import create_access_token
from app.crud.crud_user import create_google_user, get_user_by_email
from app.db.session import get_db
from app.schemas.user import Token

router = APIRouter()
logger = logging.getLogger("auth-service.google_auth")


@router.post("", response_model=Token, summary="Sign in / sign up with Google")
def google_auth(
    credential: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured",
        )

    try:
        idinfo = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        metrics.LOGINS.labels(method="google", outcome="failure").inc()
        logger.warning("Invalid Google ID token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )

    # verify_oauth2_token checks signature, audience and expiry — but not whether
    # Google has verified the address. Without this, an identity asserting an
    # unverified address on a custom domain signs in as the existing password
    # account for that address, inheriting its documents and plan.
    if not idinfo.get("email_verified"):
        metrics.LOGINS.labels(method="google", outcome="failure").inc()
        logger.warning("Google ID token for an unverified address (user_id lookup skipped)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This Google account's email address is not verified.",
        )

    email = idinfo["email"]
    name = idinfo.get("name", "")

    user = get_user_by_email(db, email)
    if not user:
        user = create_google_user(db, email=email, name=name)
        metrics.SIGNUPS.labels(method="google").inc()
        logger.info("New user created via Google OAuth: user_id=%s", user.id)
    else:
        # Google has verified the address, so a password account that never
        # confirmed it is confirmed now.
        if not user.email_verified:
            user.email_verified = True
            db.commit()
        logger.info("Existing user signed in via Google OAuth: user_id=%s", user.id)

    access_token = create_access_token(subject=user.id)
    metrics.LOGINS.labels(method="google", outcome="success").inc()
    return {"access_token": access_token, "token_type": "bearer"}
