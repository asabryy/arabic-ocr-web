import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@example.com")

def send_verification_email(to_email: str, token: str):
    verify_url = f"http://localhost:8000/api/v1/verify-email?token={token}"
    subject = "Verify your email"
    content = f"""
    Hi,

    Please verify your email by clicking the link below:

    {verify_url}

    If you didn't sign up, ignore this email.
    """

    message = Mail(
        from_email=EMAIL_FROM,
        to_emails=to_email,
        subject=subject,
        plain_text_content=content
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"Email sent to {to_email}. Status: {response.status_code}")
    except Exception as e:
        print(f"SendGrid error: {e}")
