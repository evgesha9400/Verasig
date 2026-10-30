from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from verasig.domain.account import Plan, UserAccount
from verasig.features.accounts.repository import to_account
from verasig.storage.models import UserAccountRow

# Webhook handlers read an account, decide, then write. Both finders lock the
# row so two deliveries for the same user apply one after the other.


def lock_by_id(session: Session, user_id: UUID) -> UserAccount | None:
    row = session.get(UserAccountRow, user_id, with_for_update=True)
    return to_account(row) if row else None


def lock_by_subscription_id(
    session: Session, subscription_id: str
) -> UserAccount | None:
    row = session.scalars(
        select(UserAccountRow)
        .where(UserAccountRow.stripe_subscription_id == subscription_id)
        .with_for_update()
    ).one_or_none()
    return to_account(row) if row else None


def save_subscription(
    session: Session,
    user_id: UUID,
    *,
    plan: Plan,
    status: str | None,
    customer_id: str | None,
    subscription_id: str | None,
    cancel_at: datetime | None,
) -> UserAccount | None:
    row = session.get(UserAccountRow, user_id)
    if row is None:
        return None
    row.plan = plan.value
    row.subscription_status = status
    row.stripe_customer_id = customer_id
    row.stripe_subscription_id = subscription_id
    row.cancel_at = cancel_at
    session.flush()
    return to_account(row)
