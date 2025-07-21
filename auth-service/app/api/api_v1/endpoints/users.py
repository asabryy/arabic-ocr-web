from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.schemas.user import UserOut

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
