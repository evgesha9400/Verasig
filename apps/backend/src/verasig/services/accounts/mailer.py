import logging

logger = logging.getLogger(__name__)


def send_email_confirm(email: str, token: str) -> None:
    logger.info("email confirmation requested", extra={"email": email, "token": token})


def send_password_reset_requested(email: str) -> None:
    logger.info("password reset requested", extra={"email": email})
