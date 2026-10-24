"""Initial schema baseline.

Replaces the previous 22-migration chain (0001_baseline …
0022_collapse_event_and_signal). That chain accumulated create-then-drop churn
from schema iteration and was worthless to replay for the two populated
environments — every step just reconstructs intermediate shapes nothing
running today depends on. This single migration creates the CURRENT schema
directly, verified byte-identical (via `pg_dump --schema-only` diff) to what
the old chain produced at its head.

Populated databases are `alembic stamp`-ed to this revision, not rebuilt from it.

Revision ID: 0001_init
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_account",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("plan", sa.String(), nullable=False),
        sa.Column("pending_email", sa.String(), nullable=True),
        sa.Column("cancel_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "plan IN ('observer', 'operator', 'desk')", name="ck_user_account_plan"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "parser_overlay",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name="fk_parser_overlay_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "source",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "config_encrypted", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("name IN ('Telegram')", name="ck_source_name"),
        sa.CheckConstraint(
            "status IN ('pending', 'connected')", name="ck_source_status"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user_account.id"], name="fk_source_user", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_source_user_name"),
    )
    op.create_table(
        "user_exchange_connection",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("exchange_id", sa.String(), nullable=False),
        sa.Column("api_key_masked", sa.String(), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("api_secret_encrypted", sa.Text(), nullable=False),
        sa.Column("connected", sa.Boolean(), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "exchange_id"),
    )
    op.create_table(
        "feed",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "captured_through_external_message_id", sa.BigInteger(), nullable=True
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("history_depth", sa.String(), server_default="1y", nullable=False),
        sa.Column(
            "capture_generation",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.CheckConstraint(
            "history_depth IN ('6m', '1y', 'all')", name="ck_feed_history_depth"
        ),
        sa.CheckConstraint(
            "status IN ('new', 'backfilling', 'backfilled', 'verified', "
            "'analyzed', 'cancelled', 'failed')",
            name="ck_feed_status",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["source.id"], name="fk_feed_source", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "external_id", name="user_channel_pkey"),
    )
    op.create_table(
        "backfill_job_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_count", sa.Integer(), nullable=False),
        sa.Column("oldest_posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cursor_external_message_id", sa.BigInteger(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("previous_feed_status", sa.String(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'cancelled')",
            name="ck_backfill_job_run_status",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "external_id"],
            ["feed.user_id", "feed.external_id"],
            name="fk_backfill_job_run_feed",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_backfill_job_run_status", "backfill_job_run", ["status"], unique=False
    )
    op.create_index(
        "ix_backfill_job_run_user_channel_started",
        "backfill_job_run",
        ["user_id", "external_id", "started_at"],
        unique=False,
    )
    op.create_table(
        "backtest_result",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.BigInteger(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("win_rate", sa.Numeric(), nullable=False),
        sa.Column("pnl", sa.Numeric(), nullable=False),
        sa.Column("outcomes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id", "external_id"],
            ["feed.user_id", "feed.external_id"],
            name="fk_backtest_result_feed",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_backtest_result_user_channel_completed",
        "backtest_result",
        ["user_id", "external_id", "completed_at"],
        unique=False,
    )
    op.create_table(
        "deleted_signal_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.BigInteger(), nullable=False),
        sa.Column("external_message_id", sa.BigInteger(), nullable=False),
        sa.Column("confidence", sa.String(), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("was_signal_candidate", sa.Boolean(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "confidence IN ('CONFIRMED', 'SUSPECTED')",
            name="ck_deleted_signal_evidence_confidence",
        ),
        sa.CheckConstraint(
            "method IN ('SNAPSHOT_DIFF', 'ID_GAP', 'LIVE_EVENT')",
            name="ck_deleted_signal_evidence_method",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "external_id"],
            ["feed.user_id", "feed.external_id"],
            name="fk_deleted_signal_evidence_feed",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "external_id",
            "external_message_id",
            name="uq_deleted_evidence_msg",
        ),
    )
    op.create_index(
        "ix_deleted_signal_evidence_channel",
        "deleted_signal_evidence",
        ["user_id", "external_id"],
        unique=False,
    )
    op.create_table(
        "feed_risk_config",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.BigInteger(), nullable=False),
        sa.Column("entry_mode", sa.String(), nullable=False),
        sa.Column("levels", sa.Integer(), nullable=False),
        sa.Column("weighting", sa.String(), nullable=False),
        sa.Column("exit_source", sa.String(), nullable=False),
        sa.Column("stop_pct", sa.Numeric(), nullable=False),
        sa.Column("tp_pct", sa.Numeric(), nullable=False),
        sa.Column("risk_pct", sa.Numeric(), nullable=False),
        sa.Column("leverage", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "entry_mode IN ('first', 'mid', 'ladder')",
            name="ck_feed_risk_config_entry_mode",
        ),
        sa.CheckConstraint(
            "exit_source IN ('signal', 'custom')",
            name="ck_feed_risk_config_exit_source",
        ),
        sa.CheckConstraint(
            "weighting IN ('equal', 'martingale')", name="ck_feed_risk_config_weighting"
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "external_id"],
            ["feed.user_id", "feed.external_id"],
            name="fk_feed_risk_config_feed",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "external_id", name="chat_risk_config_pkey"),
    )
    op.create_table(
        "mining_review",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.BigInteger(), nullable=False),
        sa.Column("input_revision", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("overlay", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "accepted_template_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "missed_message_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id", "external_id"],
            ["feed.user_id", "feed.external_id"],
            name="fk_mining_review_feed",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name="fk_mining_review_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mining_review_feed_created",
        "mining_review",
        ["user_id", "external_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "raw_message",
        sa.Column("external_id", sa.BigInteger(), nullable=False),
        sa.Column("external_message_id", sa.BigInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("sender_id", sa.BigInteger(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reply_to_external_message_id", sa.BigInteger(), nullable=True),
        sa.Column("edit_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("has_media", sa.Boolean(), nullable=False),
        sa.Column("views", sa.Integer(), nullable=True),
        sa.Column("forwards", sa.Integer(), nullable=True),
        sa.Column(
            "raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id", "external_id"],
            ["feed.user_id", "feed.external_id"],
            name="fk_raw_message_feed",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "external_id", "external_message_id"),
    )
    op.create_table(
        "signal",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.BigInteger(), nullable=False),
        sa.Column("external_message_id", sa.BigInteger(), nullable=False),
        sa.Column("candidate_text", sa.Text(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("entry_type", sa.String(), nullable=True),
        sa.Column("entry_low", sa.Numeric(), nullable=True),
        sa.Column("entry_high", sa.Numeric(), nullable=True),
        sa.Column("stop_loss", sa.Numeric(), nullable=True),
        sa.Column(
            "take_profits", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("leverage", sa.Numeric(), nullable=True),
        sa.Column("confidence", sa.Numeric(), nullable=True),
        sa.Column("rule_id", sa.String(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('NEW_ENTRY', 'MODIFY', 'CLOSE')",
            name="ck_signal_event_type",
        ),
        sa.CheckConstraint("side IN ('LONG', 'SHORT')", name="ck_signal_side"),
        sa.ForeignKeyConstraint(
            ["user_id", "external_id", "external_message_id"],
            [
                "raw_message.user_id",
                "raw_message.external_id",
                "raw_message.external_message_id",
            ],
            name="fk_signal_message",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "external_id"],
            ["feed.user_id", "feed.external_id"],
            name="fk_signal_feed",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "external_id", "external_message_id", name="uq_signal_msg"
        ),
    )
    op.create_index(
        "ix_signal_user_channel", "signal", ["user_id", "external_id"], unique=False
    )
    op.create_table(
        "lifecycle_link",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.BigInteger(), nullable=False),
        sa.Column("external_message_id", sa.BigInteger(), nullable=False),
        sa.Column("root_signal_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["root_signal_id"],
            ["signal.id"],
            name="fk_lifecycle_link_root_signal",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "external_id"],
            ["feed.user_id", "feed.external_id"],
            name="fk_lifecycle_link_feed",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "external_id",
            "external_message_id",
            name="uq_lifecycle_link_msg",
        ),
    )


def downgrade() -> None:
    op.drop_table("lifecycle_link")
    op.drop_index("ix_signal_user_channel", table_name="signal")
    op.drop_table("signal")
    op.drop_table("raw_message")
    op.drop_index("ix_mining_review_feed_created", table_name="mining_review")
    op.drop_table("mining_review")
    op.drop_table("feed_risk_config")
    op.drop_index(
        "ix_deleted_signal_evidence_channel", table_name="deleted_signal_evidence"
    )
    op.drop_table("deleted_signal_evidence")
    op.drop_index(
        "ix_backtest_result_user_channel_completed", table_name="backtest_result"
    )
    op.drop_table("backtest_result")
    op.drop_index(
        "ix_backfill_job_run_user_channel_started", table_name="backfill_job_run"
    )
    op.drop_index("ix_backfill_job_run_status", table_name="backfill_job_run")
    op.drop_table("backfill_job_run")
    op.drop_table("feed")
    op.drop_table("user_exchange_connection")
    op.drop_table("source")
    op.drop_table("parser_overlay")
    op.drop_table("user_account")
