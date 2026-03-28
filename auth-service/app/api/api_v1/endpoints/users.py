from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.crud.crud_user import update_user
from app.db.session import get_db
from app.schemas.user import UserOut, UserUpdate

router = APIRouter()


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get the current authenticated user",
)
def read_current_user(
    current_user=Depends(get_current_user),
):
    """
    Return details for the current user as identified by their JWT.
    """
    return current_user

@router.put(
    "/me",
    response_model=UserOut,
    summary="Update the current user's profile",
)
def update_current_user(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    updated_user = update_user(db, current_user, user_in)
    return updated_user
