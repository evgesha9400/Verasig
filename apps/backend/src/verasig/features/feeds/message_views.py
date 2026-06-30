from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from verasig.features.feeds import feed_repository
from verasig.shared.time import format_short, format_time
from verasig.storage.models import FeedRow, RawMessageRow


def project_message(
    row: RawMessageRow, channel: FeedRow, reply: RawMessageRow | None
) -> dict:
    return {
        "id": str(row.external_message_id),
        "time": format_time(row.posted_at),
        "date": format_short(row.posted_at),
        "author": channel.title,
        "text": row.text,
        "media": _media(row.raw_payload),
        "replyTo": (
            {"author": channel.title, "text": _truncate(reply.text)} if reply else None
        ),
    }


def read_replies_by_message_id(
    session: Session, user_id: UUID, channel_id: int, rows: list[RawMessageRow]
) -> dict[int, RawMessageRow]:
    reply_ids = {
        row.reply_to_external_message_id
        for row in rows
        if row.reply_to_external_message_id
    }
    if not reply_ids:
        return {}
    replies = session.scalars(
        select(RawMessageRow).where(
            RawMessageRow.user_id == user_id,
            RawMessageRow.external_id == channel_id,
            RawMessageRow.external_message_id.in_(reply_ids),
        )
    ).all()
    return {reply.external_message_id: reply for reply in replies}


def read_history(session: Session, user_id: UUID, channel_id: int) -> list[dict]:
    """Every stored message for a feed, oldest first — the full backfilled
    history, unfiltered by label or candidacy. The parser-first miner runs its
    own candidate detection, so it needs the raw history, not the labeling deck."""
    channel = feed_repository.read_feed(session, user_id, channel_id)
    rows = session.scalars(
        select(RawMessageRow)
        .where(
            RawMessageRow.user_id == user_id,
            RawMessageRow.external_id == channel_id,
        )
        .order_by(RawMessageRow.posted_at, RawMessageRow.external_message_id)
    ).all()
    replies = read_replies_by_message_id(session, user_id, channel_id, rows)
    return [
        project_message(row, channel, replies.get(row.reply_to_external_message_id))
        for row in rows
    ]


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
