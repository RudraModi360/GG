import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from ..config import settings

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, html_content: str) -> None:
    """
    Send an email using SMTP settings from configuration.
    """
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.warning("SMTP settings not configured. Email not sent.")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(html_content, 'html'))

        # Connect to SMTP server
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email sent to {to_email}: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")

def get_welcome_email_content(name: str) -> str:
    return f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2563eb;">Welcome to GearGuard!</h1>
                <p>Hello {name},</p>
                <p>Thank you for registering with GearGuard. We're excited to help you manage your equipment efficiently.</p>
                <p>Your account has been successfully created and is ready to use.</p>
                <p>If you have any questions, feel free to reply to this email.</p>
                <br>
                <p>Best regards,</p>
                <p>The GearGuard Team</p>
            </div>
        </body>
    </html>
    """

def get_reset_password_email_content(reset_token: str, base_url: str = "http://localhost:3000") -> str:
    # Assuming frontend handles the reset page at /reset-password?token=...
    reset_link = f"{base_url}/reset-password?token={reset_token}"
    return f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2563eb;">Password Reset Request</h1>
                <p>We received a request to reset your password for your GearGuard account.</p>
                <p>Click the button below to reset your password:</p>
                <p>
                    <a href="{reset_link}" style="display: inline-block; padding: 10px 20px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 5px;">Reset Password</a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p>{reset_link}</p>
                <p>This link will expire in 1 hour.</p>
                <p>If you did not request a password reset, you can safely ignore this email.</p>
                <br>
                <p>Best regards,</p>
                <p>The GearGuard Team</p>
            </div>
        </body>
    </html>
    """
