from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.email import send_verification_email
from app.core.rate_limit import limiter
from app.core.security import create_email_verification_token, verify_email_token
from app.crud.crud_user import get_user_by_email
from app.db.session import get_db
from app.schemas.user import UserOut

router = APIRouter()


@router.get(
    "",
    summary="Verify a user's email address",
)
def verify_email(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Decode and validate the email‑verification token, then mark the user.
    """
    email = verify_email_token(token)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.email_verified:
        return {"message": "Email already verified"}

    user.email_verified = True
    db.commit()
    return {"message": "Email verified successfully"}


@router.post(
    "/resend",
    response_model=UserOut,
    summary="Resend verification email to current user",
)
@limiter.limit("1 per 300 seconds")
def resend_verification_email(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified",
        )

    token = create_email_verification_token(current_user.email)
    try:
        send_verification_email(to_email=current_user.email, token=token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        )

    return current_user
