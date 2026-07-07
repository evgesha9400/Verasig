"""Append-only ORM rows mirroring the §2 contracts 1:1.

The capture layer is **user-owned and provider-agnostic**: a `feed` is a stream a
user follows (merging the old `user_channel` membership with the old
`telegram_channel` metadata + backfill cursor); `raw_message` is insert-only
(composite PK gives idempotent dedup). Provider-specific ids are stored
generically as `external_id` / `external_message_id`; Telegram-specific stream
metadata (handle, is_private, subscriber_count) lives in `feed.metadata` (JSONB).
Every capture + derived row carries `user_id`, and all channel-scoped FKs cascade
from `feed`, so deleting a feed purges everything beneath it for that user and a
re-add starts a fresh backfill from a NULL cursor.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from verasig.foundation.database.session import Base

_FEED_FK = ("user_id", "external_id")
_FEED_REF = ("feed.user_id", "feed.external_id")
_MESSAGE_FK = ("user_id", "external_id", "external_message_id")
_MESSAGE_REF = (
    "raw_message.user_id",
    "raw_message.external_id",
    "raw_message.external_message_id",
)
_FEED_STATUS = (
    "status IN ('new', 'backfilling', 'backfilled', 'verified', "
    "'analyzed', 'cancelled', 'failed')"
)
_FEED_HISTORY_DEPTH = "history_depth IN ('6m', '1y', 'all')"


class FeedRow(Base):
    """A stream a user follows (old user_channel + telegram_channel, merged).

    `metadata` holds provider-specific stream attributes (Telegram: handle,
    is_private, subscriber_count). `captured_through_external_message_id` is the
    top (highest/newest) captured id — REFRESH pulls messages above it; a
    newest->oldest capture fills older history in behind it (the oldest frontier
    is derived from the stored messages). It lives here so deleting the feed drops
    it.
    """

    __tablename__ = "feed"
    __table_args__ = (
        CheckConstraint(_FEED_STATUS, name="ck_feed_status"),
        CheckConstraint(_FEED_HISTORY_DEPTH, name="ck_feed_history_depth"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id", ondelete="CASCADE"), primary_key=True
    )
    external_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("source.id", ondelete="CASCADE", name="fk_feed_source"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="new")
    history_depth: Mapped[str] = mapped_column(
        String, nullable=False, server_default="1y"
    )
    captured_through_external_message_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    meta: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RawMessageRow(Base):
    __tablename__ = "raw_message"
    __table_args__ = (
        ForeignKeyConstraint(
            _FEED_FK, _FEED_REF, name="fk_raw_message_feed", ondelete="CASCADE"
        ),
    )

    user_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    external_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    external_message_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sender_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reply_to_external_message_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    edit_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    has_media: Mapped[bool] = mapped_column(Boolean, nullable=False)
    views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    forwards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


# --- Candidate events + extraction outputs ------------------------------------
# JSONB holds list/map fields; enums stored as their value.


class RawSignalEventRow(Base):
    __tablename__ = "raw_signal_event"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "external_id",
            "external_message_id",
            name="uq_raw_signal_event_msg",
        ),
        ForeignKeyConstraint(
            _MESSAGE_FK,
            _MESSAGE_REF,
            name="fk_raw_signal_event_message",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            _FEED_FK, _FEED_REF, name="fk_raw_signal_event_feed", ondelete="CASCADE"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    external_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    external_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    candidate_text: Mapped[str] = mapped_column(Text, nullable=False)
    materialized_by: Mapped[str] = mapped_column(String, nullable=False)
    matched_reasons: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ExtractedSignalRow(Base):
    __tablename__ = "extracted_signal"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "event_id",
            name="uq_extracted_signal_user_event",
        ),
        CheckConstraint("side IN ('LONG', 'SHORT')", name="ck_extracted_signal_side"),
        CheckConstraint(
            "event_type IN ('NEW_ENTRY', 'MODIFY', 'CLOSE', 'UNRECOGNIZED')",
            name="ck_extracted_signal_event_type",
        ),
        CheckConstraint(
            "extraction_method IN ('DETERMINISTIC', 'LLM_FALLBACK')",
            name="ck_extracted_signal_extraction_method",
        ),
        Index("ix_extracted_signal_user_channel", "user_id", "external_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False
    )
    event_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("raw_signal_event.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    references_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    entry_type: Mapped[str | None] = mapped_column(String, nullable=True)
    entry_low: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    entry_high: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    take_profits: Mapped[list] = mapped_column(JSONB, nullable=False)
    leverage: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    extraction_method: Mapped[str] = mapped_column(String, nullable=False)
    rule_id: Mapped[str | None] = mapped_column(String, nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class UnrecognizedSignalRow(Base):
    __tablename__ = "unrecognized_signal"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "event_id",
            name="uq_unrecognized_signal_user_event",
        ),
        Index("ix_unrecognized_signal_user_event", "user_id", "event_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False
    )
    event_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("raw_signal_event.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String, nullable=False)
    attempted_methods: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


# --- Durable, NON-recomputable deletion evidence (ADR 0008) -------------------
# Now user-owned: UNIQUE(user_id, external_id, external_message_id) makes rescans
# idempotent per user; deleting the feed purges its evidence (ADR-0008 durability
# is scoped to the feed's lifetime).


class DeletedSignalEvidenceRow(Base):
    __tablename__ = "deleted_signal_evidence"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "external_id",
            "external_message_id",
            name="uq_deleted_evidence_msg",
        ),
        CheckConstraint(
            "confidence IN ('CONFIRMED', 'SUSPECTED')",
            name="ck_deleted_signal_evidence_confidence",
        ),
        CheckConstraint(
            "method IN ('SNAPSHOT_DIFF', 'ID_GAP', 'LIVE_EVENT')",
            name="ck_deleted_signal_evidence_method",
        ),
        ForeignKeyConstraint(
            _FEED_FK,
            _FEED_REF,
            name="fk_deleted_signal_evidence_feed",
            ondelete="CASCADE",
        ),
        Index("ix_deleted_signal_evidence_channel", "user_id", "external_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    external_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    external_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    confidence: Mapped[str] = mapped_column(String, nullable=False)
    method: Mapped[str] = mapped_column(String, nullable=False)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    was_signal_candidate: Mapped[bool] = mapped_column(Boolean, nullable=False)


class UserAccountRow(Base):
    __tablename__ = "user_account"
    __table_args__ = (
        CheckConstraint(
            "plan IN ('observer', 'operator', 'desk')",
            name="ck_user_account_plan",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    plan: Mapped[str] = mapped_column(String, nullable=False, default="observer")
    pending_email: Mapped[str | None] = mapped_column(String, nullable=True)
    cancel_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class SourceRow(Base):
    """A user's connection to a provider (Telegram today).

    Generic + provider-agnostic: the only Telegram-specific surface is `name`
    (`CHECK IN ('Telegram')`) and the shape of `config_encrypted` — a JSON object
    holding the connection secrets, where the sensitive fields are AES-GCM
    envelopes (the codec lives in the Telegram adapter). A feed's `source_id`
    cascades from here, so disconnecting a source purges its feeds + capture.
    """

    __tablename__ = "source"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_source_user_name"),
        CheckConstraint("name IN ('Telegram')", name="ck_source_name"),
        CheckConstraint("status IN ('pending', 'connected')", name="ck_source_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    config_encrypted: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class BackfillJobRunRow(Base):
    __tablename__ = "backfill_job_run"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'cancelled')",
            name="ck_backfill_job_run_status",
        ),
        ForeignKeyConstraint(
            _FEED_FK, _FEED_REF, name="fk_backfill_job_run_feed", ondelete="CASCADE"
        ),
        Index(
            "ix_backfill_job_run_user_channel_started",
            "user_id",
            "external_id",
            "started_at",
        ),
        Index("ix_backfill_job_run_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fetched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    oldest_posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cursor_external_message_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Feed status captured when the run started, so a run interrupted by a
    # service restart can restore the reviewed status instead of falling to
    # "failed" (the in-memory map does not survive the restart).
    previous_feed_status: Mapped[str | None] = mapped_column(String, nullable=True)


class UserExchangeConnectionRow(Base):
    __tablename__ = "user_exchange_connection"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("user_account.id", ondelete="CASCADE"),
        primary_key=True,
    )
    exchange_id: Mapped[str] = mapped_column(String, primary_key=True)
    api_key_masked: Mapped[str] = mapped_column(String, nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    api_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    connected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class FeedRiskConfigRow(Base):
    __tablename__ = "feed_risk_config"
    __table_args__ = (
        CheckConstraint(
            "entry_mode IN ('first', 'mid', 'ladder')",
            name="ck_feed_risk_config_entry_mode",
        ),
        CheckConstraint(
            "weighting IN ('equal', 'martingale')",
            name="ck_feed_risk_config_weighting",
        ),
        CheckConstraint(
            "exit_source IN ('signal', 'custom')",
            name="ck_feed_risk_config_exit_source",
        ),
        ForeignKeyConstraint(
            _FEED_FK, _FEED_REF, name="fk_feed_risk_config_feed", ondelete="CASCADE"
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id", ondelete="CASCADE"), primary_key=True
    )
    external_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    entry_mode: Mapped[str] = mapped_column(String, nullable=False)
    levels: Mapped[int] = mapped_column(Integer, nullable=False)
    weighting: Mapped[str] = mapped_column(String, nullable=False)
    exit_source: Mapped[str] = mapped_column(String, nullable=False)
    stop_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    tp_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    risk_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    leverage: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class BacktestResultRow(Base):
    __tablename__ = "backtest_result"
    __table_args__ = (
        ForeignKeyConstraint(
            _FEED_FK, _FEED_REF, name="fk_backtest_result_feed", ondelete="CASCADE"
        ),
        Index(
            "ix_backtest_result_user_channel_completed",
            "user_id",
            "external_id",
            "completed_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    win_rate: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    pnl: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    outcomes: Mapped[list] = mapped_column(JSONB, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class LifecycleLinkRow(Base):
    __tablename__ = "lifecycle_link"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "external_id",
            "external_message_id",
            name="uq_lifecycle_link_msg",
        ),
        ForeignKeyConstraint(
            ["root_signal_id"],
            ["extracted_signal.id"],
            name="fk_lifecycle_link_root_signal",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            _FEED_FK, _FEED_REF, name="fk_lifecycle_link_feed", ondelete="CASCADE"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    external_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    root_signal_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ParserOverlayRow(Base):
    __tablename__ = "parser_overlay"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id", ondelete="CASCADE"), primary_key=True
    )
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class MineResultRow(Base):
    """The last template-mining result for a feed — the mined families plus the
    raw messages they were mined from ({groups, messages}, camelCase wire shape).

    One row per feed: a fresh mine upserts it, deleting the feed cascades it away.
    Reopening a verified feed hydrates the Verify audit from this snapshot instead
    of re-running the (CPU-bound) scan over the whole history."""

    __tablename__ = "mine_result"
    __table_args__ = (
        ForeignKeyConstraint(
            _FEED_FK, _FEED_REF, name="fk_mine_result_feed", ondelete="CASCADE"
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id", ondelete="CASCADE"), primary_key=True
    )
    external_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
