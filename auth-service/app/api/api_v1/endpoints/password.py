import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.email import send_password_reset_email
from app.core.security import (
    create_password_reset_token,
    hash_password,
    verify_password_reset_token,
)
from app.crud.crud_user import get_user_by_email, get_user_by_id
from app.db.session import get_db
from app.schemas.user import ForgotPasswordRequest, ResetPasswordRequest

router = APIRouter()
logger = logging.getLogger("auth-service.password")

_RESET_SENT_MSG = "If that email is registered, a reset link has been sent."


@router.post("/forgot-password", summary="Request a password reset email")
def forgot_password(
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, body.email)
    if user:
        token = create_password_reset_token(user.id)
        try:
            send_password_reset_email(user.email, token)
        except Exception:
            logger.error("Failed to send reset email to %s", body.email)
    # Always return the same message to avoid revealing whether the email exists
    return {"message": _RESET_SENT_MSG}


@router.post("/reset-password", summary="Set a new password using a reset token")
def reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters.",
        )

    user_id = verify_password_reset_token(body.token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token.",
        )

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.hashed_password = hash_password(body.new_password)
    db.commit()
    logger.info("Password reset successfully for user %d", user_id)
    return {"message": "Password reset successfully. You can now log in."}
