from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserOut
from app.crud.crud_user import get_user_by_email, create_user
from app.db.session import get_db
from app.core.security import create_email_verification_token
from app.core.rate_limit import limiter
from app.core.email import send_verification_email

router = APIRouter()

@router.post("/register", response_model=UserOut)
@limiter.limit("5/minute")
def register_user(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user = create_user(db, user)
    token = create_email_verification_token(user.email)
    send_verification_email(user.email, token)

    return db_user
