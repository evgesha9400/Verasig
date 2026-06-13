"""Append-only ORM rows mirroring the §2 contracts 1:1.

`raw_telegram_message` is insert-only (composite PK gives idempotent dedup);
`telegram_channel` carries mutable metadata + the backfill cursor.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
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


class ChannelRow(Base):
    __tablename__ = "telegram_channel"

    channel_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    handle: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False)
    subscriber_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    captured_through_message_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )


class RawMessageRow(Base):
    __tablename__ = "raw_telegram_message"

    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("telegram_channel.channel_id"), primary_key=True
    )
    message_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sender_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reply_to_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    edit_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    has_media: Mapped[bool] = mapped_column(Boolean, nullable=False)
    views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    forwards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


# --- Candidate events, extraction outputs, distilled rules, drift --------------
# JSONB holds list/map fields + GoldenLabel.expected; enums stored as their value.


class RawSignalEventRow(Base):
    __tablename__ = "raw_signal_event"
    __table_args__ = (
        UniqueConstraint("channel_id", "message_id", name="uq_raw_signal_event_msg"),
        ForeignKeyConstraint(
            ["channel_id", "message_id"],
            ["raw_telegram_message.channel_id", "raw_telegram_message.message_id"],
            name="fk_raw_signal_event_message",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("telegram_channel.channel_id"), nullable=False
    )
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    candidate_text: Mapped[str] = mapped_column(Text, nullable=False)
    materialized_by: Mapped[str] = mapped_column(String, nullable=False)
    matched_reasons: Mapped[list] = mapped_column(JSONB, nullable=False)
    filter_rule_id: Mapped[str | None] = mapped_column(String, nullable=True)
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
        Index("ix_extracted_signal_user_channel", "user_id", "channel_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id"), nullable=False
    )
    event_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("raw_signal_event.id"), nullable=False
    )
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
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
        Uuid, ForeignKey("user_account.id"), nullable=False
    )
    event_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("raw_signal_event.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String, nullable=False)
    attempted_methods: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class FilterRuleRow(Base):
    __tablename__ = "filter_rule"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "channel_id",
            "version",
            name="uq_filter_rule_user_channel_version",
        ),
        Index("ix_filter_rule_user_channel", "user_id", "channel_id"),
    )

    rule_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id"), nullable=False
    )
    channel_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("telegram_channel.channel_id"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    include_patterns: Mapped[list] = mapped_column(JSONB, nullable=False)
    exclude_patterns: Mapped[list] = mapped_column(JSONB, nullable=False)
    matched_reason_template: Mapped[str] = mapped_column(String, nullable=False)
    recall_target: Mapped[float] = mapped_column(Float, nullable=False)
    python_filter: Mapped[str | None] = mapped_column(String, nullable=True)
    display: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    distilled_from_label_ids: Mapped[list] = mapped_column(JSONB, nullable=False)


class ParserRuleRow(Base):
    __tablename__ = "parser_rule"
    __table_args__ = (Index("ix_parser_rule_user_channel", "user_id", "channel_id"),)

    rule_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id"), nullable=False
    )
    channel_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("telegram_channel.channel_id"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    patterns: Mapped[list] = mapped_column(JSONB, nullable=False)
    field_map: Mapped[dict] = mapped_column(JSONB, nullable=False)
    side_aliases: Mapped[dict] = mapped_column(JSONB, nullable=False)
    python_extractor: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    distilled_from_label_ids: Mapped[list] = mapped_column(JSONB, nullable=False)


class GoldenLabelRow(Base):
    __tablename__ = "golden_label"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "channel_id",
            "message_id",
            name="uq_golden_label_user_msg",
        ),
        CheckConstraint(
            "label IN ('signal', 'noise', 'modifier')",
            name="ck_golden_label_label",
        ),
        ForeignKeyConstraint(
            ["channel_id", "message_id"],
            ["raw_telegram_message.channel_id", "raw_telegram_message.message_id"],
            name="fk_golden_label_message",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id"), nullable=False
    )
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("telegram_channel.channel_id"), nullable=False
    )
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    expected: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    labeled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class FilterDriftWarningRow(Base):
    __tablename__ = "filter_drift_warning"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "channel_id",
            "message_id",
            name="uq_filter_drift_user_msg",
        ),
        ForeignKeyConstraint(
            ["channel_id", "message_id"],
            ["raw_telegram_message.channel_id", "raw_telegram_message.message_id"],
            name="fk_filter_drift_warning_message",
        ),
        Index("ix_filter_drift_warning_user_channel", "user_id", "channel_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id"), nullable=False
    )
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("telegram_channel.channel_id"), nullable=False
    )
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    filter_rule_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    miss_discovered_by: Mapped[str] = mapped_column(String, nullable=False)
    event_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("raw_signal_event.id"), nullable=True
    )
    source_label_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("golden_label.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ParserDriftWarningRow(Base):
    __tablename__ = "parser_drift_warning"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "event_id",
            name="uq_parser_drift_user_event",
        ),
        Index("ix_parser_drift_warning_user_channel", "user_id", "channel_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id"), nullable=False
    )
    event_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("raw_signal_event.id"), nullable=False
    )
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    deterministic_result: Mapped[str] = mapped_column(String, nullable=False)
    fallback_result: Mapped[str] = mapped_column(String, nullable=False)
    # plain Uuid, not a FK: re-extract churns the extracted PK; a FK would cascade
    fallback_signal_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


# --- Durable, NON-recomputable deletion evidence (ADR 0008) -------------------
# UNIQUE(channel_id, message_id) makes rescans idempotent; the upsert upgrades
# SUSPECTED→CONFIRMED only and preserves the first-noticed detected_at.


class DeletedSignalEvidenceRow(Base):
    __tablename__ = "deleted_signal_evidence"
    __table_args__ = (
        UniqueConstraint("channel_id", "message_id", name="uq_deleted_evidence_msg"),
        CheckConstraint(
            "confidence IN ('CONFIRMED', 'SUSPECTED')",
            name="ck_deleted_signal_evidence_confidence",
        ),
        CheckConstraint(
            "method IN ('SNAPSHOT_DIFF', 'ID_GAP', 'LIVE_EVENT')",
            name="ck_deleted_signal_evidence_method",
        ),
        Index("ix_deleted_signal_evidence_channel", "channel_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("telegram_channel.channel_id"), nullable=False
    )
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
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


class UserTelegramLinkRow(Base):
    __tablename__ = "user_telegram_link"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'connected')",
            name="ck_user_telegram_link_status",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id"), primary_key=True
    )
    api_id: Mapped[int] = mapped_column(Integer, nullable=False)
    api_hash_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    session_string_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone_code_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class UserChannelRow(Base):
    __tablename__ = "user_channel"
    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'backfilling', 'backfilled', 'verified', "
            "'analyzed', 'cancelled')",
            name="ck_user_channel_status",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id"), primary_key=True
    )
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("telegram_channel.channel_id"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="new")
    verify_attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserExchangeConnectionRow(Base):
    __tablename__ = "user_exchange_connection"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id"), primary_key=True
    )
    exchange_id: Mapped[str] = mapped_column(String, primary_key=True)
    api_key_masked: Mapped[str] = mapped_column(String, nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    api_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    connected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ChatRiskConfigRow(Base):
    __tablename__ = "chat_risk_config"
    __table_args__ = (
        CheckConstraint(
            "entry_mode IN ('first', 'mid', 'ladder')",
            name="ck_chat_risk_config_entry_mode",
        ),
        CheckConstraint(
            "weighting IN ('equal', 'martingale')",
            name="ck_chat_risk_config_weighting",
        ),
        CheckConstraint(
            "exit_source IN ('signal', 'custom')",
            name="ck_chat_risk_config_exit_source",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id"), primary_key=True
    )
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("telegram_channel.channel_id"), primary_key=True
    )
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
        Index(
            "ix_backtest_result_user_channel_completed",
            "user_id",
            "channel_id",
            "completed_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id"), nullable=False
    )
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("telegram_channel.channel_id"), nullable=False
    )
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
            "user_id", "channel_id", "message_id", name="uq_lifecycle_link_msg"
        ),
        ForeignKeyConstraint(
            ["root_signal_id"],
            ["extracted_signal.id"],
            name="fk_lifecycle_link_root_signal",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_account.id"), nullable=False
    )
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("telegram_channel.channel_id"), nullable=False
    )
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    root_signal_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
