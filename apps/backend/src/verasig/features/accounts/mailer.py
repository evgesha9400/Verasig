import logging
import smtplib
import ssl
from email.message import EmailMessage
from html import escape
from typing import Protocol

from verasig.config import MailConfig

logger = logging.getLogger(__name__)

_SMTP_TIMEOUT_SECONDS = 10


class Mailer(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class SmtpMailer:
    def __init__(self, config: MailConfig) -> None:
        self._config = config

    def send(self, message: EmailMessage) -> None:
        config = self._config
        if "From" not in message:
            message["From"] = config.sender
        # smtplib's default TLS context skips certificate and hostname checks.
        context = ssl.create_default_context()
        if config.tls == "ssl":
            connection = smtplib.SMTP_SSL(
                config.host,
                config.port,
                timeout=_SMTP_TIMEOUT_SECONDS,
                context=context,
            )
        else:
            connection = smtplib.SMTP(
                config.host, config.port, timeout=_SMTP_TIMEOUT_SECONDS
            )
        with connection as smtp:
            if config.tls == "starttls":
                smtp.starttls(context=context)
            if config.user:
                smtp.login(config.user, config.password)
            smtp.send_message(message)


class LogMailer:
    """Local fallback when no SMTP host is configured: logs, never sends."""

    def send(self, message: EmailMessage) -> None:
        # never log the body: it carries bearer links.
        logger.info(
            "email not sent (no SMTP host)",
            extra={"email": message["To"], "subject": message["Subject"]},
        )


def create_mailer(config: MailConfig | None) -> Mailer:
    return SmtpMailer(config) if config else LogMailer()


def build_password_reset_email(to: str, reset_url: str) -> EmailMessage:
    message = EmailMessage()
    message["To"] = to
    message["Subject"] = "Reset your Verasig password"
    message.set_content(
        "Someone asked to reset the password for your Verasig account.\n\n"
        f"Set a new password here:\n{reset_url}\n\n"
        "The link works once and expires in 60 minutes.\n\n"
        "If you did not ask for this, ignore this email. "
        "Your password stays the same.\n"
    )
    link = escape(reset_url, quote=True)
    message.add_alternative(
        "<p>Someone asked to reset the password for your Verasig account.</p>"
        f'<p><a href="{link}">Set a new password</a></p>'
        "<p>The link works once and expires in 60 minutes.</p>"
        "<p>If you did not ask for this, ignore this email. "
        "Your password stays the same.</p>",
        subtype="html",
    )
    return message


def send_email_confirm(email: str, token: str) -> None:
    # never log the token: it is a bearer credential that confirms the change.
    logger.info("email confirmation requested", extra={"email": email})
