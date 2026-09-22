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
    # Where support/feedback submissions are forwarded.
    SUPPORT_EMAIL: str = "support@textara.app"
    FEEDBACK_RATE_LIMIT: str = "3/hour"

    # Frontend (for verification links)
    FRONTEND_BASE_URL: str = "https://textara.app"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""

    # Rate limits
    REGISTER_RATE_LIMIT: str = "5/minute"
    LOGIN_RATE_LIMIT: str = "5/minute"
    # Header carrying the real client IP behind the ingress (first value is used).
    # Switch to "CF-Connecting-IP" if Cloudflare proxying is enabled.
    CLIENT_IP_HEADER: str = "X-Forwarded-For"

    # Admin API — empty disables the /admin routes (they return 404)
    ADMIN_API_KEY: str = ""

    # ── Stripe billing ────────────────────────────────────────────────────────
    # Empty STRIPE_SECRET_KEY disables the /billing routes (they return 404), so an
    # unconfigured deployment exposes nothing — same posture as the admin API above.
    # Prefer a restricted key (rk_...) scoped to Checkout/Customers/Billing Portal.
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    # Price the Pro tier checks out with (price_...). Created in the Stripe Dashboard.
    STRIPE_PRICE_PRO: str = ""
    # Optional product gate (prod_...). When set, only a subscription to this product
    # grants Pro — so repricing means a new Price, not a code change. When empty, any
    # live subscription grants Pro.
    STRIPE_PRODUCT_PRO: str = ""
    # Pin the API version so Stripe-side upgrades can't change payload shapes under us.
    STRIPE_API_VERSION: str = "2026-08-26.dahlia"

    # CORS — comma-separated list of allowed origins
    CORS_ORIGINS: list[str] = [
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
