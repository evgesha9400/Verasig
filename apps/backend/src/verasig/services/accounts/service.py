from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from verasig.domain.account import Plan, UserAccount
from verasig.services.accounts.passwords import check_password, hash_password
from verasig.storage.account_repository import (
    apply_pending_email,
    find_by_email,
    insert_account,
    set_cancel_at,
    set_pending_email,
    set_plan,
    update_profile,
)


class EmailTakenError(Exception):
    """Raised when an account already exists for an email."""


class InvalidCredentialsError(Exception):
    """Raised when an email/password pair does not authenticate."""


class PendingEmailMismatchError(Exception):
    """Raised when an email confirmation token does not match account state."""


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


def rename_account(
    session: Session,
    account: UserAccount,
    first_name: str | None = None,
    last_name: str | None = None,
) -> UserAccount:
    return update_profile(session, account.id, first_name, last_name)


def request_email_change(
    session: Session, account: UserAccount, new_email: str
) -> UserAccount:
    return set_pending_email(session, account.id, normalize_email(new_email))


def confirm_email_change(
    session: Session, account: UserAccount, new_email: str
) -> UserAccount:
    if account.pending_email != normalize_email(new_email):
        raise PendingEmailMismatchError()
    applied = apply_pending_email(session, account.id)
    if applied is None:
        raise PendingEmailMismatchError()
    return applied


def change_plan(session: Session, account: UserAccount, plan: Plan) -> UserAccount:
    return set_plan(session, account.id, plan)


def cancel_subscription(session: Session, account: UserAccount) -> UserAccount:
    return set_cancel_at(session, account.id, datetime.now(tz=UTC) + timedelta(days=30))


def resume_subscription(session: Session, account: UserAccount) -> UserAccount:
    return set_cancel_at(session, account.id, None)
