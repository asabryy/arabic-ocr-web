from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import verify_email_token
from app.crud.crud_user import get_user_by_email
from app.db.session import get_db

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
