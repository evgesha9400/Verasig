import hashlib
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from verasig.shared.time import format_long
from verasig.storage.models import (
    BacktestResultRow,
    ChannelRow,
    DeletedSignalEvidenceRow,
    RawMessageRow,
    UserChannelRow,
)


def _initials(title: str) -> str:
    words = [word for word in title.replace("-", " ").split() if word]
    if not words:
        return "?"
    return "".join(word[0].upper() for word in words[:2])


def _tint(title: str) -> str:
    digest = hashlib.sha1(title.encode()).hexdigest()
    return f"var(--viz-{int(digest[:2], 16) % 6 + 1})"


def _message_stats(
    session: Session, channel_ids: list[int]
) -> dict[int, tuple[int, object]]:
    rows = session.execute(
        select(
            RawMessageRow.channel_id,
            func.count(RawMessageRow.message_id),
            func.min(RawMessageRow.posted_at),
        )
        .where(RawMessageRow.channel_id.in_(channel_ids))
        .group_by(RawMessageRow.channel_id)
    ).all()
    return {channel_id: (count, oldest) for channel_id, count, oldest in rows}


def _deletion_flags(
    session: Session, channel_ids: list[int]
) -> dict[int, tuple[bool, bool]]:
    rows = session.scalars(
        select(DeletedSignalEvidenceRow).where(
            DeletedSignalEvidenceRow.channel_id.in_(channel_ids)
        )
    ).all()
    flags = {channel_id: (False, False) for channel_id in channel_ids}
    for row in rows:
        history_gaps, signal_deletion = flags[row.channel_id]
        history_gaps = history_gaps or row.confidence == "SUSPECTED"
        signal_deletion = signal_deletion or (
            row.confidence == "CONFIRMED" and row.was_signal_candidate
        )
        flags[row.channel_id] = (history_gaps, signal_deletion)
    return flags


def _latest_results(session: Session, user_id: UUID) -> dict[int, BacktestResultRow]:
    rows = session.scalars(
        select(BacktestResultRow)
        .where(BacktestResultRow.user_id == user_id)
        .order_by(BacktestResultRow.channel_id, BacktestResultRow.completed_at.desc())
    ).all()
    latest: dict[int, BacktestResultRow] = {}
    for row in rows:
        latest.setdefault(row.channel_id, row)
    return latest


def present_chats(session: Session, user_id: UUID) -> list[dict]:
    rows = session.execute(
        select(UserChannelRow, ChannelRow)
        .join(ChannelRow, ChannelRow.channel_id == UserChannelRow.channel_id)
        .where(UserChannelRow.user_id == user_id)
        .order_by(UserChannelRow.added_at)
    ).all()
    channel_ids = [channel.channel_id for _subscription, channel in rows]
    if not channel_ids:
        return []
    message_stats = _message_stats(session, channel_ids)
    deletion_flags = _deletion_flags(session, channel_ids)
    latest_results = _latest_results(session, user_id)
    return [
        _present_chat(
            subscription, channel, message_stats, deletion_flags, latest_results
        )
        for subscription, channel in rows
    ]


def _present_chat(
    subscription: UserChannelRow,
    channel: ChannelRow,
    message_stats: dict[int, tuple[int, object]],
    deletion_flags: dict[int, tuple[bool, bool]],
    latest_results: dict[int, BacktestResultRow],
) -> dict:
    fetched, oldest = message_stats.get(channel.channel_id, (0, None))
    history_gaps, signal_deletion = deletion_flags.get(
        channel.channel_id, (False, False)
    )
    result = latest_results.get(channel.channel_id)
    score = result.score if result else None
    return {
        "id": str(channel.channel_id),
        "name": channel.title,
        "tag": f"@{channel.handle}" if channel.handle else None,
        "subscribers": channel.subscriber_count,
        "initials": _initials(channel.title),
        "tint": _tint(channel.title),
        "status": subscription.status,
        "fetched": fetched,
        "lastDate": format_long(oldest) if oldest else None,
        "score": 0 if signal_deletion else score,
        "winRate": float(result.win_rate) if result else None,
        "pnl": float(result.pnl) if result else None,
        "hasRisk": subscription.status in {"verified", "analyzed"},
        "historyGaps": history_gaps,
        "signalDeletion": signal_deletion,
    }
