from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud import crud_user
from app.core.security import verify_email_token
from starlette.responses import JSONResponse

router = APIRouter()

@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    email = verify_email_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = crud_user.get_user_by_email(db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.email_verified:
        return JSONResponse(content={"message": "Email already verified"})

    user.email_verified = True
    db.commit()

    return JSONResponse(content={"message": "Email verified successfully!"})
