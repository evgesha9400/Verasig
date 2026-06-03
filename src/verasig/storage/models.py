"""Append-only ORM rows mirroring the §2 contracts 1:1.

`raw_telegram_message` is insert-only (composite PK gives idempotent dedup);
`telegram_channel` carries mutable metadata + the backfill cursor.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
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
