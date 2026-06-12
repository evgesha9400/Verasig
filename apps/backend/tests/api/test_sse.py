import asyncio

from fastapi import APIRouter

from verasig.api.sse import sse_stream


def test_sse_streams_job_events(client, app):
    router = APIRouter()

    @router.post("/dummy/start")
    async def start():
        async def run(publisher):
            publisher.progress({"step": 1})
            await asyncio.sleep(0)
            publisher.progress({"step": 2})
            return {"ok": True}

        app.state.jobs.start("dummy", run)
        return {"jobId": "dummy"}

    @router.get("/dummy/progress")
    def progress():
        return sse_stream(app.state.jobs, "dummy")

    app.include_router(router)
    assert client.post("/dummy/start").status_code == 200

    with client.stream("GET", "/dummy/progress") as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert "event: progress" in body
    assert 'data: {"step": 2}' in body
    assert "event: done" in body
    assert 'data: {"ok": true}' in body
