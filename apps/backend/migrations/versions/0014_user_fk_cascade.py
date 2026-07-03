"""Add ON DELETE CASCADE to every user_id -> user_account foreign key.

The user-owned model (0010) re-rooted the channel-scoped FKs at ``feed(...)``
with CASCADE, but the single-column ``user_id -> user_account(id)`` FKs were
created by earlier table-creation migrations without it, while the ORM models
declare ``ondelete="CASCADE"``. That mismatch is the only model<->schema drift
``alembic check`` reports on a fresh database. Deleting a user account should
purge that user's rows; this makes the schema match the models.

Two of these FKs still carry pre-rename names (``user_channel_user_id_fkey`` and
``chat_risk_config_user_id_fkey`` from 0010's table renames). Reflecting the FK
by its constrained columns finds it regardless of name and normalises it to
``<table>_user_id_fkey``.

Revision ID: 0014_user_fk_cascade
Revises: 0013_feed_history_depth
"""

from alembic import op
from sqlalchemy import inspect

revision = "0014_user_fk_cascade"
down_revision = "0013_feed_history_depth"
branch_labels = None
depends_on = None

# Every table owning a single-column user_id -> user_account(id) FK.
_USER_FK_TABLES = (
    "backfill_job_run",
    "backtest_result",
    "extracted_signal",
    "feed",
    "feed_risk_config",
    "filter_drift_warning",
    "filter_rule",
    "golden_label",
    "lifecycle_link",
    "parser_drift_warning",
    "parser_rule",
    "unrecognized_signal",
)


def _reflect_user_account_fk_name(table: str) -> str:
    """Return the current name of the table's user_id -> user_account FK."""
    for fk in inspect(op.get_bind()).get_foreign_keys(table):
        if (
            fk["constrained_columns"] == ["user_id"]
            and fk["referred_table"] == "user_account"
        ):
            return fk["name"]
    raise RuntimeError(f"0014: no user_id -> user_account FK on {table} to alter")


def _repoint_user_fk(table: str, ondelete: str | None) -> None:
    """Drop the reflected user_id FK and recreate it with the given ON DELETE."""
    op.drop_constraint(_reflect_user_account_fk_name(table), table, type_="foreignkey")
    op.create_foreign_key(
        f"{table}_user_id_fkey",
        table,
        "user_account",
        ["user_id"],
        ["id"],
        ondelete=ondelete,
    )


def upgrade() -> None:
    for table in _USER_FK_TABLES:
        _repoint_user_fk(table, ondelete="CASCADE")


def downgrade() -> None:
    for table in _USER_FK_TABLES:
        _repoint_user_fk(table, ondelete=None)
