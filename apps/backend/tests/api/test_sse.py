import asyncio

from fastapi import APIRouter

from verasig.foundation.http.sse import sse_stream


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


def test_sse_stream_returns_typed_404_when_job_absent(client, app):
    router = APIRouter()

    @router.get("/missing/progress")
    def progress():
        return sse_stream(app.state.jobs, "missing")

    app.include_router(router)

    response = client.get("/missing/progress")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"
