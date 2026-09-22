import html
import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import HtmlContent, Mail, ReplyTo

from app.core.config import settings

logger = logging.getLogger("auth-service.email")


def send_verification_email(to_email: str, token: str):
    if not settings.SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set — skipping verification email to %s", to_email)
        return

    verify_url = f"{settings.FRONTEND_BASE_URL}/verify-email?token={token}"
    message = Mail(from_email=settings.EMAIL_FROM, to_emails=to_email)
    message.dynamic_template_data = {
        "email": to_email,
        "verify_url": verify_url,
    }
    message.template_id = "d-efa8275014ff4abe855d0e0bf9310b00"

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info("Sent verification email to %s (status %d)", to_email, response.status_code)
    except Exception as ex:
        logger.error("Error sending email to %s: %s", to_email, ex)
        raise


def send_password_reset_email(to_email: str, token: str):
    reset_url = f"{settings.FRONTEND_BASE_URL}/reset-password?token={token}"

    if not settings.SENDGRID_API_KEY:
        logger.info("Password reset link for %s: %s", to_email, reset_url)
        return

    html = (
        "<p>You requested a password reset for your Textara account.</p>"
        f'<p><a href="{reset_url}">Click here to reset your password</a></p>'
        "<p>This link expires in 1 hour. If you didn't request this, you can safely ignore this email.</p>"
    )
    message = Mail(from_email=settings.EMAIL_FROM, to_emails=to_email)
    message.subject = "Reset your Textara password"
    message.add_content(HtmlContent(html))

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info("Sent password reset email to %s (status %d)", to_email, response.status_code)
    except Exception as ex:
        logger.error("Error sending password reset email to %s: %s", to_email, ex)
        raise


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

    `reply_to` is the submitter's address, so replying from the inbox reaches them
    directly. Raises on send failure so the endpoint can tell the user it didn't go
    through rather than silently swallowing it.
    """
    subject = f"[Textara {category}] from {reply_to}"
    context = [
        f"<li><strong>Category:</strong> {html.escape(category)}</li>",
        f"<li><strong>From:</strong> {html.escape(reply_to)}</li>",
        f"<li><strong>Account:</strong> {user_id if user_id else 'anonymous'}</li>",
    ]
    if plan:
        context.append(f"<li><strong>Plan:</strong> {html.escape(plan)}</li>")
    if page:
        context.append(f"<li><strong>Page:</strong> {html.escape(page)}</li>")
    if user_agent:
        context.append(f"<li><strong>User agent:</strong> {html.escape(user_agent)}</li>")

    body = (
        f"<ul>{''.join(context)}</ul>"
        f"<hr><p style='white-space:pre-wrap'>{html.escape(message)}</p>"
    )

    if not settings.SENDGRID_API_KEY:
        logger.warning(
            "SENDGRID_API_KEY not set — feedback from %s not delivered: %s",
            reply_to, message[:200],
        )
        return

    mail = Mail(from_email=settings.EMAIL_FROM, to_emails=settings.SUPPORT_EMAIL)
    mail.subject = subject
    mail.add_content(HtmlContent(body))
    mail.reply_to = ReplyTo(reply_to)

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(mail)
        logger.info(
            "Forwarded %s feedback from %s (status %d)", category, reply_to, response.status_code
        )
    except Exception as ex:
        logger.error("Error forwarding feedback from %s: %s", reply_to, ex)
        raise
