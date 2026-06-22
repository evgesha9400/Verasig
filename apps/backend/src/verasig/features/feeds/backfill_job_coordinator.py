import asyncio
import itertools
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from verasig.domain.telegram_ports import TelegramSource
from verasig.features.feeds import (
    backfill_job_repository,
    feed_repository,
)
from verasig.features.feeds.backfill import backfill
from verasig.features.feeds.backfill_job_run import (
    BackfillJobRun,
    BackfillJobStatus,
    BackfillMode,
    BackfillProgress,
    backfill_job_key,
    present_progress,
)
from verasig.features.feeds.candidate_derivation import derive_candidates
from verasig.features.feeds.deletion_rescan import rescan
from verasig.features.feeds.feed_job_progress import (
    publish_logged_progress,
    scan_phase,
    should_publish_count,
)
from verasig.foundation.jobs.registry import (
    JobAlreadyRunningError,
    JobPublisher,
    JobRegistry,
    JobTerminalError,
)
from verasig.foundation.market_data.static_exchange import StaticExchange
from verasig.storage.models import FeedRow

logger = logging.getLogger(__name__)

BACKFILL_PHASES = (
    "Opening MTProto session...",
    "Reading channel history...",
    "Decrypting message batch...",
    "Resolving media references...",
    "Backfilling older window...",
    "Indexing message bodies...",
)

SERVICE_INTERRUPTED = "SERVICE_INTERRUPTED"

# Publish one deletion-scan progress event every this many live messages, so a
# long re-fetch keeps the stream alive without flooding it with one event per id.
RESCAN_PROGRESS_INTERVAL = 200
REVIEWED_FEED_STATUSES = {"verified", "analyzed"}


