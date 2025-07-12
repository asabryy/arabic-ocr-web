from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# explicitly import the Pydantic models you need:
from app.schemas.user import UserCreate, Token

# explicit CRUD and security imports:
from app.crud.crud_user import get_user_by_email
from app.core.security import verify_password, create_access_token
from app.db.session import get_db

router = APIRouter()

@router.post("/login", response_model=Token)
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, user.email)
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(subject=db_user.id)
    return {"access_token": access_token, "token_type": "bearer"}
