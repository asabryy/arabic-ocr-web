from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, schemas
from app.db.session import get_db

router = APIRouter()

@router.post("/register", response_model=schemas.user.UserOut)
def register_user(user: schemas.user.UserCreate, db: Session = Depends(get_db)):
    if crud.crud_user.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.crud_user.create_user(db, user)