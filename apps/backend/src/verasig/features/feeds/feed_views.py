import hashlib
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from verasig.shared.time import format_long
from verasig.storage.models import (
    BacktestResultRow,
    DeletedSignalEvidenceRow,
    FeedRow,
    RawMessageRow,
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
    session: Session, user_id: UUID, external_ids: list[int]
) -> dict[int, tuple[int, object]]:
    rows = session.execute(
        select(
            RawMessageRow.external_id,
            func.count(RawMessageRow.external_message_id),
            func.min(RawMessageRow.posted_at),
        )
        .where(
            RawMessageRow.user_id == user_id,
            RawMessageRow.external_id.in_(external_ids),
        )
        .group_by(RawMessageRow.external_id)
    ).all()
    return {external_id: (count, oldest) for external_id, count, oldest in rows}


def _deletion_flags(
    session: Session, user_id: UUID, external_ids: list[int]
) -> dict[int, tuple[bool, bool]]:
    rows = session.scalars(
        select(DeletedSignalEvidenceRow).where(
            DeletedSignalEvidenceRow.user_id == user_id,
            DeletedSignalEvidenceRow.external_id.in_(external_ids),
        )
    ).all()
    flags = {external_id: (False, False) for external_id in external_ids}
    for row in rows:
        history_gaps, signal_deletion = flags[row.external_id]
        history_gaps = history_gaps or row.confidence == "SUSPECTED"
        signal_deletion = signal_deletion or (
            row.confidence == "CONFIRMED" and row.was_signal_candidate
        )
        flags[row.external_id] = (history_gaps, signal_deletion)
    return flags


def _latest_results(session: Session, user_id: UUID) -> dict[int, BacktestResultRow]:
    rows = session.scalars(
        select(BacktestResultRow)
        .where(BacktestResultRow.user_id == user_id)
        .order_by(BacktestResultRow.external_id, BacktestResultRow.completed_at.desc())
    ).all()
    latest: dict[int, BacktestResultRow] = {}
    for row in rows:
        latest.setdefault(row.external_id, row)
    return latest


def present_feeds(session: Session, user_id: UUID) -> list[dict]:
    feeds = list(
        session.scalars(
            select(FeedRow).where(FeedRow.user_id == user_id).order_by(FeedRow.added_at)
        )
    )
    external_ids = [feed.external_id for feed in feeds]
    if not external_ids:
        return []
    message_stats = _message_stats(session, user_id, external_ids)
    deletion_flags = _deletion_flags(session, user_id, external_ids)
    latest_results = _latest_results(session, user_id)
    return [
        _present_feed(feed, message_stats, deletion_flags, latest_results)
        for feed in feeds
    ]


def _present_feed(
    feed: FeedRow,
    message_stats: dict[int, tuple[int, object]],
    deletion_flags: dict[int, tuple[bool, bool]],
    latest_results: dict[int, BacktestResultRow],
) -> dict:
    fetched, oldest = message_stats.get(feed.external_id, (0, None))
    history_gaps, signal_deletion = deletion_flags.get(feed.external_id, (False, False))
    result = latest_results.get(feed.external_id)
    score = result.score if result else None
    handle = feed.meta.get("handle")
    return {
        "id": str(feed.external_id),
        "name": feed.title,
        "tag": f"@{handle}" if handle else None,
        "subscribers": feed.meta.get("subscriber_count"),
        "initials": _initials(feed.title),
        "tint": _tint(feed.title),
        "status": feed.status,
        "fetched": fetched,
        "lastDate": format_long(oldest) if oldest else None,
        "score": 0 if signal_deletion else score,
        "winRate": float(result.win_rate) if result else None,
        "pnl": float(result.pnl) if result else None,
        "hasRisk": feed.status in {"verified", "analyzed"},
        "historyGaps": history_gaps,
        "signalDeletion": signal_deletion,
    }