class BackfillJobCoordinator:
    def __init__(
        self,
        session_factory: sessionmaker,
        jobs: JobRegistry,
        batch_size: int,
    ) -> None:
        self._session_factory = session_factory
        self._jobs = jobs
        self._batch_size = batch_size
        self._previous_status_by_run_id: dict[UUID, str | None] = {}

    def start(
        self,
        user_id: UUID,
        channel_id: int,
        make_source: Callable[[], TelegramSource],
        mode: BackfillMode = BackfillMode.RESUME,
    ) -> BackfillJobRun:
        logger.info("backfill.start requested: channel=%s mode=%s", channel_id, mode)
        idempotent = self._read_idempotent_run(user_id, channel_id, mode)
        if idempotent is not None:
            logger.info(
                "backfill.start short-circuit: channel=%s mode=%s reused run=%s "
                "status=%s (no new job started)",
                channel_id,
                mode,
                idempotent.id,
                idempotent.status,
            )
            return idempotent

        if mode is BackfillMode.FULL:
            self._reset_cursor(user_id, channel_id)

        source = make_source()
        run, previous_status = self._create_run(user_id, channel_id)
        self._previous_status_by_run_id[run.id] = previous_status
        key = backfill_job_key(user_id, channel_id)
        logger.info(
            "backfill.start new run: channel=%s mode=%s run=%s",
            channel_id,
            mode,
            run.id,
        )
        try:
            self._jobs.start(
                key,
                lambda publisher: self._run_backfill(
                    publisher,
                    source,
                    run.id,
                    user_id,
                    channel_id,
                    mode,
                    previous_status,
                ),
            )
        except JobAlreadyRunningError:
            attachable = self._read_attachable_run(user_id, channel_id)
            if attachable is not None:
                return attachable
            raise
        return run

    def cancel(self, user_id: UUID, channel_id: int) -> BackfillJobRun | None:
        key = backfill_job_key(user_id, channel_id)
        self._jobs.cancel(key)
        with self._session_factory() as session:
            run = backfill_job_repository.read_running_run(session, user_id, channel_id)
            if run is None:
                return backfill_job_repository.read_latest_run(
                    session, user_id, channel_id
                )
            cancelled = backfill_job_repository.mark_run_cancelled(
                session, run.id, _now()
            )
            previous_status = self._previous_status_by_run_id.get(run.id)
            feed_repository.set_status(
                session,
                user_id,
                channel_id,
                _feed_status_after_backfill(previous_status, "cancelled"),
            )
            session.commit()
            return cancelled

    def read_progress(self, user_id: UUID, channel_id: int) -> BackfillProgress | None:
        with self._session_factory() as session:
            run = backfill_job_repository.read_latest_run(session, user_id, channel_id)
            if run is None:
                return None
            refreshed = backfill_job_repository.refresh_run_progress(session, run.id)
            session.commit()
        return self._progress_from_run(refreshed, _phase_for_status(refreshed.status))

    def mark_interrupted_runs_failed(self) -> None:
        with self._session_factory() as session:
            failed_runs = backfill_job_repository.mark_running_runs_failed(
                session,
                _now(),
                SERVICE_INTERRUPTED,
                "Backfill was interrupted by a service restart.",
            )
            for run in failed_runs:
                feed_repository.set_status(
                    session,
                    run.user_id,
                    run.channel_id,
                    _feed_status_after_backfill(
                        self._previous_status_by_run_id.get(run.id), "failed"
                    ),
                )
                self._previous_status_by_run_id.pop(run.id, None)
            session.commit()

    def mark_inactive_backfilling_failed(
        self, user_id: UUID | None = None, channel_id: int | None = None
    ) -> None:
        with self._session_factory() as session:
            statement = select(FeedRow).where(FeedRow.status == "backfilling")
            if user_id is not None:
                statement = statement.where(FeedRow.user_id == user_id)
            if channel_id is not None:
                statement = statement.where(FeedRow.external_id == channel_id)
            rows = session.scalars(statement).all()
            for row in rows:
                key = backfill_job_key(row.user_id, row.external_id)
                if self._jobs.has_job(key):
                    continue
                run = backfill_job_repository.read_running_run(
                    session, row.user_id, row.external_id
                )
                if run is not None:
                    backfill_job_repository.mark_run_failed(
                        session,
                        run.id,
                        _now(),
                        SERVICE_INTERRUPTED,
                        "Backfill was interrupted by a service restart.",
                    )
                previous_status = (
                    self._previous_status_by_run_id.get(run.id)
                    if run is not None
                    else None
                )
                row.status = _feed_status_after_backfill(previous_status, "failed")
                if run is not None:
                    self._previous_status_by_run_id.pop(run.id, None)
            session.commit()

    def _read_idempotent_run(
        self, user_id: UUID, channel_id: int, mode: BackfillMode
    ) -> BackfillJobRun | None:
        """Run a duplicate POST should return instead of starting a new backfill.

        A live RUNNING job is always attached to, so a rebackfill never spawns a
        second job or resets the cursor mid-run. A RESUME after success replays the
        terminal; REFRESH/FULL fall through to start a fresh run. FAILED/CANCELLED
        runs fall through so a retry restarts from the persisted cursor.
        """
        with self._session_factory() as session:
            latest = backfill_job_repository.read_latest_run(
                session, user_id, channel_id
            )
        if latest is None:
            return None
        key = backfill_job_key(user_id, channel_id)
        if latest.status == BackfillJobStatus.RUNNING and self._jobs.has_job(key):
            return latest
        if latest.status == BackfillJobStatus.SUCCEEDED and mode is BackfillMode.RESUME:
            return latest
        return None

    def _reset_cursor(self, user_id: UUID, channel_id: int) -> None:
        with self._session_factory() as session:
            previous = feed_repository.read_cursor(session, user_id, channel_id)
            feed_repository.reset_cursor(session, user_id, channel_id)
            session.commit()
        logger.info(
            "backfill.full reset cursor: channel=%s previous_cursor=%s -> None "
            "(next stream refetches from the start; raw rows are upserted by PK, "
            "not deleted)",
            channel_id,
            previous,
        )

    def _read_attachable_run(
        self, user_id: UUID, channel_id: int
    ) -> BackfillJobRun | None:
        key = backfill_job_key(user_id, channel_id)
        if not self._jobs.has_job(key):
            return None
        with self._session_factory() as session:
            return backfill_job_repository.read_running_run(
                session, user_id, channel_id
            )

    def _create_run(
        self, user_id: UUID, channel_id: int
    ) -> tuple[BackfillJobRun, str | None]:
        with self._session_factory() as session:
            feed = feed_repository.read_feed(session, user_id, channel_id)
            previous_status = feed.status if feed is not None else None
            run = backfill_job_repository.create_run(
                session, user_id, channel_id, _now()
            )
            feed_repository.set_status(session, user_id, channel_id, "backfilling")
            session.commit()
            return run, previous_status

    async def _run_backfill(
        self,
        publisher: JobPublisher,
        source: TelegramSource,
        run_id: UUID,
        user_id: UUID,
        channel_id: int,
        mode: BackfillMode,
        previous_status: str | None,
    ) -> dict:
        phases = itertools.cycle(BACKFILL_PHASES[1:])
        self._publish_progress(publisher, run_id, channel_id, mode, BACKFILL_PHASES[0])

        def on_batch(_inserted: int, _oldest: datetime) -> None:
            self._publish_progress(publisher, run_id, channel_id, mode, next(phases))

        try:
            async with source:
                logger.info(
                    "backfill.run stream begin: run=%s channel=%s", run_id, channel_id
                )
                result = await backfill(
                    source,
                    user_id,
                    channel_id,
                    self._session_factory,
                    self._batch_size,
                    on_batch=on_batch,
                )
                logger.info(
                    "backfill.run stream done: run=%s channel=%s inserted=%s cursor=%s",
                    run_id,
                    channel_id,
                    result.inserted,
                    result.captured_through_external_message_id,
                )
                self._publish_progress(
                    publisher, run_id, channel_id, mode, "Indexing message bodies..."
                )
                logger.info(
                    "backfill.run derive_candidates begin: channel=%s", channel_id
                )
                derive_candidates(
                    self._session_factory, user_id, channel_id, StaticExchange()
                )
                logger.info(
                    "backfill.run derive_candidates done: channel=%s", channel_id
                )
                self._publish_progress(
                    publisher, run_id, channel_id, mode, "Checking deleted messages..."
                )
                logger.info(
                    "backfill.run rescan begin: channel=%s (fetches the FULL live "
                    "message-id set from Telegram regardless of how little was "
                    "backfilled — this is the slow step)",
                    channel_id,
                )
                rescan_result = await rescan(
                    source,
                    user_id,
                    channel_id,
                    self._session_factory,
                    on_progress=self._rescan_progress_reporter(
                        publisher, run_id, channel_id, mode
                    ),
                )
                logger.info(
                    "backfill.run rescan done: channel=%s confirmed=%s suspected=%s "
                    "written=%s",
                    channel_id,
                    rescan_result.confirmed,
                    rescan_result.suspected,
                    rescan_result.written,
                )
        except asyncio.CancelledError as error:
            progress = self._finish_cancelled(
                run_id, user_id, channel_id, previous_status
            )
            raise JobTerminalError("cancelled", present_progress(progress)) from error
        except Exception as error:
            progress = self._finish_failed(
                run_id, user_id, channel_id, previous_status, error
            )
            raise JobTerminalError(
                progress.message or "Backfill failed.", present_progress(progress)
            ) from error

        progress = self._finish_succeeded(run_id, user_id, channel_id, previous_status)
        return present_progress(progress)

    def _publish_progress(
        self,
        publisher: JobPublisher,
        run_id: UUID,
        channel_id: int,
        mode: BackfillMode,
        phase: str,
        **fields,
    ) -> None:
        progress = self._refresh_progress(run_id, phase)
        publish_logged_progress(
            publisher,
            present_progress(progress),
            logger=logger,
            operation=_operation_for_mode(mode),
            external_id=channel_id,
            phase=phase,
            run_id=run_id,
            mode=mode,
            status=progress.status,
            fetched=progress.fetched,
            cursor=progress.cursor_message_id,
            **fields,
        )

    def _rescan_progress_reporter(
        self,
        publisher: JobPublisher,
        run_id: UUID,
        channel_id: int,
        mode: BackfillMode,
    ) -> Callable[[int], None]:
        def report(scanned: int) -> None:
            if should_publish_count(scanned, RESCAN_PROGRESS_INTERVAL):
                self._publish_progress(
                    publisher,
                    run_id,
                    channel_id,
                    mode,
                    scan_phase(scanned),
                    scanned=scanned,
                )

        return report

    def _refresh_progress(self, run_id: UUID, phase: str) -> BackfillProgress:
        with self._session_factory() as session:
            run = backfill_job_repository.refresh_run_progress(session, run_id)
            session.commit()
        return self._progress_from_run(run, phase)

    def _finish_succeeded(
        self,
        run_id: UUID,
        user_id: UUID,
        channel_id: int,
        previous_status: str | None,
    ) -> BackfillProgress:
        with self._session_factory() as session:
            run = backfill_job_repository.mark_run_succeeded(session, run_id, _now())
            feed_repository.set_status(
                session,
                user_id,
                channel_id,
                _feed_status_after_backfill(previous_status, "backfilled"),
            )
            session.commit()
        self._previous_status_by_run_id.pop(run_id, None)
        return self._progress_from_run(run, "Backfill complete.")

    def _finish_cancelled(
        self,
        run_id: UUID,
        user_id: UUID,
        channel_id: int,
        previous_status: str | None,
    ) -> BackfillProgress:
        with self._session_factory() as session:
            run = backfill_job_repository.mark_run_cancelled(session, run_id, _now())
            feed_repository.set_status(
                session,
                user_id,
                channel_id,
                _feed_status_after_backfill(previous_status, "cancelled"),
            )
            session.commit()
        self._previous_status_by_run_id.pop(run_id, None)
        return self._progress_from_run(run, "Backfill cancelled.")

    def _finish_failed(
        self,
        run_id: UUID,
        user_id: UUID,
        channel_id: int,
        previous_status: str | None,
        error: Exception,
    ) -> BackfillProgress:
        message = str(error) or error.__class__.__name__
        with self._session_factory() as session:
            run = backfill_job_repository.mark_run_failed(
                session, run_id, _now(), error.__class__.__name__, message
            )
            feed_repository.set_status(
                session,
                user_id,
                channel_id,
                _feed_status_after_backfill(previous_status, "failed"),
            )
            session.commit()
        self._previous_status_by_run_id.pop(run_id, None)
        return self._progress_from_run(run, "Backfill failed.")

    @staticmethod
    def _progress_from_run(run: BackfillJobRun, phase: str) -> BackfillProgress:
        return BackfillProgress(
            job_id=run.id,
            status=run.status,
            phase=phase,
            fetched=run.fetched_count,
            oldest_posted_at=run.oldest_posted_at,
            cursor_message_id=run.cursor_message_id,
            message=run.error_message,
        )


def _phase_for_status(status: str) -> str:
    if status == BackfillJobStatus.SUCCEEDED:
        return "Backfill complete."
    if status == BackfillJobStatus.FAILED:
        return "Backfill failed."
    if status == BackfillJobStatus.CANCELLED:
        return "Backfill cancelled."
    return "Reading channel history..."


def _operation_for_mode(mode: BackfillMode) -> str:
    if mode is BackfillMode.REFRESH:
        return "fetch_latest_messages"
    if mode is BackfillMode.FULL:
        return "rebackfill"
    return "backfill"


def _feed_status_after_backfill(previous_status: str | None, fallback: str) -> str:
    if previous_status in REVIEWED_FEED_STATUSES:
        return previous_status
    return fallback


def _now() -> datetime:
    return datetime.now(tz=UTC)
