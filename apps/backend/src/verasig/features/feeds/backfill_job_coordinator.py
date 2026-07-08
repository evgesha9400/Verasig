import asyncio
import itertools
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from verasig.domain.feed import FeedStatus
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
from verasig.features.feeds.feed_job_progress import publish_logged_progress
from verasig.features.feeds.history_depth import HistoryDepth, depth_cutoff
from verasig.features.feeds.recapture import guard_and_wipe
from verasig.foundation.jobs.registry import (
    JobAlreadyRunningError,
    JobPublisher,
    JobRegistry,
    JobTerminalError,
)
from verasig.storage.models import FeedRow

logger = logging.getLogger(__name__)

OPENING_PHASE = "Opening MTProto session..."
# Decorative capture-phase flavour cycled per batch so a long download is not
# silent. Every entry maps to the `capture` stage — the indexing phase is
# published explicitly by its own step and is never mixed into this cycle, so the
# stage strip never flickers to `index` mid-download.
CAPTURE_PHASES = (
    "Reading channel history...",
    "Decrypting message batch...",
    "Resolving media references...",
    "Backfilling older window...",
)
INDEXING_PHASE = "Indexing message bodies..."

SERVICE_INTERRUPTED = "SERVICE_INTERRUPTED"
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
        self._capture_generation_live: set[UUID] = set()

    def start(
        self,
        user_id: UUID,
        channel_id: int,
        make_source: Callable[[], TelegramSource],
        mode: BackfillMode = BackfillMode.RESUME,
        depth: HistoryDepth | None = None,
    ) -> BackfillJobRun:
        logger.info(
            "backfill.start requested: channel=%s mode=%s depth=%s",
            channel_id,
            mode,
            depth,
        )
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

        self._persist_depth(user_id, channel_id, depth)
        extend_newer = self._should_extend_newer(user_id, channel_id, mode)
        # FULL mutates nothing synchronously: the wipe happens inside the job,
        # after a reachability guard, and secures no evidence (that is Check gaps).
        source = make_source()
        run, previous_status = self._create_run(user_id, channel_id, mode)
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
                    extend_newer,
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
            feed_repository.set_status(
                session,
                user_id,
                channel_id,
                _feed_status_after_backfill(run.previous_status, "cancelled"),
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
                    _feed_status_after_backfill(run.previous_status, "failed"),
                )
                self._forget_run(run.id)
            session.commit()

    def mark_inactive_backfilling_failed(
        self, user_id: UUID | None = None, channel_id: int | None = None
    ) -> None:
        with self._session_factory() as session:
            statement = select(FeedRow).where(FeedRow.status == FeedStatus.BACKFILLING)
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
                previous_status = run.previous_status if run is not None else None
                row.status = _feed_status_after_backfill(previous_status, "failed")
                if run is not None:
                    self._forget_run(run.id)
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

    def _should_extend_newer(
        self, user_id: UUID, channel_id: int, mode: BackfillMode
    ) -> bool:
        """REFRESH ("fetch new messages") pulls only messages newer than the top
        cursor, independent of any prior run's status — a failed run must never flip
        a refresh into a backward re-capture of the whole depth window. Requires an
        existing cursor: without one there is nothing to be "newer" than and an
        unbounded min_id=0 fetch would ignore the depth window, so a cursorless feed
        falls back to a depth-bounded capture (extend_older).
        """
        if mode is not BackfillMode.REFRESH:
            return False
        with self._session_factory() as session:
            return feed_repository.read_cursor(session, user_id, channel_id) is not None

    def _persist_depth(
        self, user_id: UUID, channel_id: int, depth: HistoryDepth | None
    ) -> None:
        if depth is None:
            return
        with self._session_factory() as session:
            feed_repository.set_history_depth(session, user_id, channel_id, depth)
            session.commit()

    def _capture_cutoff(self, user_id: UUID, channel_id: int) -> datetime | None:
        """The oldest `posted_at` a fresh capture should reach, per the feed depth."""
        with self._session_factory() as session:
            depth = feed_repository.read_history_depth(session, user_id, channel_id)
        return depth_cutoff(depth, _now())

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
        self, user_id: UUID, channel_id: int, mode: BackfillMode
    ) -> tuple[BackfillJobRun, str | None]:
        with self._session_factory() as session:
            feed = feed_repository.read_feed(session, user_id, channel_id)
            previous_status = feed.status if feed is not None else None
            run = backfill_job_repository.create_run(
                session, user_id, channel_id, _now(), mode, previous_status
            )
            feed_repository.set_status(
                session, user_id, channel_id, FeedStatus.BACKFILLING
            )
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
        extend_newer: bool,
    ) -> dict:
        phases = itertools.cycle(CAPTURE_PHASES)
        self._publish_progress(publisher, run_id, channel_id, mode, OPENING_PHASE)

        def on_batch(_inserted: int, _oldest: datetime) -> None:
            self._publish_progress(publisher, run_id, channel_id, mode, next(phases))

        try:
            async with source:
                logger.info(
                    "backfill.run stream begin: run=%s channel=%s", run_id, channel_id
                )
                if mode is BackfillMode.FULL:
                    await self._guard_then_wipe(source, run_id, user_id, channel_id)
                result = await backfill(
                    source,
                    user_id,
                    channel_id,
                    self._session_factory,
                    self._batch_size,
                    on_batch=on_batch,
                    since=self._capture_cutoff(user_id, channel_id),
                    extend_newer=extend_newer,
                )
                logger.info(
                    "backfill.run stream done: run=%s channel=%s inserted=%s cursor=%s",
                    run_id,
                    channel_id,
                    result.inserted,
                    result.captured_through_external_message_id,
                )
                self._publish_progress(
                    publisher, run_id, channel_id, mode, INDEXING_PHASE
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
        sync = self._should_sync_from_capture(run_id, mode)
        progress = self._refresh_progress(run_id, phase, sync)
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

    async def _guard_then_wipe(
        self,
        source: TelegramSource,
        run_id: UUID,
        user_id: UUID,
        channel_id: int,
    ) -> None:
        """FULL only: verify reachability, then wipe the old capture generation.

        `guard_and_wipe` raises `ChannelUnreachableError` before any deletion if
        the channel does not resolve, so an inaccessible channel fails the run
        without destroying the existing capture. The wipe is a near-instant delete
        (no securing) so it needs no progress event of its own — the opening event
        already fired and the fetch's first batch follows. No deletion evidence is
        secured; that is the deliberate, template-gated `Check gaps` rescan.
        """
        await guard_and_wipe(source, user_id, channel_id, self._session_factory)
        # The old generation is gone: the live table now reflects only the fresh
        # capture, so progress may resume reading it (0, then growing up).
        self._capture_generation_live.add(run_id)

    def _should_sync_from_capture(self, run_id: UUID, mode: BackfillMode) -> bool:
        """Whether progress may reflect the live capture table yet.

        Progress reads the live table only once the run's capture generation is
        live: RESUME/REFRESH capture in place, so they are live from the start; a
        FULL re-fetch's generation only goes live after its pre-capture wipe, so
        until then progress stays at the seeded-empty baseline (0 / no date / no
        cursor) instead of the doomed pre-wipe total.
        """
        if mode is not BackfillMode.FULL:
            return True
        return run_id in self._capture_generation_live

    def _refresh_progress(
        self, run_id: UUID, phase: str, sync: bool = True
    ) -> BackfillProgress:
        with self._session_factory() as session:
            if sync:
                run = backfill_job_repository.refresh_run_progress(session, run_id)
                session.commit()
            else:
                run = backfill_job_repository.read_run(session, run_id)
        return self._progress_from_run(run, phase)

    def _forget_run(self, run_id: UUID) -> None:
        """Drop a finished run's per-run bookkeeping."""
        self._capture_generation_live.discard(run_id)

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
        self._forget_run(run_id)
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
        self._forget_run(run_id)
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
        self._forget_run(run_id)
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
