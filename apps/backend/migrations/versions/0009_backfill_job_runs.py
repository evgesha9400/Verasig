"""persist durable backfill job runs.

Revision ID: 0009_backfill_job_runs
Revises: 0008_schema_hardening
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_backfill_job_runs"
down_revision = "0008_schema_hardening"
branch_labels = None
depends_on = None

_USER_CHANNEL_STATUS = (
    "status IN ('new', 'backfilling', 'backfilled', 'verified', "
    "'analyzed', 'cancelled', 'failed')"
)

_OLD_USER_CHANNEL_STATUS = (
    "status IN ('new', 'backfilling', 'backfilled', 'verified', "
    "'analyzed', 'cancelled')"
)


def _replace_user_channel_status_check(condition: str) -> None:
    op.drop_constraint("ck_user_channel_status", "user_channel", type_="check")
    op.create_check_constraint("ck_user_channel_status", "user_channel", condition)


def upgrade() -> None:
    _replace_user_channel_status_check(_USER_CHANNEL_STATUS)
    op.create_table(
        "backfill_job_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_count", sa.Integer(), nullable=False),
        sa.Column("oldest_posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cursor_message_id", sa.BigInteger(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'cancelled')",
            name="ck_backfill_job_run_status",
        ),
        sa.ForeignKeyConstraint(["channel_id"], ["telegram_channel.channel_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user_account.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_backfill_job_run_user_channel_started",
        "backfill_job_run",
        ["user_id", "channel_id", "started_at"],
    )
    op.create_index("ix_backfill_job_run_status", "backfill_job_run", ["status"])


def downgrade() -> None:
    op.drop_index("ix_backfill_job_run_status", table_name="backfill_job_run")
    op.drop_index(
        "ix_backfill_job_run_user_channel_started", table_name="backfill_job_run"
    )
    op.drop_table("backfill_job_run")
    op.execute("UPDATE user_channel SET status = 'cancelled' WHERE status = 'failed'")
    _replace_user_channel_status_check(_OLD_USER_CHANNEL_STATUS)
