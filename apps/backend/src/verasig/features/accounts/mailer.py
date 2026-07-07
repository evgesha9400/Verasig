import logging

logger = logging.getLogger(__name__)


def send_email_confirm(email: str, token: str) -> None:
    # never log the token: it is a bearer credential that confirms the change.
    logger.info("email confirmation requested", extra={"email": email})


def send_password_reset_requested(email: str) -> None:
    logger.info("password reset requested", extra={"email": email})
