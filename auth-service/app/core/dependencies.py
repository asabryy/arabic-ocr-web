import hmac
import logging

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.crud_user import get_user_by_id
from app.db.session import get_db

logger = logging.getLogger("auth-service.dependencies")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/v1/token")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        # Email-verification / password-reset tokens share the signing key but carry
        # a "scope" claim; they must never be accepted as access tokens.
        if user_id is None or payload.get("scope"):
            raise credentials_exception
    except JWTError as ex:
        logger.warning("Token decode error: %s", ex)
        raise credentials_exception

    user = get_user_by_id(db, int(user_id))
    if user is None:
        raise credentials_exception

    return user


def require_admin_key(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> None:
    """Guard for /admin routes. Disabled entirely (404) when no key is configured,
    so an unconfigured deployment exposes nothing."""
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not x_admin_key or not hmac.compare_digest(x_admin_key, settings.ADMIN_API_KEY):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
