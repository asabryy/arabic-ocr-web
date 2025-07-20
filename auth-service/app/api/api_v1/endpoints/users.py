# app/api/api_v1/endpoints/users.py

from fastapi import APIRouter, Depends
from app.schemas.user      import UserOut
from app.core.dependencies import get_current_user

router = APIRouter()

@router.get("/me", response_model=UserOut, summary="Get the current user")
def read_users_me(current_user = Depends(get_current_user)):
    return current_user
