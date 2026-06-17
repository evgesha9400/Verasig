from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from verasig.shared.time import format_long


class BackfillJobStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BackfillMode(StrEnum):
    RESUME = "resume"
    REFRESH = "refresh"
    FULL = "full"


@dataclass(frozen=True)
class BackfillJobRun:
    id: UUID
    user_id: UUID
    channel_id: int
    status: str
    started_at: datetime
    finished_at: datetime | None
    fetched_count: int
    oldest_posted_at: datetime | None
    cursor_message_id: int | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class BackfillProgress:
    job_id: UUID
    status: str
    phase: str
    fetched: int
    oldest_posted_at: datetime | None
    cursor_message_id: int | None
    message: str | None = None


def backfill_job_key(user_id: UUID, channel_id: int) -> str:
    return f"{user_id}:{channel_id}:backfill"


def present_progress(progress: BackfillProgress) -> dict:
    payload = {
        "jobId": str(progress.job_id),
        "status": progress.status,
        "phase": progress.phase,
        "fetched": progress.fetched,
        "lastDate": (
            format_long(progress.oldest_posted_at)
            if progress.oldest_posted_at
            else None
        ),
        "cursorExternalMessageId": progress.cursor_message_id,
    }
    if progress.message:
        payload["message"] = progress.message
    return payload


def progress_event_name(progress: BackfillProgress) -> str:
    if progress.status == BackfillJobStatus.SUCCEEDED:
        return "done"
    if progress.status in {BackfillJobStatus.FAILED, BackfillJobStatus.CANCELLED}:
        return "error"
    return "progress"
