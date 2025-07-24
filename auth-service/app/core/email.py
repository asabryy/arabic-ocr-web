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
    verify_url = f"{settings.FRONTEND_BASE_URL}/verify-email?token={token}"
    message = Mail(
        from_email=settings.EMAIL_FROM,
        to_emails=to_email
    )
    message.dynamic_template_data = {
        'email': to_email,
        'verify_url': verify_url,
    }
    message.template_id = 'd-efa8275014ff4abe855d0e0bf9310b00'

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info("Sent verification email to %s (status %d)", to_email, response.status_code)
    except Exception as ex:
        logger.error("Error sending email to %s: %s", to_email, ex)
        raise
