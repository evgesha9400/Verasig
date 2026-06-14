import json

from sse_starlette.sse import EventSourceResponse

from verasig.foundation.jobs.registry import JobRegistry


def sse_stream(registry: JobRegistry, key: str) -> EventSourceResponse:
    if not registry.has_job(key):
        raise KeyError(key)

    async def events():
        async for event, data in registry.stream(key):
            yield {"event": event, "data": json.dumps(data)}

    return EventSourceResponse(events())


def sse_single_event(event: str, data: dict) -> EventSourceResponse:
    async def events():
        yield {"event": event, "data": json.dumps(data)}

    return EventSourceResponse(events())
