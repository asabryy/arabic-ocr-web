import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import HtmlContent, Mail

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
