import os
from datetime import datetime, timedelta
from typing import Union
from jose import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(subject: Union[str, int]) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_email_verification_token(email: str, expires_delta: timedelta = timedelta(hours=1)) -> str:
    expire = datetime.utcnow() + expires_delta
    payload = {
        "sub": email,
        "exp": expire,
        "scope": "email_verification"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_email_token(token: str) -> Union[str, None]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("scope") != "email_verification":
            return None
        return payload.get("sub")
    except jwt.JWTError:
        return None