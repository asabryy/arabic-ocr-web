from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.core.security import create_access_token
from app.schemas.user import Token

router = APIRouter()


@router.post("", response_model=Token, summary="Renew an access token")
def refresh_token(current_user=Depends(get_current_user)):
    new_token = create_access_token(subject=current_user.id)
    return {"access_token": new_token, "token_type": "bearer"}
