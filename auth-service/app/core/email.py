import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.core.config import Settings

settings = Settings()
logger = logging.getLogger("auth-service.email")


def send_verification_email(to_email: str, token: str):
    """
    Send an email with a verification link to the user.
    """
    verify_url = f"{settings.FRONTEND_BASE_URL}/api/auth/v1/verify?token={token}"
    message = Mail(
        from_email=settings.EMAIL_FROM,
        to_emails=to_email,
        subject="Please verify your email address",
        plain_text_content=(
            f"Hello,\n\n"
            f"Please verify your email by clicking the link below:\n"
            f"{verify_url}\n\n"
            "If you did not register, please ignore this message."
        ),
    )

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info("Sent verification email to %s (status %d)", to_email, response.status_code)
    except Exception as ex:
        logger.error("Error sending email to %s: %s", to_email, ex)
        raise
