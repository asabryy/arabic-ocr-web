import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import send_verification_email
from app.core.rate_limit import limiter
from app.core.security import create_email_verification_token
from app.crud.crud_user import create_user, get_user_by_email
from app.db.session import get_db
from app.schemas.user import UserCreate, UserOut

router = APIRouter()
logger = logging.getLogger("auth-service.register")


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
@limiter.limit(settings.REGISTER_RATE_LIMIT)
def register_user(
    request: Request,
    user_in: UserCreate,
    db: Session = Depends(get_db),
):
    if get_user_by_email(db, user_in.email):
        logger.info("Registration attempted for existing email: %s", user_in.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        )

    new_user = create_user(db, user_in)
    token = create_email_verification_token(new_user.email)

    try:
        send_verification_email(to_email=new_user.email, token=token)
        logger.info("Verification email sent to %s", new_user.email)
    except Exception as ex:
        logger.error("Failed to send verification email: %s", ex)

    return new_user
