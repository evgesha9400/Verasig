"""Collapse the shared-channel cache into a user-owned, generic feed model.

Merges `user_channel` (membership) + `telegram_channel` (stream metadata + cursor)
into one user-owned `feed`; renames `raw_telegram_message`->`raw_message` and
`chat_risk_config`->`feed_risk_config`; renames provider ids `channel_id`->
`external_id` and `message_id`->`external_message_id` everywhere; adds `user_id`
to the capture tables; and re-roots every channel-scoped FK at
`feed(user_id, external_id)` with ON DELETE CASCADE (event children cascade via
their event_id FK). Deleting a feed now purges all of that user's capture +
derived rows, so re-adding starts a fresh backfill from a NULL cursor.

Single-user invariant: each channel has exactly one subscriber, so `user_id` is
backfilled from `user_channel`; capture for a channel nobody subscribes to (an
orphan left by the old delete) is purged.

Revision ID: 0010_user_owned_feed
Revises: 0009_backfill_job_runs
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB

revision = "0010_user_owned_feed"
down_revision = "0009_backfill_job_runs"
branch_labels = None
depends_on = None

# tables gaining user_id (were channel-global), keyed by their channel column
_CAPTURE_TABLES = (
    "raw_telegram_message",
    "raw_signal_event",
    "deleted_signal_evidence",
)

# single-column channel_id FK -> composite (user_id, external_id) FK on feed.
# (table-before-rename, new fk name)
_CHANNEL_FKS = (
    ("raw_message", "fk_raw_message_feed"),
    ("raw_signal_event", "fk_raw_signal_event_feed"),
    ("filter_rule", "fk_filter_rule_feed"),
    ("parser_rule", "fk_parser_rule_feed"),
    ("golden_label", "fk_golden_label_feed"),
    ("filter_drift_warning", "fk_filter_drift_warning_feed"),
    ("deleted_signal_evidence", "fk_deleted_signal_evidence_feed"),
    ("backfill_job_run", "fk_backfill_job_run_feed"),
    ("feed_risk_config", "fk_feed_risk_config_feed"),
    ("backtest_result", "fk_backtest_result_feed"),
    ("lifecycle_link", "fk_lifecycle_link_feed"),
)

# composite (external_id, external_message_id) FK -> raw_message; named in 0008
_MESSAGE_FKS = (
    ("raw_signal_event", "fk_raw_signal_event_message"),
    ("golden_label", "fk_golden_label_message"),
    ("filter_drift_warning", "fk_filter_drift_warning_message"),
)

# (table, column, referred_table, referred_column, new fk name) re-pointed CASCADE
_CASCADE_FKS = (
    (
        "extracted_signal",
        "event_id",
        "raw_signal_event",
        "id",
        "fk_extracted_signal_event",
    ),
    (
        "unrecognized_signal",
        "event_id",
        "raw_signal_event",
        "id",
        "fk_unrecognized_signal_event",
    ),
    (
        "parser_drift_warning",
        "event_id",
        "raw_signal_event",
        "id",
        "fk_parser_drift_warning_event",
    ),
    (
        "filter_drift_warning",
        "event_id",
        "raw_signal_event",
        "id",
        "fk_filter_drift_warning_event",
    ),
    (
        "filter_drift_warning",
        "source_label_id",
        "golden_label",
        "id",
        "fk_filter_drift_warning_source_label",
    ),
)

# (table, [(old_col, new_col), ...]) applied after the table renames below
_COLUMN_RENAMES = (
    ("feed", [("channel_id", "external_id")]),
    (
        "raw_message",
        [
            ("channel_id", "external_id"),
            ("message_id", "external_message_id"),
            ("reply_to_message_id", "reply_to_external_message_id"),
        ],
    ),
    (
        "raw_signal_event",
        [("channel_id", "external_id"), ("message_id", "external_message_id")],
    ),
    (
        "deleted_signal_evidence",
        [("channel_id", "external_id"), ("message_id", "external_message_id")],
    ),
    ("extracted_signal", [("channel_id", "external_id")]),
    (
        "golden_label",
        [("channel_id", "external_id"), ("message_id", "external_message_id")],
    ),
    (
        "filter_drift_warning",
        [("channel_id", "external_id"), ("message_id", "external_message_id")],
    ),
    ("parser_drift_warning", [("channel_id", "external_id")]),
    (
        "lifecycle_link",
        [("channel_id", "external_id"), ("message_id", "external_message_id")],
    ),
    ("filter_rule", [("channel_id", "external_id")]),
    ("parser_rule", [("channel_id", "external_id")]),
    ("backtest_result", [("channel_id", "external_id")]),
    (
        "backfill_job_run",
        [
            ("channel_id", "external_id"),
            ("cursor_message_id", "cursor_external_message_id"),
        ],
    ),
    ("feed_risk_config", [("channel_id", "external_id")]),
)

_RENAMED_CHECKS = (
    ("feed", "ck_user_channel_status", "ck_feed_status"),
    (
        "feed_risk_config",
        "ck_chat_risk_config_entry_mode",
        "ck_feed_risk_config_entry_mode",
    ),
    (
        "feed_risk_config",
        "ck_chat_risk_config_weighting",
        "ck_feed_risk_config_weighting",
    ),
    (
        "feed_risk_config",
        "ck_chat_risk_config_exit_source",
        "ck_feed_risk_config_exit_source",
    ),
)


def _drop_fk_on_columns(table: str, columns: list[str]) -> None:
    inspector = inspect(op.get_bind())
    for fk in inspector.get_foreign_keys(table):
        if fk["constrained_columns"] == columns:
            op.drop_constraint(fk["name"], table, type_="foreignkey")
            return
    raise RuntimeError(f"0010: no FK on {table}{columns} to drop")


def _drop_pk(table: str) -> None:
    op.drop_constraint(
        inspect(op.get_bind()).get_pk_constraint(table)["name"], table, type_="primary"
    )


def upgrade() -> None:
    duplicate = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT channel_id FROM user_channel "
                "GROUP BY channel_id HAVING COUNT(*) > 1 LIMIT 1"
            )
        )
        .first()
    )
    if duplicate is not None:
        raise RuntimeError(
            f"0010 aborted: channel {duplicate[0]} has >1 subscriber; the user-owned "
            "migration assumes a single owner per channel"
        )

    for table in _CAPTURE_TABLES:
        op.add_column(table, sa.Column("user_id", sa.Uuid(), nullable=True))
        op.execute(
            sa.text(
                f"UPDATE {table} t SET user_id = uc.user_id "
                f"FROM user_channel uc WHERE uc.channel_id = t.channel_id"
            )
        )

    # drop every FK + parent PK we will re-root, on pre-rename names/columns
    for name, table in (
        ("fk_raw_signal_event_message", "raw_signal_event"),
        ("fk_golden_label_message", "golden_label"),
        ("fk_filter_drift_warning_message", "filter_drift_warning"),
    ):
        op.drop_constraint(name, table, type_="foreignkey")
    for table in (
        "raw_telegram_message",
        "raw_signal_event",
        "filter_rule",
        "parser_rule",
        "golden_label",
        "filter_drift_warning",
        "deleted_signal_evidence",
        "user_channel",
        "backfill_job_run",
        "chat_risk_config",
        "backtest_result",
        "lifecycle_link",
    ):
        _drop_fk_on_columns(table, ["channel_id"])
    for table, column, *_rest in _CASCADE_FKS:
        _drop_fk_on_columns(table, [column])
    _drop_pk("raw_telegram_message")

    op.rename_table("user_channel", "feed")
    op.rename_table("raw_telegram_message", "raw_message")
    op.rename_table("chat_risk_config", "feed_risk_config")
    for table, renames in _COLUMN_RENAMES:
        for old, new in renames:
            op.alter_column(table, old, new_column_name=new)

    op.add_column("feed", sa.Column("title", sa.String(), nullable=True))
    op.add_column(
        "feed",
        sa.Column("metadata", JSONB(), nullable=True, server_default="{}"),
    )
    op.add_column(
        "feed",
        sa.Column(
            "captured_through_external_message_id", sa.BigInteger(), nullable=True
        ),
    )
    op.add_column(
        "feed", sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute(
        sa.text(
            "UPDATE feed f SET title = tc.title, first_seen_at = tc.first_seen_at, "
            "captured_through_external_message_id = tc.captured_through_message_id, "
            "metadata = jsonb_build_object('handle', tc.handle, 'is_private', "
            "tc.is_private, 'subscriber_count', tc.subscriber_count) "
            "FROM telegram_channel tc WHERE tc.channel_id = f.external_id"
        )
    )

    op.create_primary_key(
        "raw_message_pkey",
        "raw_message",
        ["user_id", "external_id", "external_message_id"],
    )

    for table, name in _CHANNEL_FKS:
        op.create_foreign_key(
            name,
            table,
            "feed",
            ["user_id", "external_id"],
            ["user_id", "external_id"],
            ondelete="CASCADE",
        )
    for table, name in _MESSAGE_FKS:
        op.create_foreign_key(
            name,
            table,
            "raw_message",
            ["user_id", "external_id", "external_message_id"],
            ["user_id", "external_id", "external_message_id"],
            ondelete="CASCADE",
        )
    for table, column, referred_table, referred_column, name in _CASCADE_FKS:
        op.create_foreign_key(
            name, table, referred_table, [column], [referred_column], ondelete="CASCADE"
        )

    op.drop_constraint("uq_raw_signal_event_msg", "raw_signal_event", type_="unique")
    op.create_unique_constraint(
        "uq_raw_signal_event_msg",
        "raw_signal_event",
        ["user_id", "external_id", "external_message_id"],
    )
    op.drop_constraint(
        "uq_deleted_evidence_msg", "deleted_signal_evidence", type_="unique"
    )
    op.create_unique_constraint(
        "uq_deleted_evidence_msg",
        "deleted_signal_evidence",
        ["user_id", "external_id", "external_message_id"],
    )
    op.drop_index(
        "ix_deleted_signal_evidence_channel", table_name="deleted_signal_evidence"
    )
    op.create_index(
        "ix_deleted_signal_evidence_channel",
        "deleted_signal_evidence",
        ["user_id", "external_id"],
    )

    for table, old, new in _RENAMED_CHECKS:
        op.execute(sa.text(f"ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new}"))

    # purge orphan capture (channels nobody subscribes to); event children cascade
    op.execute(sa.text("DELETE FROM raw_signal_event WHERE user_id IS NULL"))
    op.execute(sa.text("DELETE FROM deleted_signal_evidence WHERE user_id IS NULL"))
    op.execute(sa.text("DELETE FROM raw_message WHERE user_id IS NULL"))
    op.drop_table("telegram_channel")

    for table in ("raw_message", "raw_signal_event", "deleted_signal_evidence"):
        op.alter_column(table, "user_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column("feed", "title", existing_type=sa.String(), nullable=False)
    op.alter_column("feed", "metadata", existing_type=JSONB(), nullable=False)
    op.alter_column(
        "feed",
        "first_seen_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.alter_column("feed", "metadata", server_default=None)


def downgrade() -> None:
    raise NotImplementedError(
        "0010 is a destructive merge (telegram_channel dropped); forward-only."
    )
