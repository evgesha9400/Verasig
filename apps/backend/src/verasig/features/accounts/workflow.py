from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from verasig.domain.account import Plan, UserAccount
from verasig.features.accounts.name_validation import validate_account_name_pair
from verasig.features.accounts.passwords import check_password, hash_password
from verasig.features.accounts.repository import (
    apply_pending_email,
    find_by_email,
    find_by_id,
    insert_account,
    set_password_hash,
    set_pending_email,
    update_profile,
)
from verasig.features.accounts.tokens import password_fingerprint


class EmailTakenError(Exception):
    """Raised when an account already exists for an email."""


class InvalidCredentialsError(Exception):
    """Raised when an email/password pair does not authenticate."""


class PendingEmailMismatchError(Exception):
    """Raised when an email confirmation token does not match account state."""


class ResetLinkInvalidError(Exception):
    """Raised when a password reset token no longer matches its account."""


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
    normalized_first_name, normalized_last_name = validate_account_name_pair(
        first_name, last_name
    )
    account = UserAccount(
        id=uuid4(),
        email=normalized,
        password_hash=hash_password(password),
        first_name=normalized_first_name,
        last_name=normalized_last_name,
        plan=Plan.FREE,
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
    if first_name is None and last_name is None:
        return account
    normalized_first_name = account.first_name if first_name is None else first_name
    normalized_last_name = account.last_name if last_name is None else last_name
    normalized_first_name, normalized_last_name = validate_account_name_pair(
        normalized_first_name, normalized_last_name
    )
    return update_profile(
        session, account.id, normalized_first_name, normalized_last_name
    )


def request_email_change(
    session: Session, account: UserAccount, new_email: str
) -> UserAccount:
    normalized = normalize_email(new_email)
    existing = find_by_email(session, normalized)
    if existing is not None and existing.id != account.id:
        raise EmailTakenError(normalized)
    return set_pending_email(session, account.id, normalized)


def confirm_email_change(
    session: Session, account: UserAccount, new_email: str
) -> UserAccount:
    normalized = normalize_email(new_email)
    if account.pending_email != normalized:
        raise PendingEmailMismatchError()
    # the address may have been claimed between request and confirm; reject with a
    # typed error rather than letting the unique constraint 500 on apply.
    existing = find_by_email(session, normalized)
    if existing is not None and existing.id != account.id:
        raise EmailTakenError(normalized)
    applied = apply_pending_email(session, account.id, normalized)
    if applied is None:
        raise PendingEmailMismatchError()
    return applied


def cancel_email_change(session: Session, account: UserAccount) -> UserAccount:
    return set_pending_email(session, account.id, None)


def find_account(session: Session, email: str) -> UserAccount | None:
    return find_by_email(session, normalize_email(email))


def reset_password(
    session: Session, user_id: UUID, fingerprint: str, new_password: str
) -> UserAccount:
    account = find_by_id(session, user_id)
    if account is None or password_fingerprint(account.password_hash) != fingerprint:
        raise ResetLinkInvalidError()
    updated = set_password_hash(
        session, user_id, hash_password(new_password), account.password_hash
    )
    if updated is None:
        raise ResetLinkInvalidError()
    return updated
