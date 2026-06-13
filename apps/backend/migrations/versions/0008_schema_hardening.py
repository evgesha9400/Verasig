"""harden user-scoped persisted schema.

Revision ID: 0008_schema_hardening
Revises: 0007_drop_golden_label_is_signal
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_schema_hardening"
down_revision = "0007_drop_golden_label_is_signal"
branch_labels = None
depends_on = None

_USER_SCOPED_TABLES = (
    "golden_label",
    "filter_rule",
    "parser_rule",
    "extracted_signal",
    "unrecognized_signal",
    "parser_drift_warning",
    "filter_drift_warning",
)

_USER_SCOPED_UNIQUES = (
    (
        "golden_label",
        "uq_golden_label_user_msg",
        ["user_id", "channel_id", "message_id"],
    ),
    (
        "filter_rule",
        "uq_filter_rule_user_channel_version",
        ["user_id", "channel_id", "version"],
    ),
    ("extracted_signal", "uq_extracted_signal_user_event", ["user_id", "event_id"]),
    (
        "unrecognized_signal",
        "uq_unrecognized_signal_user_event",
        ["user_id", "event_id"],
    ),
    (
        "parser_drift_warning",
        "uq_parser_drift_user_event",
        ["user_id", "event_id"],
    ),
    (
        "filter_drift_warning",
        "uq_filter_drift_user_msg",
        ["user_id", "channel_id", "message_id"],
    ),
)

_CHECK_CONSTRAINTS = (
    (
        "golden_label",
        "ck_golden_label_label",
        "label IN ('signal', 'noise', 'modifier')",
    ),
    (
        "extracted_signal",
        "ck_extracted_signal_side",
        "side IN ('LONG', 'SHORT')",
    ),
    (
        "extracted_signal",
        "ck_extracted_signal_event_type",
        "event_type IN ('NEW_ENTRY', 'MODIFY', 'CLOSE', 'UNRECOGNIZED')",
    ),
    (
        "extracted_signal",
        "ck_extracted_signal_extraction_method",
        "extraction_method IN ('DETERMINISTIC', 'LLM_FALLBACK')",
    ),
    (
        "deleted_signal_evidence",
        "ck_deleted_signal_evidence_confidence",
        "confidence IN ('CONFIRMED', 'SUSPECTED')",
    ),
    (
        "deleted_signal_evidence",
        "ck_deleted_signal_evidence_method",
        "method IN ('SNAPSHOT_DIFF', 'ID_GAP', 'LIVE_EVENT')",
    ),
    (
        "chat_risk_config",
        "ck_chat_risk_config_entry_mode",
        "entry_mode IN ('first', 'mid', 'ladder')",
    ),
    (
        "chat_risk_config",
        "ck_chat_risk_config_weighting",
        "weighting IN ('equal', 'martingale')",
    ),
    (
        "chat_risk_config",
        "ck_chat_risk_config_exit_source",
        "exit_source IN ('signal', 'custom')",
    ),
)

_CAPTURED_MESSAGE_FOREIGN_KEYS = (
    ("raw_signal_event", "fk_raw_signal_event_message"),
    ("golden_label", "fk_golden_label_message"),
    ("filter_drift_warning", "fk_filter_drift_warning_message"),
)

_INDEXES = (
    (
        "ix_backtest_result_user_channel_completed",
        "backtest_result",
        ["user_id", "channel_id", "completed_at"],
    ),
    (
        "ix_extracted_signal_user_channel",
        "extracted_signal",
        ["user_id", "channel_id"],
    ),
    (
        "ix_unrecognized_signal_user_event",
        "unrecognized_signal",
        ["user_id", "event_id"],
    ),
    ("ix_parser_rule_user_channel", "parser_rule", ["user_id", "channel_id"]),
    ("ix_filter_rule_user_channel", "filter_rule", ["user_id", "channel_id"]),
    (
        "ix_deleted_signal_evidence_channel",
        "deleted_signal_evidence",
        ["channel_id"],
    ),
    (
        "ix_parser_drift_warning_user_channel",
        "parser_drift_warning",
        ["user_id", "channel_id"],
    ),
    (
        "ix_filter_drift_warning_user_channel",
        "filter_drift_warning",
        ["user_id", "channel_id"],
    ),
)


def _abort_if_user_scope_is_null() -> None:
    connection = op.get_bind()
    for table in _USER_SCOPED_TABLES:
        has_null_user_id = connection.execute(
            sa.text(f"SELECT 1 FROM {table} WHERE user_id IS NULL LIMIT 1")
        ).first()
        if has_null_user_id:
            raise RuntimeError(
                f"schema hardening aborted: {table}.user_id contains NULL values"
            )


def _set_user_id_nullable(nullable: bool) -> None:
    for table in _USER_SCOPED_TABLES:
        op.alter_column(
            table,
            "user_id",
            existing_type=sa.Uuid(),
            nullable=nullable,
        )


def _add_unique_nulls_not_distinct(table: str, name: str, columns: list[str]) -> None:
    quoted = ", ".join(columns)
    op.execute(
        f"ALTER TABLE {table} ADD CONSTRAINT {name} "
        f"UNIQUE NULLS NOT DISTINCT ({quoted})"
    )


def _replace_unique_nulls_not_distinct() -> None:
    for table, name, columns in _USER_SCOPED_UNIQUES:
        op.drop_constraint(name, table, type_="unique")
        op.create_unique_constraint(name, table, columns)


def _restore_unique_nulls_not_distinct() -> None:
    for table, name, columns in _USER_SCOPED_UNIQUES:
        op.drop_constraint(name, table, type_="unique")
        _add_unique_nulls_not_distinct(table, name, columns)


def _create_check_constraints() -> None:
    for table, name, condition in _CHECK_CONSTRAINTS:
        op.create_check_constraint(name, table, condition)


def _drop_check_constraints() -> None:
    for table, name, _condition in reversed(_CHECK_CONSTRAINTS):
        op.drop_constraint(name, table, type_="check")


def _create_foreign_keys() -> None:
    for table, name in _CAPTURED_MESSAGE_FOREIGN_KEYS:
        op.create_foreign_key(
            name,
            table,
            "raw_telegram_message",
            ["channel_id", "message_id"],
            ["channel_id", "message_id"],
        )
    op.create_foreign_key(
        "fk_lifecycle_link_root_signal",
        "lifecycle_link",
        "extracted_signal",
        ["root_signal_id"],
        ["id"],
        ondelete="CASCADE",
    )


def _drop_foreign_keys() -> None:
    op.drop_constraint(
        "fk_lifecycle_link_root_signal", "lifecycle_link", type_="foreignkey"
    )
    for table, name in reversed(_CAPTURED_MESSAGE_FOREIGN_KEYS):
        op.drop_constraint(name, table, type_="foreignkey")


def _create_indexes() -> None:
    for name, table, columns in _INDEXES:
        op.create_index(name, table, columns)


def _drop_indexes() -> None:
    for name, table, _columns in reversed(_INDEXES):
        op.drop_index(name, table_name=table)


def upgrade() -> None:
    _abort_if_user_scope_is_null()
    _replace_unique_nulls_not_distinct()
    _set_user_id_nullable(nullable=False)
    _create_check_constraints()
    _create_foreign_keys()
    _create_indexes()


def downgrade() -> None:
    _drop_indexes()
    _drop_foreign_keys()
    _drop_check_constraints()
    _set_user_id_nullable(nullable=True)
    _restore_unique_nulls_not_distinct()
