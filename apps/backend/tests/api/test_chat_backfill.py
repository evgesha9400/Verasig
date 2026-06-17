import asyncio
from datetime import datetime, timedelta, timezone

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


def _many_messages(count: int) -> list[RawTelegramMessage]:
    first_posted_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
    return [
        RawTelegramMessage(
            channel_id=7,
            message_id=message_id,
            text=f"message {message_id}",
            posted_at=first_posted_at + timedelta(days=message_id - 1),
            captured_at=first_posted_at + timedelta(days=message_id - 1),
            has_media=False,
            raw_payload={},
        )
        for message_id in range(1, count + 1)
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
    assert duplicate.status_code == 202
    assert duplicate.json()["jobId"] == first.json()["jobId"]
    assert cancelled.status_code == 204
    assert "event: error" in body
    assert "cancelled" in body
    assert listed.json()["chats"][0]["status"] == "cancelled"


def test_failed_backfill_can_retry_from_persisted_cursor(client, app):
    token = _register(client)
    failed_source = FakeSource(
        _channel(), _many_messages(205), live_ids={1, 2}, fail_after_batch=1
    )
    _connect_and_subscribe(client, app, token, failed_source)

    started = client.post("/chats/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/chats/7/backfill/progress", headers=_auth(token)
    ) as response:
        failed_body = "".join(response.iter_text())
    failed_list = client.get("/chats", headers=_auth(token)).json()["chats"][0]

    resumed_source = FakeSource(
        _channel(), _many_messages(205), live_ids=set(range(1, 206))
    )
    app.state.telegram_source_factory = lambda _link: resumed_source
    retried = client.post("/chats/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/chats/7/backfill/progress", headers=_auth(token)
    ) as response:
        retried_body = "".join(response.iter_text())
    retried_list = client.get("/chats", headers=_auth(token)).json()["chats"][0]

    assert started.status_code == 202
    assert "event: error" in failed_body
    assert failed_list["status"] == "failed"
    assert failed_list["fetched"] == 200
    assert failed_list["lastDate"] == "Jun 1, 2026"
    assert retried.status_code == 202
    assert retried.json()["jobId"] != started.json()["jobId"]
    assert resumed_source.requested_afters[0] == 200
    assert all(message_id > 200 for message_id in resumed_source.yielded_ids)
    assert "event: done" in retried_body
    assert retried_list["status"] == "backfilled"
    assert retried_list["fetched"] == 205
    assert retried_list["lastDate"] == "Jun 1, 2026"


def test_backfill_after_success_is_idempotent_and_does_not_restart(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    first = client.post("/chats/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/chats/7/backfill/progress", headers=_auth(token)
    ) as response:
        first_body = "".join(response.iter_text())
    fetches_after_first = len(source.requested_afters)

    second = client.post("/chats/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/chats/7/backfill/progress", headers=_auth(token)
    ) as response:
        second_body = "".join(response.iter_text())
    listed = client.get("/chats", headers=_auth(token)).json()["chats"][0]

    assert first.status_code == 202
    assert "event: done" in first_body
    assert second.status_code == 202
    assert second.json()["jobId"] == first.json()["jobId"]
    assert len(source.requested_afters) == fetches_after_first
    assert "event: done" in second_body
    assert listed["status"] == "backfilled"


def test_refresh_backfill_starts_new_run_and_resumes_from_cursor(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    first = client.post("/chats/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/chats/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())

    grown = FakeSource(_channel(), _many_messages(5), live_ids=set(range(1, 6)))
    app.state.telegram_source_factory = lambda _link: grown
    refreshed = client.post(
        "/chats/7/backfill", headers=_auth(token), json={"mode": "refresh"}
    )
    with client.stream(
        "GET", "/chats/7/backfill/progress", headers=_auth(token)
    ) as response:
        refreshed_body = "".join(response.iter_text())
    listed = client.get("/chats", headers=_auth(token)).json()["chats"][0]

    assert refreshed.status_code == 202
    assert refreshed.json()["jobId"] != first.json()["jobId"]
    assert grown.requested_afters[0] == 3
    assert all(message_id > 3 for message_id in grown.yielded_ids)
    assert "event: done" in refreshed_body
    assert listed["status"] == "backfilled"
    assert listed["fetched"] == 5


def test_full_backfill_resets_cursor_and_refetches_all(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    first = client.post("/chats/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/chats/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())

    refetch = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    app.state.telegram_source_factory = lambda _link: refetch
    full = client.post("/chats/7/backfill", headers=_auth(token), json={"mode": "full"})
    with client.stream(
        "GET", "/chats/7/backfill/progress", headers=_auth(token)
    ) as response:
        full_body = "".join(response.iter_text())
    listed = client.get("/chats", headers=_auth(token)).json()["chats"][0]

    assert full.status_code == 202
    assert full.json()["jobId"] != first.json()["jobId"]
    assert refetch.requested_afters[0] is None
    assert sorted(refetch.yielded_ids) == [1, 2, 3]
    assert "event: done" in full_body
    assert listed["status"] == "backfilled"
    assert listed["fetched"] == 3


def test_full_backfill_while_running_attaches_without_starting_second_job(client, app):
    token = _register(client)
    source = SlowSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    first = client.post("/chats/7/backfill", headers=_auth(token))
    attached = client.post(
        "/chats/7/backfill", headers=_auth(token), json={"mode": "full"}
    )
    client.post("/chats/7/backfill/cancel", headers=_auth(token))
    with client.stream(
        "GET", "/chats/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())

    assert first.status_code == 202
    assert attached.status_code == 202
    assert attached.json()["jobId"] == first.json()["jobId"]


def test_backfill_rescan_emits_scan_progress_so_stream_is_not_silent(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _many_messages(205), live_ids=set(range(1, 206)))
    _connect_and_subscribe(client, app, token, source)

    client.post("/chats/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/chats/7/backfill/progress", headers=_auth(token)
    ) as response:
        body = "".join(response.iter_text())

    assert "event: done" in body
    assert "scanned)" in body


def test_backfill_progress_stream_reports_cumulative_count_and_oldest_date(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _many_messages(5), live_ids={1, 2, 3, 4, 5})
    _connect_and_subscribe(client, app, token, source)

    started = client.post("/chats/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/chats/7/backfill/progress", headers=_auth(token)
    ) as response:
        body = "".join(response.iter_text())

    assert started.status_code == 202
    assert '"status": "running"' in body
    assert '"fetched": 5' in body
    assert '"lastDate": "Jun 1, 2026"' in body
    assert '"cursorMessageId": 5' in body


def test_stale_backfilling_subscription_is_reconciled_to_failed(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    with app.state.session_factory() as session:
        from verasig.features.accounts.tokens import read_user_id
        from verasig.features.sources.feed_repository import set_status

        user_id = read_user_id(token, app.state.jwt_secret)
        set_status(session, user_id, 7, "backfilling")
        session.commit()

    listed = client.get("/chats", headers=_auth(token))

    assert listed.status_code == 200
    assert listed.json()["chats"][0]["status"] == "failed"


def test_backfill_foreign_user_is_not_found(client, app):
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, owner, source)

    response = client.post("/chats/7/backfill", headers=_auth(other))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FEED_NOT_FOUND"


def test_backfill_progress_reports_missing_job_as_404(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    response = client.get("/chats/7/backfill/progress", headers=_auth(token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"


def test_readd_after_delete_refetches_from_zero(client, app):
    from verasig.features.accounts.tokens import read_user_id
    from verasig.features.sources import feed_repository, message_repository

    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    client.post("/chats/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/chats/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())
    assert client.get("/chats", headers=_auth(token)).json()["chats"][0]["fetched"] == 3

    assert client.delete("/chats/7", headers=_auth(token)).status_code == 204

    user_id = read_user_id(token, app.state.jwt_secret)
    with app.state.session_factory() as session:
        assert message_repository.count_messages(session, user_id, 7) == 0
        assert feed_repository.read_cursor(session, user_id, 7) is None

    readded = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    app.state.telegram_source_factory = lambda _link: readded
    assert (
        client.post("/chats", headers=_auth(token), json={"tag": "@pilot"}).status_code
        == 201
    )
    client.post("/chats/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/chats/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())

    assert readded.requested_afters[0] is None
    assert sorted(readded.yielded_ids) == [1, 2, 3]
    assert client.get("/chats", headers=_auth(token)).json()["chats"][0]["fetched"] == 3
