import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.rate_limit import limiter
from app.core.security import verify_password, create_access_token
from app.crud.crud_user import get_user_by_email
from app.db.session import get_db
from app.schemas.user import Token

router = APIRouter()
settings = Settings()
logger = logging.getLogger("auth-service.login")


@router.post(
    "",
    response_model=Token,
    summary="Obtain an OAuth2 password‑grant token",
)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Validate user credentials and return a JWT access token.
    """
    user = get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning("Invalid login attempt for user: %s", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.email_verified:
        logger.info("Login attempt before email verification: %s", user.email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address has not been verified",
        )

    access_token = create_access_token(subject=user.id)
    logger.info("User %s authenticated successfully", user.email)
    return {"access_token": access_token, "token_type": "bearer"}
