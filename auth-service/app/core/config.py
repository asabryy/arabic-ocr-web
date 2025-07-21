# auth-service/app/core/config.py

from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """
    Application configuration, loaded once from environment variables.
    Any extra environment variables not listed here will be ignored.
    """
    # Tell Pydantic to read .env and ignore any extras
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core settings
    DATABASE_URL: str
    SECRET_KEY: str

    # JWT
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRES_MINUTES: int = 30

    # Email (SendGrid)
    SENDGRID_API_KEY: str
    EMAIL_FROM: str = "noreply@example.com"

    # Frontend (for verification links)
    FRONTEND_BASE_URL: str = "http://localhost:3000"

    # Rate limits
    REGISTER_RATE_LIMIT: str = "5/minute"
    LOGIN_RATE_LIMIT: str = "5/minute"
