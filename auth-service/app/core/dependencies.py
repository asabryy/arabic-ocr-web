import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_db
from app.crud.crud_user import get_user_by_id

settings = Settings()
logger = logging.getLogger("auth-service.dependencies")

# Matches the token endpoint path defined in login.py
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/v1/token")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Decode JWT and retrieve the corresponding user, or fail with 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError as ex:
        logger.warning("Token decode error: %s", ex)
        raise credentials_exception

    user = get_user_by_id(db, int(user_id))
    if user is None:
        raise credentials_exception

    return user
