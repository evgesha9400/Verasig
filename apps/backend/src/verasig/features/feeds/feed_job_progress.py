import logging
from enum import StrEnum
from uuid import UUID


def publish_logged_progress(
    publisher,
    payload: dict,
    *,
    logger: logging.Logger,
    operation: str,
    external_id: int,
    phase: str,
    **fields,
) -> None:
    log_progress(
        logger,
        operation=operation,
        external_id=external_id,
        phase=phase,
        **fields,
    )
    publisher.progress(payload)


def log_progress(
    logger: logging.Logger,
    *,
    operation: str,
    external_id: int,
    phase: str,
    **fields,
) -> None:
    logger.info(
        "feed_job.progress: operation=%s external_id=%s phase=%s%s",
        operation,
        external_id,
        phase,
        _format_fields(fields),
    )


def should_publish_count(count: int, interval: int) -> bool:
    return count % interval == 0


def scan_phase(scanned: int) -> str:
    return f"Checking deleted messages... ({scanned:,} scanned)"


def _format_fields(fields: dict) -> str:
    pairs = [f"{key}={_format_value(value)}" for key, value in fields.items()]
    return "" if not pairs else " " + " ".join(pairs)


def _format_value(value) -> str:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    return str(value)
