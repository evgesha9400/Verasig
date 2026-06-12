from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from verasig.domain.account import Plan, UserAccount
from verasig.storage.models import UserAccountRow


def _to_account(row: UserAccountRow) -> UserAccount:
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
    return _to_account(row)


def find_by_email(session: Session, email: str) -> UserAccount | None:
    row = session.scalars(
        select(UserAccountRow).where(UserAccountRow.email == email)
    ).one_or_none()
    return _to_account(row) if row else None


def find_by_id(session: Session, user_id: UUID) -> UserAccount | None:
    row = session.get(UserAccountRow, user_id)
    return _to_account(row) if row else None


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
    return _to_account(row)


def set_pending_email(
    session: Session, user_id: UUID, pending_email: str
) -> UserAccount | None:
    row = session.get(UserAccountRow, user_id)
    if row is None:
        return None
    row.pending_email = pending_email
    session.flush()
    return _to_account(row)


def apply_pending_email(session: Session, user_id: UUID) -> UserAccount | None:
    row = session.get(UserAccountRow, user_id)
    if row is None or row.pending_email is None:
        return None
    row.email = row.pending_email
    row.pending_email = None
    session.flush()
    return _to_account(row)


def set_plan(session: Session, user_id: UUID, plan: Plan) -> UserAccount | None:
    row = session.get(UserAccountRow, user_id)
    if row is None:
        return None
    row.plan = plan.value
    session.flush()
    return _to_account(row)


def set_cancel_at(
    session: Session, user_id: UUID, cancel_at: datetime | None
) -> UserAccount | None:
    row = session.get(UserAccountRow, user_id)
    if row is None:
        return None
    row.cancel_at = cancel_at
    session.flush()
    return _to_account(row)
