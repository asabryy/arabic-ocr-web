"""Prometheus metrics shared by the doc-manager API and the doc-worker.

Everything is defined exactly once, at module scope (the prometheus_client registry is
process-global and rejects duplicate names). This module imports only prometheus_client
so the worker process can use it without pulling in FastAPI.

Naming:
- ``ocr_*`` keep the names the retired local OCR server used, so the existing
  "Textara OCR Pipeline" Grafana dashboard lights up again (a ``mode`` label was added;
  its ``sum()``/``histogram_quantile`` queries are unaffected).
- ``gemini_*`` describe the upstream API calls (attempts, latency, tokens, cost).
- ``textara_*`` are product/business counters emitted by the API.
Label values are bounded enums only — never user ids, filenames or trial ids.
"""

import logging

from prometheus_client import Counter, Histogram, start_http_server

log = logging.getLogger("doc-manager.metrics")

# ── Worker: OCR tasks & pages (legacy names) ──────────────────────────────────

OCR_REQUESTS = Counter(
    "ocr_requests",
    "OCR document tasks processed by the worker, by outcome",
    ["status", "mode"],  # status: success|error, mode: ocr|trial
)
OCR_REQUEST_DURATION = Histogram(
    "ocr_request_duration_seconds",
    "End-to-end task time (fetch + OCR + save), incl. retries/backoff",
    ["mode"],
    buckets=[5, 10, 30, 60, 120, 300, 600, 1200],
)
OCR_PAGES = Counter("ocr_pages", "Pages OCR'd", ["mode"])
OCR_PAGE_DURATION = Histogram(
    "ocr_page_duration_seconds",
    "Wall time per page (render + Gemini call incl. retries/backoff)",
    buckets=[1, 2, 5, 10, 20, 30, 60, 120],
)

# ── Gemini API ────────────────────────────────────────────────────────────────

GEMINI_REQUESTS = Counter(
    "gemini_requests",
    "generate_content attempts by outcome",
    ["outcome", "model"],  # outcome: ok|retry_503|retry_429|error
)
GEMINI_REQUEST_DURATION = Histogram(
    "gemini_request_duration_seconds",
    "Latency of successful generate_content calls (pure API time)",
    buckets=[1, 2, 5, 10, 20, 30, 60, 120],
)
GEMINI_BACKOFF_SECONDS = Counter(
    "gemini_backoff_seconds",
    "Seconds slept waiting to retry a rate-limited/overloaded call",
    ["reason"],  # 429|503
)
GEMINI_TOKENS = Counter(
    "gemini_tokens",
    "Tokens reported by usage_metadata",
    ["kind", "model"],  # kind: prompt|candidates|thoughts
)
GEMINI_COST_USD = Counter(
    "gemini_cost_usd",
    "Estimated spend in USD (prompt at input price; candidates+thoughts at output price)",
    ["model"],
)

# ── API: product / business counters ──────────────────────────────────────────

UPLOADS = Counter("textara_uploads", "PDF uploads accepted")
CONVERSIONS_REQUESTED = Counter(
    "textara_conversions_requested",
    "Conversions queued to the worker",
    ["mode", "plan"],  # plan: free|pro|anonymous
)
PAGES_REQUESTED = Counter(
    "textara_pages_requested", "Pages queued for OCR", ["mode", "plan"]
)
QUOTA_REJECTIONS = Counter(
    "textara_quota_rejections",
    "Conversions refused by plan quota (HTTP 402)",
    ["reason", "plan"],  # reason: doc_pages_exceeded|daily_pages_exceeded
)
TRIAL_REJECTIONS = Counter(
    "textara_trial_rejections",
    "Anonymous trial uploads refused",
    ["reason"],  # rate_limited|too_large|invalid_pdf
)
TRIAL_DOWNLOADS = Counter("textara_trial_downloads", "Trial results downloaded")
ENQUEUE_FAILURES = Counter(
    "textara_enqueue_failures", "Conversions that could not be queued (RabbitMQ)", ["mode"]
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def start_worker_metrics_server(port: int) -> None:
    """Expose /metrics for the worker process (no-op when port is 0)."""
    if port and port > 0:
        start_http_server(port)
        log.info("Worker metrics server listening on :%d/metrics", port)


def record_gemini_usage(usage, model: str, price_in_per_m: float, price_out_per_m: float) -> float:
    """Account tokens + estimated cost from a genai ``usage_metadata`` object.

    Tolerates a missing/partial object. Returns the estimated cost in USD.
    """
    if usage is None:
        return 0.0
    prompt = getattr(usage, "prompt_token_count", None) or 0
    candidates = getattr(usage, "candidates_token_count", None) or 0
    thoughts = getattr(usage, "thoughts_token_count", None) or 0
    GEMINI_TOKENS.labels(kind="prompt", model=model).inc(prompt)
    GEMINI_TOKENS.labels(kind="candidates", model=model).inc(candidates)
    GEMINI_TOKENS.labels(kind="thoughts", model=model).inc(thoughts)
    cost = prompt * price_in_per_m / 1e6 + (candidates + thoughts) * price_out_per_m / 1e6
    GEMINI_COST_USD.labels(model=model).inc(cost)
    return cost


# A counter child does not exist until .labels() is first called, so a failure mode
# that has never occurred has no series — an alert on it never fires and a panel
# reads "No data" exactly as it would during a real outage. Create them at zero.
for _mode in ("ocr", "trial"):
    ENQUEUE_FAILURES.labels(mode=_mode)
    OCR_REQUESTS.labels(status="success", mode=_mode)
    OCR_REQUESTS.labels(status="error", mode=_mode)
    OCR_PAGES.labels(mode=_mode)

for _reason in ("rate_limited", "too_large", "invalid_pdf"):
    TRIAL_REJECTIONS.labels(reason=_reason)

for _plan in ("free", "pro"):
    for _code in ("daily_pages_exceeded", "doc_pages_exceeded"):
        QUOTA_REJECTIONS.labels(reason=_code, plan=_plan)
