import os
import logging
from email.message import EmailMessage
from aiosmtplib import send
from dotenv import load_dotenv

# Use development env by default if not set
env_file = ".env.dev" if os.getenv("ENV") == "dev" else ".env"
load_dotenv(env_file)

logger = logging.getLogger(__name__)

class EmailService:
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

    @classmethod
    async def send_email(cls, to: str, subject: str, html_content: str):
        """Sends an HTML email using SMTP."""
        if not cls.SMTP_USER or not cls.SMTP_PASSWORD:
            logger.error("Email settings missing: SMTP_USER or SMTP_PASSWORD not set.")
            # For development, we can still log it to console as a fallback
            print(f"\n[EMAIL LOG (Fallback)] To: {to}\nSubject: {subject}\nContent: {html_content}\n")
            return False

        message = EmailMessage()
        message["From"] = cls.SMTP_USER
        message["To"] = to
        message["Subject"] = subject
        message.set_content(html_content, subtype="html")

        try:
            await send(
                message,
                hostname=cls.SMTP_HOST,
                port=cls.SMTP_PORT,
                username=cls.SMTP_USER,
                password=cls.SMTP_PASSWORD,
                use_tls=False,
                start_tls=True if cls.SMTP_PORT == 587 else False
            )
            logger.info(f"Email sent successfully to {to}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {str(e)}")
            return False

    @classmethod
    async def send_reset_email(cls, to: str, reset_link: str):
        """Sends a stylized password reset email."""
        subject = "Reset Your InterractAI Password"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
            <h2 style="color: #001F3F; text-align: center;">Password Reset Request</h2>
            <p>Hello,</p>
            <p>We received a request to reset your password for your <b>InterractAI</b> account. Click the button below to set a new password:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}" style="background-color: #001F3F; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Password</a>
            </div>
            <p>If you didn't request this, you can safely ignore this email. This link will expire in 1 hour.</p>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="font-size: 12px; color: #888; text-align: center;">&copy; 2026 InterractAI Dashboard. All rights reserved.</p>
        </div>
        """
        return await cls.send_email(to, subject, html_content)

email_service = EmailService()
