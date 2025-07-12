from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud
from app.schemas import user
from app.db.session import get_db
from app.core.security import create_email_verification_token

router = APIRouter()

@router.post("/register", response_model=user.UserOut)
def register_user(user: user.UserCreate, db: Session = Depends(get_db)):
    if crud.crud_user.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user = crud.crud_user.create_user(db, user)

    # Create verification token
    token = create_email_verification_token(user.email)

    # Simulate sending email by printing the link
    verification_url = f"http://localhost:8000/api/v1/verify-email?token={token}"
    print(f"🔗 Email verification link (simulate send): {verification_url}")

    return db_user
