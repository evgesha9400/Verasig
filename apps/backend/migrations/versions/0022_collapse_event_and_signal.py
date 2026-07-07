"""Collapse raw_signal_event + extracted_signal into one signal table.

`raw_signal_event` was never raw capture (`raw_message` is that) — post-0021,
the miner is the only extractor, and Confirm persists a candidate message and
its extracted trade together, 1:1, in one transaction. That is two tables for
one write. This migration collapses them into one `signal` table keyed by
message: every persisted `signal` IS an extraction (there are no stored
"misses" — removed in 0021).

The backfill is an INNER JOIN on `raw_signal_event.id = extracted_signal.event_id`,
so a `raw_signal_event` with no matching `extracted_signal` is dropped, not
carried forward. The dev DB has 961 such rows — stale legacy "miss" events from
the removed pipeline (the old event/miss materialization this repo no longer
runs) — and dropping them is correct and intended, not data loss of anything
this system still produces.

`extracted_signal.id` is preserved as `signal.id` so `lifecycle_link.root_signal_id`
(and any external reference to a signal id) stays valid across the migration.

Revision ID: 0022_collapse_event_and_signal
Revises: 0021_drop_unrecognized
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0022_collapse_event_and_signal"
down_revision = "0021_drop_unrecognized"
branch_labels = None
depends_on = None

_MESSAGE_COLS = ["user_id", "external_id", "external_message_id"]
_FEED_COLS = ["user_id", "external_id"]

_LIFECYCLE_LINK_FK = "fk_lifecycle_link_root_signal"


def upgrade() -> None:
    op.create_table(
        "signal",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("user_account.id", ondelete="CASCADE"),
            nullable=False,
        ),
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
        sa.Column("take_profits", JSONB(), nullable=False),
        sa.Column("leverage", sa.Numeric(), nullable=True),
        sa.Column("confidence", sa.Numeric(), nullable=True),
        sa.Column("rule_id", sa.String(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id", "external_id", "external_message_id", name="uq_signal_msg"
        ),
        sa.CheckConstraint("side IN ('LONG', 'SHORT')", name="ck_signal_side"),
        sa.CheckConstraint(
            "event_type IN ('NEW_ENTRY', 'MODIFY', 'CLOSE')",
            name="ck_signal_event_type",
        ),
    )
    op.create_foreign_key(
        "fk_signal_message",
        "signal",
        "raw_message",
        _MESSAGE_COLS,
        _MESSAGE_COLS,
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_signal_feed",
        "signal",
        "feed",
        _FEED_COLS,
        _FEED_COLS,
        ondelete="CASCADE",
    )
    op.create_index("ix_signal_user_channel", "signal", ["user_id", "external_id"])

    op.execute(
        sa.text(
            """
            INSERT INTO signal (
                id, user_id, external_id, external_message_id, candidate_text,
                symbol, side, event_type, entry_type, entry_low, entry_high,
                stop_loss, take_profits, leverage, confidence, rule_id,
                extracted_at, created_at
            )
            SELECT
                e.id, e.user_id, e.external_id, r.external_message_id,
                r.candidate_text, e.symbol, e.side, e.event_type, e.entry_type,
                e.entry_low, e.entry_high, e.stop_loss, e.take_profits,
                e.leverage, e.confidence, e.rule_id, e.extracted_at, r.created_at
            FROM extracted_signal e
            JOIN raw_signal_event r ON r.id = e.event_id
            """
        )
    )

    op.drop_constraint(_LIFECYCLE_LINK_FK, "lifecycle_link", type_="foreignkey")
    op.create_foreign_key(
        _LIFECYCLE_LINK_FK,
        "lifecycle_link",
        "signal",
        ["root_signal_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_table("extracted_signal")
    op.drop_table("raw_signal_event")


def downgrade() -> None:
    op.create_table(
        "raw_signal_event",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.BigInteger(), nullable=False),
        sa.Column("external_message_id", sa.BigInteger(), nullable=False),
        sa.Column("candidate_text", sa.Text(), nullable=False),
        sa.Column("materialized_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id",
            "external_id",
            "external_message_id",
            name="uq_raw_signal_event_msg",
        ),
    )
    op.create_foreign_key(
        "fk_raw_signal_event_message",
        "raw_signal_event",
        "raw_message",
        _MESSAGE_COLS,
        _MESSAGE_COLS,
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_raw_signal_event_feed",
        "raw_signal_event",
        "feed",
        _FEED_COLS,
        _FEED_COLS,
        ondelete="CASCADE",
    )

    op.create_table(
        "extracted_signal",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey(
                "user_account.id",
                ondelete="CASCADE",
                name="extracted_signal_user_id_fkey",
            ),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey(
                "raw_signal_event.id",
                ondelete="CASCADE",
                name="fk_extracted_signal_event",
            ),
            nullable=False,
        ),
        sa.Column("external_id", sa.BigInteger(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("entry_type", sa.String(), nullable=True),
        sa.Column("entry_low", sa.Numeric(), nullable=True),
        sa.Column("entry_high", sa.Numeric(), nullable=True),
        sa.Column("stop_loss", sa.Numeric(), nullable=True),
        sa.Column("take_profits", JSONB(), nullable=False),
        sa.Column("leverage", sa.Numeric(), nullable=True),
        sa.Column("confidence", sa.Numeric(), nullable=True),
        sa.Column("rule_id", sa.String(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id", "event_id", name="uq_extracted_signal_user_event"
        ),
        sa.CheckConstraint("side IN ('LONG', 'SHORT')", name="ck_extracted_signal_side"),
        sa.CheckConstraint(
            "event_type IN ('NEW_ENTRY', 'MODIFY', 'CLOSE')",
            name="ck_extracted_signal_event_type",
        ),
    )
    op.create_index(
        "ix_extracted_signal_user_channel", "extracted_signal", ["user_id", "external_id"]
    )

    # Split each signal back into its (event, extraction) pair: `extracted_signal`
    # keeps the signal's own id (round-tripping the identity `upgrade` preserved),
    # `raw_signal_event` gets a fresh id per row — the original event id was not
    # kept anywhere once the tables merged, so it cannot be recovered.
    op.execute(
        sa.text(
            """
            WITH inserted_events AS (
                INSERT INTO raw_signal_event (
                    id, user_id, external_id, external_message_id, candidate_text,
                    materialized_by, created_at
                )
                SELECT
                    gen_random_uuid(), s.user_id, s.external_id,
                    s.external_message_id, s.candidate_text, 'MINING', s.created_at
                FROM signal s
                RETURNING id, user_id, external_id, external_message_id
            )
            INSERT INTO extracted_signal (
                id, user_id, event_id, external_id, symbol, side, event_type,
                entry_type, entry_low, entry_high, stop_loss, take_profits,
                leverage, confidence, rule_id, extracted_at
            )
            SELECT
                s.id, s.user_id, ie.id, s.external_id, s.symbol, s.side,
                s.event_type, s.entry_type, s.entry_low, s.entry_high,
                s.stop_loss, s.take_profits, s.leverage, s.confidence,
                s.rule_id, s.extracted_at
            FROM signal s
            JOIN inserted_events ie
                ON ie.user_id = s.user_id
                AND ie.external_id = s.external_id
                AND ie.external_message_id = s.external_message_id
            """
        )
    )

    op.drop_constraint(_LIFECYCLE_LINK_FK, "lifecycle_link", type_="foreignkey")
    op.create_foreign_key(
        _LIFECYCLE_LINK_FK,
        "lifecycle_link",
        "extracted_signal",
        ["root_signal_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_table("signal")
