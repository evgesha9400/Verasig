"""multi-tenant API schema.

Adds user accounts, per-user Telegram/exchange/channel/risk/backtest/link state,
and scopes rule-driven projections by nullable user_id for the CLI transition.

Revision ID: 0006_multi_tenant_api
Revises: 0005_deletion_evidence
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_multi_tenant_api"
down_revision = "0005_deletion_evidence"
branch_labels = None
depends_on = None

_USER_FK = "user_account.id"
_CHANNEL_FK = "telegram_channel.channel_id"


def _add_unique_nulls_not_distinct(table: str, name: str, columns: list[str]) -> None:
    quoted = ", ".join(columns)
    op.execute(
        f"ALTER TABLE {table} ADD CONSTRAINT {name} "
        f"UNIQUE NULLS NOT DISTINCT ({quoted})"
    )


def upgrade() -> None:
    op.create_table(
        "user_account",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("plan", sa.String(), nullable=False),
        sa.Column("pending_email", sa.String(), nullable=True),
        sa.Column("cancel_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "plan IN ('observer', 'operator', 'desk')",
            name="ck_user_account_plan",
        ),
    )
    op.create_table(
        "user_telegram_link",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey(_USER_FK), primary_key=True),
        sa.Column("api_id", sa.Integer(), nullable=False),
        sa.Column("api_hash_encrypted", sa.Text(), nullable=False),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("session_string_encrypted", sa.Text(), nullable=True),
        sa.Column("phone_code_hash", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'connected')",
            name="ck_user_telegram_link_status",
        ),
    )
    op.create_table(
        "user_channel",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey(_USER_FK), primary_key=True),
        sa.Column(
            "channel_id", sa.BigInteger(), sa.ForeignKey(_CHANNEL_FK), primary_key=True
        ),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("verify_attempt", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('new', 'backfilling', 'backfilled', 'verified', "
            "'analyzed', 'cancelled')",
            name="ck_user_channel_status",
        ),
    )
    op.create_table(
        "user_exchange_connection",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey(_USER_FK), primary_key=True),
        sa.Column("exchange_id", sa.String(), primary_key=True),
        sa.Column("api_key_masked", sa.String(), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("api_secret_encrypted", sa.Text(), nullable=False),
        sa.Column("connected", sa.Boolean(), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "chat_risk_config",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey(_USER_FK), primary_key=True),
        sa.Column(
            "channel_id", sa.BigInteger(), sa.ForeignKey(_CHANNEL_FK), primary_key=True
        ),
        sa.Column("entry_mode", sa.String(), nullable=False),
        sa.Column("levels", sa.Integer(), nullable=False),
        sa.Column("weighting", sa.String(), nullable=False),
        sa.Column("exit_source", sa.String(), nullable=False),
        sa.Column("stop_pct", sa.Numeric(), nullable=False),
        sa.Column("tp_pct", sa.Numeric(), nullable=False),
        sa.Column("risk_pct", sa.Numeric(), nullable=False),
        sa.Column("leverage", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "backtest_result",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey(_USER_FK), nullable=False),
        sa.Column(
            "channel_id", sa.BigInteger(), sa.ForeignKey(_CHANNEL_FK), nullable=False
        ),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("win_rate", sa.Numeric(), nullable=False),
        sa.Column("pnl", sa.Numeric(), nullable=False),
        sa.Column("outcomes", postgresql.JSONB(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "lifecycle_link",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey(_USER_FK), nullable=False),
        sa.Column(
            "channel_id", sa.BigInteger(), sa.ForeignKey(_CHANNEL_FK), nullable=False
        ),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("root_signal_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id", "channel_id", "message_id", name="uq_lifecycle_link_msg"
        ),
    )

    op.add_column(
        "golden_label",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey(_USER_FK), nullable=True),
    )
    op.add_column(
        "golden_label",
        sa.Column("label", sa.String(), nullable=False, server_default="signal"),
    )
    op.alter_column("golden_label", "label", server_default=None)
    op.drop_constraint("uq_golden_label_msg", "golden_label", type_="unique")
    _add_unique_nulls_not_distinct(
        "golden_label",
        "uq_golden_label_user_msg",
        ["user_id", "channel_id", "message_id"],
    )

    op.add_column(
        "filter_rule",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey(_USER_FK), nullable=True),
    )
    op.add_column(
        "filter_rule",
        sa.Column(
            "display",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.alter_column("filter_rule", "display", server_default=None)
    _add_unique_nulls_not_distinct(
        "filter_rule",
        "uq_filter_rule_user_channel_version",
        ["user_id", "channel_id", "version"],
    )

    op.add_column(
        "parser_rule",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey(_USER_FK), nullable=True),
    )

    op.add_column(
        "extracted_signal",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey(_USER_FK), nullable=True),
    )
    op.drop_constraint("uq_extracted_signal_event", "extracted_signal", type_="unique")
    _add_unique_nulls_not_distinct(
        "extracted_signal",
        "uq_extracted_signal_user_event",
        ["user_id", "event_id"],
    )

    op.add_column(
        "unrecognized_signal",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey(_USER_FK), nullable=True),
    )
    op.drop_constraint(
        "uq_unrecognized_signal_event", "unrecognized_signal", type_="unique"
    )
    _add_unique_nulls_not_distinct(
        "unrecognized_signal",
        "uq_unrecognized_signal_user_event",
        ["user_id", "event_id"],
    )

    op.add_column(
        "parser_drift_warning",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey(_USER_FK), nullable=True),
    )
    op.drop_constraint("uq_parser_drift_event", "parser_drift_warning", type_="unique")
    _add_unique_nulls_not_distinct(
        "parser_drift_warning",
        "uq_parser_drift_user_event",
        ["user_id", "event_id"],
    )

    op.add_column(
        "filter_drift_warning",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey(_USER_FK), nullable=True),
    )
    op.drop_constraint("uq_filter_drift_msg", "filter_drift_warning", type_="unique")
    _add_unique_nulls_not_distinct(
        "filter_drift_warning",
        "uq_filter_drift_user_msg",
        ["user_id", "channel_id", "message_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_filter_drift_user_msg", "filter_drift_warning", type_="unique"
    )
    op.create_unique_constraint(
        "uq_filter_drift_msg", "filter_drift_warning", ["channel_id", "message_id"]
    )
    op.drop_column("filter_drift_warning", "user_id")

    op.drop_constraint(
        "uq_parser_drift_user_event", "parser_drift_warning", type_="unique"
    )
    op.create_unique_constraint(
        "uq_parser_drift_event", "parser_drift_warning", ["event_id"]
    )
    op.drop_column("parser_drift_warning", "user_id")

    op.drop_constraint(
        "uq_unrecognized_signal_user_event", "unrecognized_signal", type_="unique"
    )
    op.create_unique_constraint(
        "uq_unrecognized_signal_event", "unrecognized_signal", ["event_id"]
    )
    op.drop_column("unrecognized_signal", "user_id")

    op.drop_constraint(
        "uq_extracted_signal_user_event", "extracted_signal", type_="unique"
    )
    op.create_unique_constraint(
        "uq_extracted_signal_event", "extracted_signal", ["event_id"]
    )
    op.drop_column("extracted_signal", "user_id")

    op.drop_column("parser_rule", "user_id")

    op.drop_constraint(
        "uq_filter_rule_user_channel_version", "filter_rule", type_="unique"
    )
    op.drop_column("filter_rule", "display")
    op.drop_column("filter_rule", "user_id")

    op.drop_constraint("uq_golden_label_user_msg", "golden_label", type_="unique")
    op.create_unique_constraint(
        "uq_golden_label_msg", "golden_label", ["channel_id", "message_id"]
    )
    op.drop_column("golden_label", "label")
    op.drop_column("golden_label", "user_id")

    op.drop_table("lifecycle_link")
    op.drop_table("backtest_result")
    op.drop_table("chat_risk_config")
    op.drop_table("user_exchange_connection")
    op.drop_table("user_channel")
    op.drop_table("user_telegram_link")
    op.drop_table("user_account")
