import json

from sse_starlette.sse import EventSourceResponse

from verasig.services.jobs.registry import JobRegistry


def sse_stream(registry: JobRegistry, key: str) -> EventSourceResponse:
    async def events():
        async for event, data in registry.stream(key):
            yield {"event": event, "data": json.dumps(data)}

    return EventSourceResponse(events())
