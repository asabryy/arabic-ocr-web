import logging
from datetime import datetime, timedelta
from typing import Union

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import Settings

settings = Settings()
logger = logging.getLogger("auth-service.security")

# Configure password‑hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against its hashed counterpart.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: Union[str, int]) -> str:
    """
    Create a JWT containing the subject (user ID) and expiration.
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_MINUTES)
    payload = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_email_verification_token(email: str, expires_delta: timedelta = timedelta(hours=1)) -> str:
    """
    Create a scoped JWT for email verification.
    """
    expire = datetime.utcnow() + expires_delta
    payload = {"sub": email, "exp": expire, "scope": "email_verification"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_email_token(token: str) -> Union[str, None]:
    """
    Decode and validate an email‑verification token, returning the email if valid.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("scope") != "email_verification":
            logger.warning("Token has invalid scope: %s", payload.get("scope"))
            return None
        return payload.get("sub")
    except JWTError as ex:
        logger.error("Failed to verify email token: %s", ex)
        return None
