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
STRIPE_EVENTS = Counter(
    "textara_stripe_events",
    "Stripe webhook events by type and what we did about them",
    ["type", "outcome"],  # applied|duplicate|ignored|no_user|invalid_signature|no_secret
)

# Prometheus does not create a child series until .labels() is first called, so a
# failure mode that has never occurred has no series — and an alert on it silently
# never fires, while a dashboard panel reads "No data" exactly as it would during a
# real outage. Pre-create the combinations that matter so zero is a visible zero.
for _kind in ("verification", "password_reset", "feedback"):
    for _outcome in ("sent", "failed", "skipped"):
        EMAILS_SENT.labels(kind=_kind, outcome=_outcome)

for _outcome in ("applied", "duplicate", "ignored", "no_user", "invalid_signature", "no_secret"):
    for _type in (
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.payment_failed",
    ):
        STRIPE_EVENTS.labels(type=_type, outcome=_outcome)

for _method in ("password", "google"):
    for _outcome in ("success", "failure"):
        LOGINS.labels(method=_method, outcome=_outcome)
    SIGNUPS.labels(method=_method)
