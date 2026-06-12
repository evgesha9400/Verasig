import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from functools import partial


class JobAlreadyRunningError(Exception):
    """Raised when a job key already has an active task."""


@dataclass
class JobChannel:
    subscribers: list[asyncio.Queue] = field(default_factory=list)
    progress_events: list[tuple[str, dict]] = field(default_factory=list)
    terminal: tuple[str, dict] | None = None
    task: asyncio.Task | None = None


class JobPublisher:
    def __init__(self, emit: Callable[[str, dict], None]) -> None:
        self._emit = emit

    def progress(self, data: dict) -> None:
        self._emit("progress", data)

    def done(self, data: dict) -> None:
        self._emit("done", data)

    def error(self, message: str) -> None:
        self._emit("error", {"message": message})


class JobRegistry:
    def __init__(self) -> None:
        self._channels: dict[str, JobChannel] = {}

    def start(self, key: str, run: Callable[[JobPublisher], Awaitable[dict]]) -> None:
        channel = self._channels.get(key)
        if channel and channel.task and not channel.task.done():
            raise JobAlreadyRunningError(key)
        channel = JobChannel()
        self._channels[key] = channel
        publisher = JobPublisher(partial(self._broadcast, key))
        channel.task = asyncio.create_task(self._guard(run, publisher))

    def cancel(self, key: str) -> None:
        channel = self._channels.get(key)
        if channel and channel.task and not channel.task.done():
            channel.task.cancel()

    def _broadcast(self, key: str, event: str, data: dict) -> None:
        channel = self._channels[key]
        if event == "progress":
            channel.progress_events.append((event, data))
            channel.progress_events = channel.progress_events[-20:]
        else:
            channel.terminal = (event, data)
        for queue in channel.subscribers:
            queue.put_nowait((event, data))

    async def _guard(
        self,
        run: Callable[[JobPublisher], Awaitable[dict]],
        publisher: JobPublisher,
    ) -> None:
        try:
            publisher.done(await run(publisher))
        except asyncio.CancelledError:
            publisher.error("cancelled")
            raise
        except Exception as error:
            publisher.error(str(error))

    async def stream(self, key: str) -> AsyncIterator[tuple[str, dict]]:
        channel = self._channels[key]
        queue: asyncio.Queue = asyncio.Queue()
        for replay in (*channel.progress_events, channel.terminal):
            if replay:
                queue.put_nowait(replay)
        channel.subscribers.append(queue)
        try:
            while True:
                event, data = await queue.get()
                yield event, data
                if event in {"done", "error"}:
                    return
        finally:
            channel.subscribers.remove(queue)
