import json

from sse_starlette.sse import EventSourceResponse

from verasig.foundation.http.errors import ApiError
from verasig.foundation.jobs.registry import JobRegistry


def sse_stream(registry: JobRegistry, key: str) -> EventSourceResponse:
    if not registry.has_job(key):
        raise ApiError(404, "JOB_NOT_FOUND", "No running job for this feed")

    async def events():
        # the job may drain between the has-job check and the first stream read;
        # end the stream cleanly rather than 500 mid-response on the missing key.
        try:
            async for event, data in registry.stream(key):
                yield {"event": event, "data": json.dumps(data)}
        except KeyError:
            return

    return EventSourceResponse(events())


def sse_single_event(event: str, data: dict) -> EventSourceResponse:
    async def events():
        yield {"event": event, "data": json.dumps(data)}

    return EventSourceResponse(events())
