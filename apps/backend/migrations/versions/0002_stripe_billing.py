"""Stripe billing: launch plan names and the account's subscription fields.

Renames the plans (observer -> free, operator -> trader) and adds the Stripe
customer, subscription and status columns that the billing webhook writes.

Revision ID: 0002_stripe_billing
Revises: 0001_init
"""

import sqlalchemy as sa
from alembic import op

from verasig.domain.account import Plan
from verasig.storage.models import enum_check

revision = "0002_stripe_billing"
down_revision = "0001_init"
branch_labels = None
depends_on = None

_PLAN_CHECK = "ck_user_account_plan"
_RENAMES = {"observer": "free", "operator": "trader"}


def upgrade() -> None:
    op.drop_constraint(_PLAN_CHECK, "user_account", type_="check")
    for old, new in _RENAMES.items():
        _rename_plan(old, new)
    check = enum_check("plan", Plan, name=_PLAN_CHECK)
    op.create_check_constraint(_PLAN_CHECK, "user_account", str(check.sqltext))
    op.alter_column("user_account", "plan", server_default=Plan.FREE.value)
    op.add_column(
        "user_account", sa.Column("stripe_customer_id", sa.String(), nullable=True)
    )
    op.add_column(
        "user_account", sa.Column("stripe_subscription_id", sa.String(), nullable=True)
    )
    op.add_column(
        "user_account", sa.Column("subscription_status", sa.String(), nullable=True)
    )
    for column in ("stripe_customer_id", "stripe_subscription_id"):
        op.create_index(
            f"uq_user_account_{column}",
            "user_account",
            [column],
            unique=True,
            postgresql_where=sa.text(f"{column} IS NOT NULL"),
        )


def downgrade() -> None:
    for column in ("stripe_customer_id", "stripe_subscription_id"):
        op.drop_index(f"uq_user_account_{column}", table_name="user_account")
    op.drop_column("user_account", "subscription_status")
    op.drop_column("user_account", "stripe_subscription_id")
    op.drop_column("user_account", "stripe_customer_id")
    op.alter_column("user_account", "plan", server_default=None)
    op.drop_constraint(_PLAN_CHECK, "user_account", type_="check")
    for old, new in _RENAMES.items():
        _rename_plan(new, old)
    op.create_check_constraint(
        _PLAN_CHECK, "user_account", "plan IN ('observer', 'operator', 'desk')"
    )


def _rename_plan(old: str, new: str) -> None:
    op.execute(
        sa.text("UPDATE user_account SET plan = :new WHERE plan = :old").bindparams(
            old=old, new=new
        )
    )
