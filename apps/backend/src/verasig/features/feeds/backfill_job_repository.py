from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from verasig.features.feeds.backfill_job_run import (
    BackfillJobRun,
    BackfillJobStatus,
    BackfillMode,
)
from verasig.storage.models import BackfillJobRunRow, FeedRow, RawMessageRow


def _row_to_run(row: BackfillJobRunRow) -> BackfillJobRun:
    return BackfillJobRun(
        id=row.id,
        user_id=row.user_id,
        channel_id=row.external_id,
        status=row.status,
        started_at=row.started_at,
        finished_at=row.finished_at,
        fetched_count=row.fetched_count,
        oldest_posted_at=row.oldest_posted_at,
        cursor_message_id=row.cursor_external_message_id,
        error_code=row.error_code,
        error_message=row.error_message,
        previous_status=row.previous_feed_status,
    )


def _read_stored_progress(
    session: Session, user_id: UUID, external_id: int
) -> tuple[int, datetime | None, int | None]:
    fetched, oldest = session.execute(
        select(
            func.count(RawMessageRow.external_message_id),
            func.min(RawMessageRow.posted_at),
        )
        .select_from(RawMessageRow)
        .where(
            RawMessageRow.user_id == user_id,
            RawMessageRow.external_id == external_id,
        )
    ).one()
    feed = session.get(FeedRow, (user_id, external_id))
    cursor = feed.captured_through_external_message_id if feed else None
    return int(fetched or 0), oldest, cursor


def _sync_progress(session: Session, row: BackfillJobRunRow) -> BackfillJobRunRow:
    fetched, oldest, cursor = _read_stored_progress(
        session, row.user_id, row.external_id
    )
    row.fetched_count = fetched
    row.oldest_posted_at = oldest
    row.cursor_external_message_id = cursor
    session.flush()
    return row


def _initial_progress(
    session: Session, user_id: UUID, external_id: int, mode: BackfillMode
) -> tuple[int, datetime | None, int | None]:
    """The progress a new run starts from.

    A FULL re-fetch opens a fresh capture generation (the old one is wiped later
    in the job), so its progress starts empty. RESUME/REFRESH continue the
    existing capture, so they resume from the stored progress.
    """
    if mode is BackfillMode.FULL:
        return 0, None, None
    return _read_stored_progress(session, user_id, external_id)


def create_run(
    session: Session,
    user_id: UUID,
    channel_id: int,
    started_at: datetime,
    mode: BackfillMode = BackfillMode.RESUME,
    previous_status: str | None = None,
) -> BackfillJobRun:
    fetched, oldest, cursor = _initial_progress(session, user_id, channel_id, mode)
    row = BackfillJobRunRow(
        id=uuid4(),
        user_id=user_id,
        external_id=channel_id,
        status=BackfillJobStatus.RUNNING,
        started_at=started_at,
        finished_at=None,
        fetched_count=fetched,
        oldest_posted_at=oldest,
        cursor_external_message_id=cursor,
        error_code=None,
        error_message=None,
        previous_feed_status=previous_status,
    )
    session.add(row)
    session.flush()
    return _row_to_run(row)


def read_run(session: Session, run_id: UUID) -> BackfillJobRun | None:
    row = session.get(BackfillJobRunRow, run_id)
    return _row_to_run(row) if row else None


def read_latest_run(
    session: Session, user_id: UUID, channel_id: int
) -> BackfillJobRun | None:
    row = session.scalar(
        select(BackfillJobRunRow)
        .where(
            BackfillJobRunRow.user_id == user_id,
            BackfillJobRunRow.external_id == channel_id,
        )
        .order_by(BackfillJobRunRow.started_at.desc())
        .limit(1)
    )
    return _row_to_run(row) if row else None


def read_running_run(
    session: Session, user_id: UUID, channel_id: int
) -> BackfillJobRun | None:
    row = session.scalar(
        select(BackfillJobRunRow).where(
            BackfillJobRunRow.user_id == user_id,
            BackfillJobRunRow.external_id == channel_id,
            BackfillJobRunRow.status == BackfillJobStatus.RUNNING,
        )
    )
    return _row_to_run(row) if row else None


def refresh_run_progress(session: Session, run_id: UUID) -> BackfillJobRun | None:
    row = session.get(BackfillJobRunRow, run_id)
    if row is None:
        return None
    return _row_to_run(_sync_progress(session, row))


def advance_run_progress(
    session: Session, run_id: UUID, inserted: int, oldest_posted_at: datetime
) -> BackfillJobRun | None:
    """Fold one committed batch into the run's progress in memory.

    Avoids re-aggregating the whole capture (`count`/`min` over `raw_message`)
    after every batch; the terminal transitions still re-sync from storage.
    """
    row = session.get(BackfillJobRunRow, run_id)
    if row is None:
        return None
    row.fetched_count += inserted
    if row.oldest_posted_at is None or oldest_posted_at < row.oldest_posted_at:
        row.oldest_posted_at = oldest_posted_at
    feed = session.get(FeedRow, (row.user_id, row.external_id))
    row.cursor_external_message_id = (
        feed.captured_through_external_message_id if feed else None
    )
    session.flush()
    return _row_to_run(row)


def mark_run_succeeded(
    session: Session, run_id: UUID, finished_at: datetime
) -> BackfillJobRun | None:
    row = session.get(BackfillJobRunRow, run_id)
    if row is None:
        return None
    _sync_progress(session, row)
    row.status = BackfillJobStatus.SUCCEEDED
    row.finished_at = finished_at
    row.error_code = None
    row.error_message = None
    session.flush()
    return _row_to_run(row)


def mark_run_cancelled(
    session: Session, run_id: UUID, finished_at: datetime
) -> BackfillJobRun | None:
    row = session.get(BackfillJobRunRow, run_id)
    if row is None:
        return None
    _sync_progress(session, row)
    row.status = BackfillJobStatus.CANCELLED
    row.finished_at = finished_at
    row.error_code = "USER_CANCELLED"
    row.error_message = "Backfill cancelled."
    session.flush()
    return _row_to_run(row)


def mark_run_failed(
    session: Session,
    run_id: UUID,
    finished_at: datetime,
    error_code: str,
    error_message: str,
) -> BackfillJobRun | None:
    row = session.get(BackfillJobRunRow, run_id)
    if row is None:
        return None
    _sync_progress(session, row)
    row.status = BackfillJobStatus.FAILED
    row.finished_at = finished_at
    row.error_code = error_code
    row.error_message = error_message
    session.flush()
    return _row_to_run(row)


def mark_running_runs_failed(
    session: Session,
    finished_at: datetime,
    error_code: str,
    error_message: str,
) -> list[BackfillJobRun]:
    rows = session.scalars(
        select(BackfillJobRunRow).where(
            BackfillJobRunRow.status == BackfillJobStatus.RUNNING
        )
    ).all()
    failed = []
    for row in rows:
        _sync_progress(session, row)
        row.status = BackfillJobStatus.FAILED
        row.finished_at = finished_at
        row.error_code = error_code
        row.error_message = error_message
        failed.append(_row_to_run(row))
    session.flush()
    return failed
