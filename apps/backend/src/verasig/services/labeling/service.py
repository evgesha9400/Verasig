from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from verasig.domain.label import GoldenLabel, LabelKind
from verasig.services.projection.dates import format_short, format_time
from verasig.storage.models import (
    ChannelRow,
    GoldenLabelRow,
    RawMessageRow,
    RawSignalEventRow,
)
from verasig.storage.rule_repository import upsert_labels


def _media(raw_payload: dict) -> str | None:
    if raw_payload.get("photo"):
        return "image"
    if raw_payload.get("document"):
        return "doc"
    media = raw_payload.get("media") or {}
    media_type = str(media.get("_", "")).lower()
    if "photo" in media_type:
        return "image"
    if "document" in media_type:
        return "doc"
    return None


def _truncate(text: str | None, limit: int = 80) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


def _message_dict(
    row: RawMessageRow, channel: ChannelRow, reply: RawMessageRow | None
) -> dict:
    return {
        "id": str(row.message_id),
        "time": format_time(row.posted_at),
        "date": format_short(row.posted_at),
        "author": channel.title,
        "text": row.text,
        "media": _media(row.raw_payload),
        "replyTo": (
            {"author": channel.title, "text": _truncate(reply.text)} if reply else None
        ),
    }


def labeling_sample(
    session: Session, user_id: UUID, channel_id: int, limit: int
) -> list[dict]:
    channel = session.get(ChannelRow, channel_id)
    labeled = (
        select(GoldenLabelRow.message_id)
        .where(
            GoldenLabelRow.user_id == user_id,
            GoldenLabelRow.channel_id == channel_id,
        )
        .subquery()
    )
    rows = session.scalars(
        select(RawMessageRow)
        .join(
            RawSignalEventRow,
            (RawSignalEventRow.channel_id == RawMessageRow.channel_id)
            & (RawSignalEventRow.message_id == RawMessageRow.message_id),
        )
        .where(
            RawMessageRow.channel_id == channel_id,
            RawMessageRow.message_id.not_in(select(labeled.c.message_id)),
        )
        .order_by(RawMessageRow.posted_at, RawMessageRow.message_id)
        .limit(limit)
    ).all()
    replies = _replies_by_message_id(session, channel_id, rows)
    return [
        _message_dict(row, channel, replies.get(row.reply_to_message_id))
        for row in rows
    ]


def _replies_by_message_id(
    session: Session, channel_id: int, rows: list[RawMessageRow]
) -> dict[int, RawMessageRow]:
    reply_ids = {row.reply_to_message_id for row in rows if row.reply_to_message_id}
    if not reply_ids:
        return {}
    replies = session.scalars(
        select(RawMessageRow).where(
            RawMessageRow.channel_id == channel_id,
            RawMessageRow.message_id.in_(reply_ids),
        )
    ).all()
    return {reply.message_id: reply for reply in replies}


def record_label(
    session: Session, user_id: UUID, channel_id: int, message_id: int, label: LabelKind
) -> None:
    upsert_labels(
        session,
        [
            GoldenLabel(
                user_id=user_id,
                channel_id=channel_id,
                message_id=message_id,
                label=label,
                labeled_at=datetime.now(tz=UTC),
            )
        ],
    )


def label_counts(session: Session, user_id: UUID, channel_id: int) -> dict:
    rows = session.execute(
        select(GoldenLabelRow.label, func.count())
        .where(
            GoldenLabelRow.user_id == user_id, GoldenLabelRow.channel_id == channel_id
        )
        .group_by(GoldenLabelRow.label)
    ).all()
    counts = {label: count for label, count in rows}
    signal = counts.get(LabelKind.SIGNAL.value, 0)
    noise = counts.get(LabelKind.NOISE.value, 0)
    modifier = counts.get(LabelKind.MODIFIER.value, 0)
    return {
        "signalCount": signal,
        "noiseCount": noise,
        "modifierCount": modifier,
        "total": signal + noise + modifier,
    }
