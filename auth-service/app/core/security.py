import logging
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger("auth-service.security")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str | int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_MINUTES)
    payload = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_email_verification_token(email: str, expires_delta: timedelta = timedelta(hours=1)) -> str:
    expire = datetime.now(UTC) + expires_delta
    payload = {"sub": email, "exp": expire, "scope": "email_verification"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_password_reset_token(user_id: int, expires_delta: timedelta = timedelta(hours=1)) -> str:
    expire = datetime.now(UTC) + expires_delta
    payload = {"sub": str(user_id), "exp": expire, "scope": "password_reset"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_password_reset_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("scope") != "password_reset":
            return None
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError) as ex:
        logger.error("Failed to verify password reset token: %s", ex)
        return None


def verify_email_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("scope") != "email_verification":
            logger.warning("Token has invalid scope: %s", payload.get("scope"))
            return None
        return payload.get("sub")
    except JWTError as ex:
        logger.error("Failed to verify email token: %s", ex)
        return None
