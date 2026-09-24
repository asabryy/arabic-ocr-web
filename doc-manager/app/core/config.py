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
    # Rate-limit (429) backoff: honor Google's suggested delay, capped; bounded attempts.
    OCR_429_MAX_RETRIES: int = 6
    OCR_429_MAX_DELAY_S: float = 60.0
    OCR_429_DEFAULT_DELAY_S: float = 10.0  # per attempt, when no hint is given
    # Pricing used for the estimated-cost metric (USD per 1M tokens)
    GEMINI_PRICE_INPUT_USD_PER_M: float = 0.75
    GEMINI_PRICE_OUTPUT_USD_PER_M: float = 3.75

    # DOCX output. The font is written to w:ascii/w:hAnsi AND to w:cs (complex script) —
    # Word lays Arabic out from the complex-script side, so a font set only on the Latin
    # side silently falls back to Word's default. Same for the size (w:sz + w:szCs).
    DOCX_FONT: str = "Arial"
    DOCX_FONT_SIZE_PT: float = 12.0
    DOCX_FOOTNOTE_SIZE_PT: float = 9.0

    # Worker /metrics endpoint (scraped by Prometheus via pod annotations); 0 disables
    WORKER_METRICS_PORT: int = 9100

    # ── Blank-output guard ────────────────────────────────────────────────────
    # An image-only scan makes the OCR pipeline return empty page text, and an
    # empty DOCX is still a ~36KB valid file — so the task used to be reported as
    # "done" with the user's quota spent and not one readable character inside.
    # Below this many visible non-whitespace characters *in the whole document*
    # the conversion is failed and refunded instead. Ten characters is roughly two
    # Arabic words: every page a human would call "converted" clears it, while the
    # single-glyph artifacts a blank scan produces (".", "-", "…", a stray digit)
    # do not. Document-wide, never per page — see _docx_visible_chars().
    OCR_MIN_OUTPUT_CHARS: int = 10

    # ── Conversion-finished notification ──────────────────────────────────────
    # The worker POSTs the *user id* and outcome to auth-service, which owns the
    # email seam and the users table; doc-manager never sees an email address and
    # holds no mail credentials. Empty URL or key disables notification entirely.
    NOTIFY_URL: str = ""      # e.g. http://auth-service/api/auth/v1/internal/notifications/conversion
    NOTIFY_API_KEY: str = ""  # must equal auth-service's INTERNAL_API_KEY
    # Only notify jobs slower than this. Below it the user is almost certainly
    # still watching the Convert page (it polls while mounted) and already saw the
    # result; mailing them would turn a five-document session into five emails.
    # Bench data is 3-9 s/page, so 120s is about a 15-40 page document — the size
    # at which people tab away.
    NOTIFY_MIN_SECONDS: float = 120.0
    NOTIFY_TIMEOUT_S: float = 5.0

    # Database — shared with auth-service (reads users.plan, reads/writes usage_daily).
    # Empty => quota-gated endpoints (/convert, /usage) return 503.
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 2
    DB_MAX_OVERFLOW: int = 3

    # Plan limits (pages). Enforced at /convert; surfaced by /usage.
    PLAN_FREE_DAILY_PAGES: int = 10
    PLAN_FREE_MAX_DOC_PAGES: int = 10
    # Worst-case Gemini spend for one Pro seat must stay below what the seat pays.
    # At ~$0.0036/page, break-even on $9.99 is ~2,775 pages/month (~2,611 after
    # Stripe fees). 300/day allowed 9,000 and 100/day allowed 3,000 — both above it.
    # 50/day caps a fully-used seat at ~1,500 pages (~$5.40), leaving ~45% margin.
    PLAN_PRO_DAILY_PAGES: int = 50
    # Must stay below the daily cap: at parity, one max-size document consumes
    # the whole day and the advertised per-document allowance is usable once.
    PLAN_PRO_MAX_DOC_PAGES: int = 40

    # Anonymous trial (landing page): first N pages only, rate-limited per client IP.
    TRIAL_MAX_PAGES: int = 1
    TRIAL_RATE_LIMIT: str = "3/day"
    # Authenticated uploads were bounded only by the ingress proxy-body-size.
    MAX_UPLOAD_MB: int = 50
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
