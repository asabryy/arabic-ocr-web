"""Transactional email.

One seam for every outgoing message. Callers (register, verify, password, feedback)
depend only on the three send_* functions, so swapping providers is a config change.

Provider history worth knowing: SendGrid's trial expired and every send began failing
with "Maximum credits exceeded" for weeks without anyone noticing, because callers
swallow send errors so a mail outage can't break signup. Every send now increments
textara_emails_total{outcome=...}, so the next outage is visible in Grafana instead of
turning up later as a bad verification rate.
"""
import html
import logging

import requests

from app import metrics
from app.core.config import settings

logger = logging.getLogger("auth-service.email")

RESEND_ENDPOINT = "https://api.resend.com/emails"
_TIMEOUT = 15


def _send(
    *,
    kind: str,
    to: str,
    subject: str,
    html_body: str,
    reply_to: str | None = None,
    link: str | None = None,
) -> None:
    """Deliver one message. Raises on failure so callers can decide what to do.

    A missing API key is a skip, not a failure: local development and CI run without
    credentials and must not have signup blow up in their faces. ``link`` is printed
    in that case only when EMAIL_ECHO_LINKS is explicitly on, so the flows stay
    testable locally without writing live verification and reset tokens into logs
    that are retained indefinitely and readable by anyone with dashboard access.
    """
    if not settings.RESEND_API_KEY:
        metrics.EMAILS_SENT.labels(kind=kind, outcome="skipped").inc()
        logger.warning("RESEND_API_KEY not set — %s email to %s not sent", kind, to)
        if link and settings.EMAIL_ECHO_LINKS:
            logger.warning("EMAIL_ECHO_LINKS is on — %s link for %s: %s", kind, to, link)
        return

    payload = {
        "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
        "to": [to],
        "subject": subject,
        "html": html_body,
    }
    if reply_to:
        payload["reply_to"] = reply_to

    try:
        resp = requests.post(
            RESEND_ENDPOINT,
            json=payload,
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            timeout=_TIMEOUT,
        )
    except requests.RequestException as ex:
        metrics.EMAILS_SENT.labels(kind=kind, outcome="failed").inc()
        logger.error("Network error sending %s email to %s: %s", kind, to, ex)
        raise

    if resp.status_code >= 400:
        metrics.EMAILS_SENT.labels(kind=kind, outcome="failed").inc()
        # The body carries the actionable part ("domain is not verified", quota, ...).
        logger.error(
            "Resend rejected %s email to %s: HTTP %d %s",
            kind, to, resp.status_code, resp.text[:300],
        )
        resp.raise_for_status()

    # Read the id before counting, and never let a surprising 2xx body (a proxy
    # interstitial, an empty 202) turn a delivered message into a caller-visible
    # failure — /feedback would answer 503 and the user would send it twice.
    try:
        message_id = resp.json().get("id")
    except ValueError:
        message_id = "unknown"

    metrics.EMAILS_SENT.labels(kind=kind, outcome="sent").inc()
    logger.info("Sent %s email to %s (id=%s)", kind, to, message_id)


# ── Shared chrome ─────────────────────────────────────────────────────────────

def _wrap(heading: str, body: str, button_label: str | None = None, button_url: str | None = None) -> str:
    """Minimal, table-free HTML that survives Gmail and Outlook.

    Deliberately plain: inline styles only, no external CSS or images, since remote
    content is blocked by default in most clients and a broken layout reads as phishing.
    """
    button = ""
    if button_label and button_url:
        # Escaped like every other interpolation here: a token format that ever
        # contains & " or < would otherwise silently produce an unclickable link
        # in the one email that has to work.
        button_url = html.escape(button_url, quote=True)
        button = (
            f'<p style="margin:28px 0"><a href="{button_url}" '
            'style="background:#6366f1;color:#ffffff;text-decoration:none;padding:12px 22px;'
            'display:inline-block;font-weight:600;border-radius:2px">'
            f'{html.escape(button_label)}</a></p>'
            '<p style="margin:0 0 6px;font-size:13px;color:#71717a">'
            "Or paste this link into your browser:</p>"
            f'<p style="margin:0;font-size:13px;word-break:break-all"><a href="{button_url}" '
            f'style="color:#6366f1">{button_url}</a></p>'
        )

    return (
        '<div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        'font-size:15px;line-height:1.6;color:#18181b;max-width:520px;margin:0 auto;padding:24px">'
        '<p style="font-size:18px;font-weight:700;margin:0 0 20px">Textara</p>'
        f'<p style="font-size:17px;font-weight:600;margin:0 0 12px">{html.escape(heading)}</p>'
        f"{body}{button}"
        '<hr style="border:none;border-top:1px solid #e4e4e7;margin:32px 0 14px">'
        '<p style="font-size:12px;color:#a1a1aa;margin:0">'
        "You received this because someone used this address at "
        '<a href="https://textara.app" style="color:#71717a">textara.app</a>. '
        "If it wasn't you, you can ignore this message.</p></div>"
    )


# ── Messages ──────────────────────────────────────────────────────────────────

def send_verification_email(to_email: str, token: str) -> None:
    url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/verify-email?token={token}"
    body = (
        '<p style="margin:0">Confirm this address to finish setting up your Textara '
        "account and convert Arabic PDFs to Word documents.</p>"
    )
    _send(
        kind="verification",
        to=to_email,
        subject="Confirm your email address",
        html_body=_wrap("Confirm your email", body, "Confirm email address", url),
        link=url,
    )


def send_password_reset_email(to_email: str, token: str) -> None:
    url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password?token={token}"
    body = (
        '<p style="margin:0">You asked to reset your Textara password. '
        "This link expires in one hour.</p>"
    )
    _send(
        kind="password_reset",
        to=to_email,
        subject="Reset your Textara password",
        html_body=_wrap("Reset your password", body, "Choose a new password", url),
        link=url,
    )


def send_feedback_email(
    *,
    category: str,
    message: str,
    reply_to: str,
    user_id: int | None = None,
    plan: str | None = None,
    page: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Forward a support/feedback submission to the team inbox.

    `reply_to` is the submitter's address, so answering from the inbox reaches them.
    """
    rows = [
        ("Category", category),
        ("From", reply_to),
        ("Account", str(user_id) if user_id else "anonymous"),
    ]
    if plan:
        rows.append(("Plan", plan))
    if page:
        rows.append(("Page", page))
    if user_agent:
        rows.append(("User agent", user_agent))

    details = "".join(
        f'<p style="margin:0 0 4px;font-size:13px;color:#71717a">'
        f"<strong>{html.escape(k)}:</strong> {html.escape(v)}</p>"
        for k, v in rows
    )
    body = (
        f"{details}"
        '<div style="margin-top:18px;padding:14px;background:#fafafa;border:1px solid #e4e4e7;'
        'white-space:pre-wrap;font-size:14px">'
        f"{html.escape(message)}</div>"
    )
    _send(
        kind="feedback",
        to=settings.SUPPORT_EMAIL,
        subject=f"[Textara {category}] from {reply_to}",
        html_body=_wrap(f"New {category} report", body),
        reply_to=reply_to,
    )
