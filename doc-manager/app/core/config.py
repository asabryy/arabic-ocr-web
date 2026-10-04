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

    # ── Digital conversion path ───────────────────────────────────────────────
    # Most uploads are born-digital: the PDF already contains its text, so it can
    # be converted with no Gemini call at all — free, and milliseconds instead of
    # 3-9 s per page. Measured over 293 real documents (11,336 pages): 71% are
    # digital, and of those 76% extract cleanly, so ~50% of all pages take this
    # route. The rest fall back to Gemini.
    DIGITAL_PATH_ENABLED: bool = True      # kill switch; False = Gemini for everything
    # Fraction of pages that must carry a usable text layer. Below it the document
    # is a scan (or a scan wearing an OCR text layer) and belongs on the OCR path.
    DIGITAL_MIN_TEXT_PAGE_RATIO: float = 0.8
    # Fraction of combining marks sharing a coordinate with another. Above this the
    # typesetter batched its tashkeel at shared pen positions, the coordinates carry
    # no per-mark information, and no geometry recovers which letter each belongs
    # to. 23% of digital documents in the corpus; they go to Gemini.
    DIGITAL_MAX_MARK_BATCHING: float = 0.10
    # Below this many marks the ratio above is noise, not signal: a page with two
    # marks that happen to collide would otherwise score 100%.
    DIGITAL_MIN_MARKS_FOR_BATCHING: int = 30
    # Pages inspected when choosing a route. Bounds triage on a 600-page book; it
    # does not bound the conversion itself.
    DIGITAL_TRIAGE_MAX_PAGES: int = 25
    # Word-gap threshold, in em. Subset fonts often omit the space glyph, so gaps
    # are inferred from geometry; this must stay above the intra-word gap that a
    # non-connecting Arabic letter (ا د ر و) leaves behind.
    DIGITAL_WORD_GAP_EM: float = 0.25
    # A baseline gap this many times the dominant line spacing starts a new
    # paragraph. Measured across the corpus, paragraph breaks sit at 1.2-1.3x the
    # line spacing — markedly tighter than the 1.5x that reads as obvious, which
    # silently merged every paragraph in the closest-set documents.
    DIGITAL_PARA_GAP_RATIO: float = 1.15
    # "source" keeps the original's fonts, sizes, colours and underlines;
    # "uniform" renders like the Gemini path. Users choose per conversion.
    DIGITAL_DEFAULT_STYLE: str = "source"

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
    # Comped / beta accounts. Effectively unlimited, but finite on purpose: Gemini
    # is metered and prepaid, so a genuinely uncapped account could drain the balance
    # in an afternoon. 5,000 pages/day is ~$18/day of exposure per comped account —
    # far beyond any real use, and still a backstop.
    PLAN_UNLIMITED_DAILY_PAGES: int = 5000
    PLAN_UNLIMITED_MAX_DOC_PAGES: int = 2000

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
