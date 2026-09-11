from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    UPLOAD_DIR: str = "./uploads"

    # JWT — must match auth-service values to verify tokens
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    # RabbitMQ
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_url: str | None = None
    rabbitmq_queue: str = "ocr_tasks"
    rabbitmq_user: str = "guest"
    rabbitmq_pass: str = "guest"
    rabbitmq_uri: str | None = None

    # OCR
    # OCR_BACKEND: "gemini" (prod — hosted Google Gemini vision) or
    # "http" (local dev — POSTs the PDF to a self-hosted OCR server at OCR_HTTP_URL).
    OCR_BACKEND: str = "gemini"
    OCR_HTTP_URL: str = "http://localhost:8002"
    OCR_DPI: int = 150
    OCR_MAX_RETRIES: int = 5

    # Google Gemini (hosted OCR)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-latest"

    # Database — shared with auth-service (reads users.plan, reads/writes usage_daily).
    # Empty => quota-gated endpoints (/convert, /usage) return 503.
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 2
    DB_MAX_OVERFLOW: int = 3

    # Plan limits (pages). Enforced at /convert; surfaced by /usage.
    PLAN_FREE_DAILY_PAGES: int = 10
    PLAN_FREE_MAX_DOC_PAGES: int = 10
    PLAN_PRO_DAILY_PAGES: int = 300
    PLAN_PRO_MAX_DOC_PAGES: int = 100

    # Anonymous trial (landing page): first N pages only, rate-limited per client IP.
    TRIAL_MAX_PAGES: int = 1
    TRIAL_RATE_LIMIT: str = "3/day"
    TRIAL_MAX_UPLOAD_MB: int = 10

    # Header carrying the real client IP behind ingress-nginx (first value is used).
    # Switch to "CF-Connecting-IP" if Cloudflare proxying is enabled.
    CLIENT_IP_HEADER: str = "X-Forwarded-For"

    # Storage
    STORAGE_BACKEND: str = "local"

    # Cloudflare R2 — optional, only required when STORAGE_BACKEND=r2
    R2_ENDPOINT_URL: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""

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
