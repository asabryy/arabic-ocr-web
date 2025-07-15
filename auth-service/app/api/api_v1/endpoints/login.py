from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, Token
from app.crud.crud_user import get_user_by_email
from app.core.security import verify_password, create_access_token
from app.db.session import get_db
from app.core.rate_limit import limiter

router = APIRouter()

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, user.email)
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(subject=db_user.id)
    return {"access_token": access_token, "token_type": "bearer"}
