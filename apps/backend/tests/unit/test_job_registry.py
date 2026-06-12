import asyncio

import pytest

from verasig.services.jobs.registry import JobAlreadyRunningError, JobRegistry


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
async def test_late_subscriber_receives_latest_progress_and_terminal_event():
    registry = JobRegistry()

    async def run(publisher):
        publisher.progress({"step": 1})
        publisher.progress({"step": 2})
        return {"ok": True}

    registry.start("job", run)
    await asyncio.sleep(0)

    assert await _collect(registry, "job") == [
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

    registry.start("job", run)

    assert await _collect(registry, "job") == [("error", {"message": "boom"})]


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
