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
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from verasig.foundation.db import Base


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


# --- Slice 3/4: candidate events, extraction outputs, distilled rules, drift ---
# JSONB holds list/map fields + GoldenLabel.expected; enums stored as their value.


class RawSignalEventRow(Base):
    __tablename__ = "raw_signal_event"
    __table_args__ = (
        UniqueConstraint("channel_id", "message_id", name="uq_raw_signal_event_msg"),
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

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
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

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
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

    rule_id: Mapped[str] = mapped_column(String, primary_key=True)
    channel_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("telegram_channel.channel_id"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    include_patterns: Mapped[list] = mapped_column(JSONB, nullable=False)
    exclude_patterns: Mapped[list] = mapped_column(JSONB, nullable=False)
    matched_reason_template: Mapped[str] = mapped_column(String, nullable=False)
    recall_target: Mapped[float] = mapped_column(Float, nullable=False)
    python_filter: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    distilled_from_label_ids: Mapped[list] = mapped_column(JSONB, nullable=False)


class ParserRuleRow(Base):
    __tablename__ = "parser_rule"

    rule_id: Mapped[str] = mapped_column(String, primary_key=True)
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
        UniqueConstraint("channel_id", "message_id", name="uq_golden_label_msg"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("telegram_channel.channel_id"), nullable=False
    )
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_signal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    expected: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    labeled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class FilterDriftWarningRow(Base):
    __tablename__ = "filter_drift_warning"
    __table_args__ = (
        UniqueConstraint("channel_id", "message_id", name="uq_filter_drift_msg"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
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
