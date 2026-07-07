"""Cascade user_exchange_connection when its owning account is deleted.

Every other user-owned table cascades on account delete; the exchange
connection's user_id FK was left as the default (RESTRICT), so deleting an
account with a connected exchange would fail. Re-point it ON DELETE CASCADE.

Revision ID: 0018_exchange_user_cascade
Revises: 0017_backfill_prev_status
"""

from alembic import op

revision = "0018_exchange_user_cascade"
down_revision = "0017_backfill_prev_status"
branch_labels = None
depends_on = None

_FK = "user_exchange_connection_user_id_fkey"


def upgrade() -> None:
    op.drop_constraint(_FK, "user_exchange_connection", type_="foreignkey")
    op.create_foreign_key(
        _FK,
        "user_exchange_connection",
        "user_account",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(_FK, "user_exchange_connection", type_="foreignkey")
    op.create_foreign_key(
        _FK,
        "user_exchange_connection",
        "user_account",
        ["user_id"],
        ["id"],
    )
