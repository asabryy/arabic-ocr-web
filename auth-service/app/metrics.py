"""Prometheus product counters for auth-service (defined once, module scope)."""

from prometheus_client import Counter

SIGNUPS = Counter("textara_signups", "Accounts created", ["method"])  # password|google
LOGINS = Counter(
    "textara_logins", "Login attempts", ["method", "outcome"]  # outcome: success|failure
)
EMAIL_VERIFICATIONS = Counter("textara_email_verifications", "Email addresses verified")
EMAILS_SENT = Counter(
    "textara_emails", "Transactional emails by kind and outcome",
    ["kind", "outcome"],  # kind: verification|password_reset|feedback; outcome: sent|failed|skipped
)
