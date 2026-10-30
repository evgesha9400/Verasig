import asyncio
import logging
from contextlib import contextmanager

import pytest

from verasig.foundation.jobs.registry import JobAlreadyRunningError, JobRegistry


class _RecordLogHandler(logging.Handler):
    def __init__(self, level: int = logging.ERROR) -> None:
        super().__init__(level)
        self.records: list[logging.LogRecord] = []

    @property
    def text(self) -> str:
        return "\n".join(record.getMessage() for record in self.records)

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@contextmanager
def _capture_logger(name: str, level: int = logging.ERROR):
    handler = _RecordLogHandler(level)
    logger = logging.getLogger(name)
    previous_level = logger.level
    previous_disabled = logger.disabled
    logger.setLevel(level)
    logger.disabled = False
    logger.addHandler(handler)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.disabled = previous_disabled


async def _collect(registry: JobRegistry, key: str) -> list[tuple[str, dict]]:
    events = []
    async for event in registry.stream(key):
        events.append(event)
    return events


@pytest.mark.asyncio
async def test_start_runs_coroutine_and_streams_progress_then_done():
    registry = JobRegistry()

    async def run(publisher):
        publisher.progress({"step": 1})
        return {"ok": True}

    registry.start("job", run)

    assert await _collect(registry, "job") == [
        ("progress", {"step": 1}),
        ("done", {"ok": True}),
    ]


@pytest.mark.asyncio
async def test_two_concurrent_subscribers_each_receive_every_event():
    registry = JobRegistry()
    ready = asyncio.Event()
    release = asyncio.Event()

    async def run(publisher):
        ready.set()
        await release.wait()
        publisher.progress({"step": 1})
        publisher.progress({"step": 2})
        return {"ok": True}

    registry.start("job", run)
    await ready.wait()
    first = asyncio.create_task(_collect(registry, "job"))
    second = asyncio.create_task(_collect(registry, "job"))
    await asyncio.sleep(0)
    release.set()

    assert await first == [
        ("progress", {"step": 1}),
        ("progress", {"step": 2}),
        ("done", {"ok": True}),
    ]
    assert await second == await first


@pytest.mark.asyncio
async def test_late_subscriber_receives_progress_replay_and_terminal_event():
    registry = JobRegistry()

    async def run(publisher):
        publisher.progress({"step": 1})
        publisher.progress({"step": 2})
        return {"ok": True}

    registry.start("job", run)
    await asyncio.sleep(0)

    assert await _collect(registry, "job") == [
        ("progress", {"step": 1}),
        ("progress", {"step": 2}),
        ("done", {"ok": True}),
    ]


@pytest.mark.asyncio
async def test_duplicate_start_while_running_raises_and_finished_job_restarts():
    registry = JobRegistry()
    release = asyncio.Event()

    async def run(_publisher):
        await release.wait()
        return {"ok": True}

    registry.start("job", run)
    with pytest.raises(JobAlreadyRunningError):
        registry.start("job", run)
    release.set()
    await _collect(registry, "job")

    registry.start("job", run)
    assert await _collect(registry, "job") == [("done", {"ok": True})]


@pytest.mark.asyncio
async def test_failing_coroutine_yields_error_event():
    registry = JobRegistry()

    async def run(_publisher):
        raise RuntimeError("boom")

    with _capture_logger("verasig.foundation.jobs.registry") as logs:
        registry.start("job", run)
        events = await _collect(registry, "job")

    assert events == [("error", {"message": "boom"})]
    assert "job.unexpected_failure" in logs.text
    assert any(record.exc_info for record in logs.records)


@pytest.mark.asyncio
async def test_cancel_yields_cancelled_error_event():
    registry = JobRegistry()
    started = asyncio.Event()

    async def run(_publisher):
        started.set()
        await asyncio.sleep(60)
        return {"ok": True}

    registry.start("job", run)
    await started.wait()
    registry.cancel("job")

    assert await _collect(registry, "job") == [("error", {"message": "cancelled"})]


@pytest.mark.asyncio
async def test_finished_job_is_evicted_after_last_subscriber_disconnects():
    registry = JobRegistry()

    async def run(publisher):
        publisher.progress({"step": 1})
        return {"ok": True}

    registry.start("job", run)
    await _collect(registry, "job")

    assert registry.has_job("job") is False


@pytest.mark.asyncio
async def test_has_job_tracks_active_job_keys():
    registry = JobRegistry()

    async def run(_publisher):
        return {"ok": True}

    assert registry.has_job("job") is False
    registry.start("job", run)
    assert registry.has_job("job") is True


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


async def _finish_unobserved(registry: JobRegistry, key: str) -> None:
    async def run(_publisher):
        return {"ok": True}

    registry.start(key, run)
    while registry.channel(key).terminal is None:
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_unsubscribed_finished_job_stays_replayable_within_ttl():
    clock = _Clock()
    registry = JobRegistry(clock=clock)
    await _finish_unobserved(registry, "first")

    clock.now += 299
    await _finish_unobserved(registry, "second")

    # POST-then-subscribe still replays the terminal of a just-finished job
    assert await _collect(registry, "first") == [("done", {"ok": True})]


@pytest.mark.asyncio
async def test_unsubscribed_finished_job_is_pruned_after_ttl_on_next_start():
    clock = _Clock()
    registry = JobRegistry(clock=clock)
    await _finish_unobserved(registry, "never-streamed")

    clock.now += 301
    await _finish_unobserved(registry, "next")

    assert registry.has_job("never-streamed") is False
    assert registry.has_job("next") is True


@pytest.mark.asyncio
async def test_running_job_is_never_pruned():
    clock = _Clock()
    registry = JobRegistry(clock=clock)
    release = asyncio.Event()

    async def run(_publisher):
        await release.wait()
        return {"ok": True}

    registry.start("running", run)
    clock.now += 10_000
    await _finish_unobserved(registry, "other")

    assert registry.has_job("running") is True
    release.set()
    assert await _collect(registry, "running") == [("done", {"ok": True})]
