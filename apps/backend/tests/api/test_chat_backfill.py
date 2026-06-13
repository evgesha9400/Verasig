import asyncio
from datetime import datetime, timezone

from fakes import FakeSource, FakeTelegramAuth

from verasig.domain.channel import TelegramChannel
from verasig.domain.message import RawTelegramMessage


def _register(client, email: str = "ada@example.com") -> str:
    response = client.post(
        "/auth/register",
        json={
            "firstName": "Ada",
            "lastName": "Lovelace",
            "email": email,
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201
    return response.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _channel() -> TelegramChannel:
    return TelegramChannel(
        channel_id=7,
        handle="pilot",
        title="Pilot Signals",
        is_private=False,
        subscriber_count=1234,
        first_seen_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )


def _messages() -> list[RawTelegramMessage]:
    return [
        RawTelegramMessage(
            channel_id=7,
            message_id=message_id,
            text=text,
            posted_at=datetime(2026, 6, message_id, tzinfo=timezone.utc),
            captured_at=datetime(2026, 6, message_id, tzinfo=timezone.utc),
            has_media=False,
            raw_payload={},
        )
        for message_id, text in {
            1: "hello",
            2: "BTC long entry 65000",
            3: "ETH short entry 3000",
        }.items()
    ]


class SlowSource(FakeSource):
    async def backfill_batches(self, channel_id, after_message_id, batch_size):
        await asyncio.sleep(0.2)
        async for batch in super().backfill_batches(
            channel_id, after_message_id, batch_size
        ):
            yield batch


def _connect_and_subscribe(client, app, token: str, source) -> None:
    app.state.telegram_auth = FakeTelegramAuth()
    assert (
        client.post(
            "/telegram/connect",
            headers=_auth(token),
            json={"apiId": 123, "apiHash": "api-secret", "phone": "+441234568821"},
        ).status_code
        == 202
    )
    assert (
        client.post(
            "/telegram/verify", headers=_auth(token), json={"code": "12345"}
        ).status_code
        == 200
    )
    app.state.telegram_source_factory = lambda _link: source
    assert (
        client.post("/chats", headers=_auth(token), json={"tag": "@pilot"}).status_code
        == 201
    )


def test_backfill_job_streams_progress_and_flags_deleted_signal(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 3})
    _connect_and_subscribe(client, app, token, source)

    started = client.post("/chats/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/chats/7/backfill/progress", headers=_auth(token)
    ) as response:
        body = "".join(response.iter_text())
    listed = client.get("/chats", headers=_auth(token))

    assert started.status_code == 202
    assert "event: progress" in body
    assert "event: done" in body
    assert listed.json()["chats"][0]["status"] == "backfilled"
    assert listed.json()["chats"][0]["signalDeletion"] is True


def test_backfill_duplicate_start_and_cancel(client, app):
    token = _register(client)
    source = SlowSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    first = client.post("/chats/7/backfill", headers=_auth(token))
    duplicate = client.post("/chats/7/backfill", headers=_auth(token))
    cancelled = client.post("/chats/7/backfill/cancel", headers=_auth(token))
    with client.stream(
        "GET", "/chats/7/backfill/progress", headers=_auth(token)
    ) as response:
        body = "".join(response.iter_text())
    listed = client.get("/chats", headers=_auth(token))

    assert first.status_code == 202
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "JOB_ALREADY_RUNNING"
    assert cancelled.status_code == 204
    assert "event: error" in body
    assert "cancelled" in body
    assert listed.json()["chats"][0]["status"] == "cancelled"


def test_backfill_foreign_user_is_not_found(client, app):
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, owner, source)

    response = client.post("/chats/7/backfill", headers=_auth(other))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CHAT_NOT_FOUND"


def test_backfill_progress_reports_missing_job_as_404(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    response = client.get("/chats/7/backfill/progress", headers=_auth(token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"
