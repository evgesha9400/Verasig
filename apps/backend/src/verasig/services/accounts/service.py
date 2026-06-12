from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from verasig.domain.account import Plan, UserAccount
from verasig.services.accounts.passwords import check_password, hash_password
from verasig.storage.account_repository import find_by_email, insert_account


class EmailTakenError(Exception):
    """Raised when an account already exists for an email."""


class InvalidCredentialsError(Exception):
    """Raised when an email/password pair does not authenticate."""


def normalize_email(email: str) -> str:
    return email.strip().lower()


def register_account(
    session: Session,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
) -> UserAccount:
    normalized = normalize_email(email)
    if find_by_email(session, normalized) is not None:
        raise EmailTakenError(normalized)
    account = UserAccount(
        id=uuid4(),
        email=normalized,
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        plan=Plan.OBSERVER,
        pending_email=None,
        cancel_at=None,
        created_at=datetime.now(tz=UTC),
    )
    return insert_account(session, account)


def authenticate(session: Session, email: str, password: str) -> UserAccount:
    account = find_by_email(session, normalize_email(email))
    if account is None:
        raise InvalidCredentialsError()
    if not check_password(password, account.password_hash):
        raise InvalidCredentialsError()
    return account
