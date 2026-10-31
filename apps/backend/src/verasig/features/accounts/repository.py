from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from verasig.domain.account import Plan, UserAccount
from verasig.storage.models import UserAccountRow


def to_account(row: UserAccountRow) -> UserAccount:
    return UserAccount(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        first_name=row.first_name,
        last_name=row.last_name,
        plan=Plan(row.plan),
        pending_email=row.pending_email,
        cancel_at=row.cancel_at,
        created_at=row.created_at,
        stripe_customer_id=row.stripe_customer_id,
        stripe_subscription_id=row.stripe_subscription_id,
        subscription_status=row.subscription_status,
        stripe_checkout_session_id=row.stripe_checkout_session_id,
        stripe_event_at=row.stripe_event_at,
    )


def insert_account(session: Session, account: UserAccount) -> UserAccount:
    row = UserAccountRow(
        id=account.id,
        email=account.email,
        password_hash=account.password_hash,
        first_name=account.first_name,
        last_name=account.last_name,
        plan=account.plan.value,
        pending_email=account.pending_email,
        cancel_at=account.cancel_at,
        created_at=account.created_at,
    )
    session.add(row)
    session.flush()
    return to_account(row)


def find_by_email(session: Session, email: str) -> UserAccount | None:
    row = session.scalars(
        select(UserAccountRow).where(UserAccountRow.email == email)
    ).one_or_none()
    return to_account(row) if row else None


def find_by_id(session: Session, user_id: UUID) -> UserAccount | None:
    row = session.get(UserAccountRow, user_id)
    return to_account(row) if row else None


def update_profile(
    session: Session,
    user_id: UUID,
    first_name: str | None = None,
    last_name: str | None = None,
) -> UserAccount | None:
    row = session.get(UserAccountRow, user_id)
    if row is None:
        return None
    if first_name is not None:
        row.first_name = first_name
    if last_name is not None:
        row.last_name = last_name
    session.flush()
    return to_account(row)


def set_pending_email(
    session: Session, user_id: UUID, pending_email: str | None
) -> UserAccount | None:
    row = session.get(UserAccountRow, user_id)
    if row is None:
        return None
    row.pending_email = pending_email
    session.flush()
    return to_account(row)


def apply_pending_email(
    session: Session, user_id: UUID, expected_email: str
) -> UserAccount | None:
    """Promote the pending email, only if it is still `expected_email`.

    The row is locked and re-read, so a pending email replaced or cancelled after
    the caller's check cannot be applied in its place.
    """
    row = session.get(UserAccountRow, user_id, with_for_update=True)
    if row is None or row.pending_email is None:
        return None
    if row.pending_email != expected_email:
        return None
    row.email = row.pending_email
    row.pending_email = None
    session.flush()
    return to_account(row)


def set_password_hash(
    session: Session, user_id: UUID, password_hash: str, expected_hash: str
) -> UserAccount | None:
    """Replace the password hash, only if it is still `expected_hash`.

    The row is locked and re-read, so two resets racing on one token cannot
    both succeed.
    """
    row = session.get(UserAccountRow, user_id, with_for_update=True)
    if row is None or row.password_hash != expected_hash:
        return None
    row.password_hash = password_hash
    session.flush()
    return to_account(row)
