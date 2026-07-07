import hashlib
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from verasig.domain.feed import REVIEWED_STATUSES
from verasig.features.feeds import deletion_repository
from verasig.shared.time import format_long
from verasig.storage.models import (
    BacktestResultRow,
    FeedRow,
    RawMessageRow,
)


def feed_initials(title: str) -> str:
    words = [word for word in title.replace("-", " ").split() if word]
    if not words:
        return "?"
    return "".join(word[0].upper() for word in words[:2])


def feed_tint(title: str) -> str:
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


def _latest_results(session: Session, user_id: UUID) -> dict[int, BacktestResultRow]:
    # DISTINCT ON keeps only the newest run per feed at the DB, instead of loading
    # every historical run and deduping in Python.
    rows = session.scalars(
        select(BacktestResultRow)
        .where(BacktestResultRow.user_id == user_id)
        .distinct(BacktestResultRow.external_id)
        .order_by(BacktestResultRow.external_id, BacktestResultRow.completed_at.desc())
    ).all()
    return {row.external_id: row for row in rows}


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
    deletion_summaries = deletion_repository.summarize_deletions(
        session, user_id, external_ids
    )
    latest_results = _latest_results(session, user_id)
    return [
        _present_feed(feed, message_stats, deletion_summaries, latest_results)
        for feed in feeds
    ]


def _present_feed(
    feed: FeedRow,
    message_stats: dict[int, tuple[int, object]],
    deletion_summaries: dict[int, deletion_repository.DeletionSummary],
    latest_results: dict[int, BacktestResultRow],
) -> dict:
    fetched, oldest = message_stats.get(feed.external_id, (0, None))
    deletion = deletion_summaries.get(
        feed.external_id, deletion_repository.DeletionSummary()
    )
    result = latest_results.get(feed.external_id)
    score = result.score if result else None
    handle = feed.meta.get("handle")
    return {
        "id": str(feed.external_id),
        "name": feed.title,
        "tag": f"@{handle}" if handle else None,
        "subscribers": feed.meta.get("subscriber_count"),
        "initials": feed_initials(feed.title),
        "tint": feed_tint(feed.title),
        "status": feed.status,
        "historyDepth": feed.history_depth,
        "fetched": fetched,
        "lastDate": format_long(oldest) if oldest else None,
        "score": 0 if deletion.signal_deletion else score,
        "winRate": float(result.win_rate) if result else None,
        "pnl": float(result.pnl) if result else None,
        "hasRisk": feed.status in REVIEWED_STATUSES,
        "signalDeletion": deletion.signal_deletion,
        "deletedCount": deletion.deleted_count,
        "deletedSignalCount": deletion.deleted_signal_count,
    }
