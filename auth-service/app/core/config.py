# auth-service/app/core/config.py

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    # Core
    DATABASE_URL: str
    SECRET_KEY: str

    # JWT
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRES_MINUTES: int = 30

    # Email (SendGrid) — optional; email sending is skipped if empty
    SENDGRID_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@textara.app"

    # Frontend (for verification links)
    FRONTEND_BASE_URL: str = "https://textara.app"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""

    # Rate limits
    REGISTER_RATE_LIMIT: str = "5/minute"
    LOGIN_RATE_LIMIT: str = "5/minute"

    # CORS — comma-separated list of allowed origins
    CORS_ORIGINS: list[str] = [
        "https://textara.netlify.app",
        "https://textara.app",
        "https://www.textara.app",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()
