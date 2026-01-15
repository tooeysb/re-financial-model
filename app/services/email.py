"""
Email service using SendGrid.

Falls back to console logging if SendGrid is not configured.
"""

import logging
from typing import Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    """Email service with SendGrid integration."""

    def __init__(self):
        self.api_key = settings.sendgrid_api_key
        self.from_email = settings.sendgrid_from_email
        self.from_name = settings.sendgrid_from_name
        self.frontend_url = settings.frontend_url
        self.client = None

        if self.api_key:
            self.client = SendGridAPIClient(self.api_key)

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.client:
            # Log email to console if SendGrid not configured
            logger.info(
                f"[EMAIL - Console Mode]\n"
                f"To: {to_email}\n"
                f"Subject: {subject}\n"
                f"Content:\n{html_content}\n"
            )
            return True

        try:
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content),
            )

            response = self.client.send(message)

            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(
                    f"Failed to send email: {response.status_code} - {response.body}"
                )
                return False

        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False

    def send_invite_email(
        self,
        to_email: str,
        token: str,
        inviter_name: Optional[str] = None,
    ) -> bool:
        """
        Send an invitation email to a new user.

        Args:
            to_email: New user's email address
            token: Invitation token
            inviter_name: Name of the person who sent the invite

        Returns:
            True if sent successfully
        """
        invite_url = f"{self.frontend_url}/auth/register?token={token}"
        inviter_text = f" by {inviter_name}" if inviter_name else ""

        subject = f"You've been invited to {settings.app_name}"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #3b82f6; color: white; text-decoration: none; border-radius: 6px; font-weight: 500; }}
                .button:hover {{ background-color: #2563eb; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Welcome to {settings.app_name}</h1>
                <p>You've been invited{inviter_text} to join {settings.app_name}.</p>
                <p>Click the button below to create your account:</p>
                <p style="margin: 30px 0;">
                    <a href="{invite_url}" class="button">Create Account</a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">{invite_url}</p>
                <p class="footer">
                    This invitation will expire in {settings.invite_token_expire_days} days.<br>
                    If you didn't expect this invitation, you can safely ignore this email.
                </p>
            </div>
        </body>
        </html>
        """

        return self._send_email(to_email, subject, html_content)

    def send_password_reset_email(self, to_email: str, token: str) -> bool:
        """
        Send a password reset email.

        Args:
            to_email: User's email address
            token: Password reset token

        Returns:
            True if sent successfully
        """
        reset_url = f"{self.frontend_url}/auth/reset-password?token={token}"

        subject = f"Reset your {settings.app_name} password"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #3b82f6; color: white; text-decoration: none; border-radius: 6px; font-weight: 500; }}
                .button:hover {{ background-color: #2563eb; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Reset Your Password</h1>
                <p>We received a request to reset your password for your {settings.app_name} account.</p>
                <p>Click the button below to set a new password:</p>
                <p style="margin: 30px 0;">
                    <a href="{reset_url}" class="button">Reset Password</a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">{reset_url}</p>
                <p class="footer">
                    This link will expire in {settings.password_reset_token_expire_hours} hours.<br>
                    If you didn't request a password reset, you can safely ignore this email.
                </p>
            </div>
        </body>
        </html>
        """

        return self._send_email(to_email, subject, html_content)

    def send_welcome_email(self, to_email: str, first_name: Optional[str] = None) -> bool:
        """
        Send a welcome email after registration.

        Args:
            to_email: User's email address
            first_name: User's first name (optional)

        Returns:
            True if sent successfully
        """
        greeting = f"Hi {first_name}" if first_name else "Welcome"
        login_url = f"{self.frontend_url}/auth/login"

        subject = f"Welcome to {settings.app_name}"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #3b82f6; color: white; text-decoration: none; border-radius: 6px; font-weight: 500; }}
                .button:hover {{ background-color: #2563eb; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{greeting}!</h1>
                <p>Your account has been successfully created. You now have access to {settings.app_name}.</p>
                <p>Click below to log in and get started:</p>
                <p style="margin: 30px 0;">
                    <a href="{login_url}" class="button">Log In</a>
                </p>
                <p class="footer">
                    If you have any questions, please don't hesitate to reach out.
                </p>
            </div>
        </body>
        </html>
        """

        return self._send_email(to_email, subject, html_content)


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get the email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
