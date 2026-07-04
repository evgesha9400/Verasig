import asyncio
import logging
from contextlib import contextmanager
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


class _MessageLogHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.INFO)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


_APP_LOGGER_NAMES = (
    "verasig",
    "verasig.features.feeds.backfill_job_coordinator",
    "verasig.features.feeds.deletion_rescan",
)


@contextmanager
def _capture_app_logs():
    handler = _MessageLogHandler()
    loggers = [logging.getLogger(name) for name in _APP_LOGGER_NAMES]
    previous_levels = {logger: logger.level for logger in loggers}
    previous_disabled = {logger: logger.disabled for logger in loggers}
    for logger in loggers:
        logger.setLevel(logging.INFO)
        logger.disabled = False
        logger.addHandler(handler)
    try:
        yield handler.messages
    finally:
        for logger in loggers:
            logger.removeHandler(handler)
            logger.setLevel(previous_levels[logger])
            logger.disabled = previous_disabled[logger]


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
    async def backfill_batches(
        self, channel_id, after_message_id, batch_size, since=None
    ):
        await asyncio.sleep(0.2)
        async for batch in super().backfill_batches(
            channel_id, after_message_id, batch_size, since=since
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
        client.post("/feeds", headers=_auth(token), json={"tag": "@pilot"}).status_code
        == 201
    )


def _set_feed_status(app, token: str, status: str) -> None:
    from verasig.features.accounts.tokens import read_user_id
    from verasig.features.feeds import feed_repository

    user_id = read_user_id(token, app.state.jwt_secret)
    with app.state.session_factory() as session:
        feed_repository.set_status(session, user_id, 7, status)
        session.commit()


def test_backfill_streams_progress_and_indexes_without_deletion_scan(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 3})
    _connect_and_subscribe(client, app, token, source)

    started = client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        body = "".join(response.iter_text())
    listed = client.get("/feeds", headers=_auth(token))

    assert started.status_code == 202
    assert "event: progress" in body
    assert "event: done" in body
    assert '"stage"' in body  # progress carries a coarse stage for the UI strip
    assert "Checking deleted messages" not in body  # a fetch runs no deletion scan
    feed = listed.json()["feeds"][0]
    assert feed["status"] == "backfilled"
    # a plain backfill no longer detects deletions — that is the Check gaps rescan
    assert feed["deletedCount"] == 0
    assert feed["signalDeletion"] is False


def test_backfill_persists_selected_history_depth(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 3})
    _connect_and_subscribe(client, app, token, source)

    started = client.post(
        "/feeds/7/backfill",
        headers=_auth(token),
        json={"mode": "resume", "depth": "6m"},
    )
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())
    listed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert started.status_code == 202
    assert listed["historyDepth"] == "6m"


def test_backfill_defaults_history_depth_to_one_year(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 3})
    _connect_and_subscribe(client, app, token, source)

    client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())
    listed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert listed["historyDepth"] == "1y"


def test_backfill_rejects_unknown_history_depth(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 3})
    _connect_and_subscribe(client, app, token, source)

    response = client.post(
        "/feeds/7/backfill", headers=_auth(token), json={"depth": "2y"}
    )

    assert response.status_code == 422


def test_backfill_duplicate_start_and_cancel(client, app):
    token = _register(client)
    source = SlowSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    first = client.post("/feeds/7/backfill", headers=_auth(token))
    duplicate = client.post("/feeds/7/backfill", headers=_auth(token))
    cancelled = client.post("/feeds/7/backfill/cancel", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        body = "".join(response.iter_text())
    listed = client.get("/feeds", headers=_auth(token))

    assert first.status_code == 202
    assert duplicate.status_code == 202
    assert duplicate.json()["jobId"] == first.json()["jobId"]
    assert cancelled.status_code == 204
    assert "event: error" in body
    assert "cancelled" in body
    assert listed.json()["feeds"][0]["status"] == "cancelled"


def test_failed_backfill_can_retry_from_persisted_cursor(client, app):
    token = _register(client)
    failed_source = FakeSource(
        _channel(), _many_messages(205), live_ids={1, 2}, fail_after_batch=1
    )
    _connect_and_subscribe(client, app, token, failed_source)

    started = client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        failed_body = "".join(response.iter_text())
    failed_list = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    resumed_source = FakeSource(
        _channel(), _many_messages(205), live_ids=set(range(1, 206))
    )
    app.state.telegram_source_factory = lambda _link: resumed_source
    retried = client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        retried_body = "".join(response.iter_text())
    retried_list = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

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

    first = client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        first_body = "".join(response.iter_text())
    fetches_after_first = len(source.requested_afters)

    second = client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        second_body = "".join(response.iter_text())
    listed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

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

    first = client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())

    grown = FakeSource(_channel(), _many_messages(5), live_ids=set(range(1, 6)))
    app.state.telegram_source_factory = lambda _link: grown
    refreshed = client.post(
        "/feeds/7/backfill", headers=_auth(token), json={"mode": "refresh"}
    )
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        refreshed_body = "".join(response.iter_text())
    listed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert refreshed.status_code == 202
    assert refreshed.json()["jobId"] != first.json()["jobId"]
    assert grown.requested_afters[0] == 3
    assert all(message_id > 3 for message_id in grown.yielded_ids)
    assert "event: done" in refreshed_body
    assert listed["status"] == "backfilled"
    assert listed["fetched"] == 5


def test_verified_feed_refresh_restores_verified_status(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    first = client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())
    _set_feed_status(app, token, "verified")

    grown = FakeSource(_channel(), _many_messages(5), live_ids=set(range(1, 6)))
    app.state.telegram_source_factory = lambda _link: grown
    refreshed = client.post(
        "/feeds/7/backfill", headers=_auth(token), json={"mode": "refresh"}
    )
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        refreshed_body = "".join(response.iter_text())
    listed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert first.status_code == 202
    assert refreshed.status_code == 202
    assert "event: done" in refreshed_body
    assert listed["status"] == "verified"
    assert listed["fetched"] == 5


def test_analyzed_feed_refresh_restores_analyzed_status(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())
    _set_feed_status(app, token, "analyzed")

    grown = FakeSource(_channel(), _many_messages(5), live_ids=set(range(1, 6)))
    app.state.telegram_source_factory = lambda _link: grown
    refreshed = client.post(
        "/feeds/7/backfill", headers=_auth(token), json={"mode": "refresh"}
    )
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        refreshed_body = "".join(response.iter_text())
    listed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert refreshed.status_code == 202
    assert "event: done" in refreshed_body
    assert listed["status"] == "analyzed"
    assert listed["fetched"] == 5


def test_full_backfill_resets_cursor_and_refetches_all(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    first = client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())

    refetch = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    app.state.telegram_source_factory = lambda _link: refetch
    full = client.post("/feeds/7/backfill", headers=_auth(token), json={"mode": "full"})
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        full_body = "".join(response.iter_text())
    listed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert full.status_code == 202
    assert full.json()["jobId"] != first.json()["jobId"]
    assert refetch.requested_afters[0] is None
    assert sorted(refetch.yielded_ids) == [1, 2, 3]
    assert "event: done" in full_body
    assert listed["status"] == "backfilled"
    assert listed["fetched"] == 3


def test_full_refetch_wipes_and_recaptures_without_securing_evidence(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)
    client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())

    # message 2 vanished upstream: the recapture simply sees {1,3}
    survivors = [message for message in _messages() if message.message_id != 2]
    refetch = FakeSource(_channel(), survivors, live_ids={1, 3})
    app.state.telegram_source_factory = lambda _link: refetch
    full = client.post("/feeds/7/backfill", headers=_auth(token), json={"mode": "full"})
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        body = "".join(response.iter_text())
    listed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert full.status_code == 202
    assert "Securing deletion evidence" not in body  # a wipe & re-fetch secures nothing
    assert "Checking deleted messages" not in body  # and runs no deletion scan
    assert "event: done" in body
    assert listed["fetched"] == 2  # counter restarted; only survivors recaptured
    assert listed["deletedCount"] == 0  # deletion detection is the Check gaps rescan


def test_full_refetch_progress_never_shows_stale_pre_wipe_total(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _many_messages(5), live_ids=set(range(1, 6)))
    _connect_and_subscribe(client, app, token, source)
    client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())
    assert client.get("/feeds", headers=_auth(token)).json()["feeds"][0]["fetched"] == 5

    # Only messages 1 and 2 still live upstream: the full re-fetch wipes the old
    # capture of 5 and recaptures 2. The counter must restart at 0 for the new
    # generation, so the stale pre-wipe total (5) must never reach the stream.
    survivors = _many_messages(5)[:2]
    refetch = FakeSource(_channel(), survivors, live_ids={1, 2})
    app.state.telegram_source_factory = lambda _link: refetch
    full = client.post("/feeds/7/backfill", headers=_auth(token), json={"mode": "full"})
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        body = "".join(response.iter_text())
    listed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert full.status_code == 202
    assert '"fetched": 5' not in body  # the doomed old total must never appear
    assert "event: done" in body
    assert listed["fetched"] == 2  # only the survivors recaptured


def test_full_refetch_aborts_without_wiping_when_channel_unreachable(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)
    client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())

    # channel no longer resolves — the reachability guard must abort before wiping
    refetch = FakeSource(
        _channel(), _messages(), resolve_error=RuntimeError("channel gone")
    )
    app.state.telegram_source_factory = lambda _link: refetch
    full = client.post("/feeds/7/backfill", headers=_auth(token), json={"mode": "full"})
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        body = "".join(response.iter_text())
    listed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert full.status_code == 202
    assert "event: error" in body
    assert listed["fetched"] == 3  # original capture intact — nothing wiped


def test_verified_feed_full_refetch_restores_verified_status(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())
    _set_feed_status(app, token, "verified")

    refetch = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    app.state.telegram_source_factory = lambda _link: refetch
    full = client.post("/feeds/7/backfill", headers=_auth(token), json={"mode": "full"})
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        full_body = "".join(response.iter_text())
    listed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert full.status_code == 202
    assert refetch.requested_afters[0] is None
    assert "event: done" in full_body
    assert listed["status"] == "verified"
    assert listed["fetched"] == 3


def test_analyzed_feed_failed_refresh_restores_analyzed_status(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())
    _set_feed_status(app, token, "analyzed")

    failed = FakeSource(
        _channel(), _many_messages(205), live_ids=set(range(1, 206)), fail_after_batch=0
    )
    app.state.telegram_source_factory = lambda _link: failed
    refreshed = client.post(
        "/feeds/7/backfill", headers=_auth(token), json={"mode": "refresh"}
    )
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        failed_body = "".join(response.iter_text())
    listed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert refreshed.status_code == 202
    assert "event: error" in failed_body
    assert listed["status"] == "analyzed"
    assert listed["fetched"] == 3


def test_verified_feed_cancelled_refresh_restores_verified_status(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())
    _set_feed_status(app, token, "verified")

    slow = SlowSource(_channel(), _many_messages(5), live_ids=set(range(1, 6)))
    app.state.telegram_source_factory = lambda _link: slow
    refreshed = client.post(
        "/feeds/7/backfill", headers=_auth(token), json={"mode": "refresh"}
    )
    cancelled = client.post("/feeds/7/backfill/cancel", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        cancelled_body = "".join(response.iter_text())
    listed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert refreshed.status_code == 202
    assert cancelled.status_code == 204
    assert "event: error" in cancelled_body
    assert listed["status"] == "verified"


def test_full_backfill_while_running_attaches_without_starting_second_job(client, app):
    token = _register(client)
    source = SlowSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    first = client.post("/feeds/7/backfill", headers=_auth(token))
    attached = client.post(
        "/feeds/7/backfill", headers=_auth(token), json={"mode": "full"}
    )
    client.post("/feeds/7/backfill/cancel", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())

    assert first.status_code == 202
    assert attached.status_code == 202
    assert attached.json()["jobId"] == first.json()["jobId"]


def test_backfill_progress_stream_reports_cumulative_count_and_oldest_date(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _many_messages(5), live_ids={1, 2, 3, 4, 5})
    _connect_and_subscribe(client, app, token, source)

    started = client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        body = "".join(response.iter_text())

    assert started.status_code == 202
    assert '"status": "running"' in body
    assert '"fetched": 5' in body
    assert '"lastDate": "Jun 1, 2026"' in body
    assert '"cursorExternalMessageId": 5' in body


def test_backfill_logs_history_progress(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _many_messages(205), live_ids=set(range(1, 206)))
    _connect_and_subscribe(client, app, token, source)

    with _capture_app_logs() as messages:
        client.post("/feeds/7/backfill", headers=_auth(token))
        with client.stream(
            "GET", "/feeds/7/backfill/progress", headers=_auth(token)
        ) as response:
            "".join(response.iter_text())

    logs = "\n".join(messages)
    assert "feed_job.progress: operation=backfill external_id=7" in logs
    assert "phase=Reading channel history..." in logs
    assert "fetched=200" in logs
    assert "Checking deleted messages" not in logs  # a fetch runs no deletion scan


def test_refresh_backfill_logs_fetch_latest_progress(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    with _capture_app_logs() as messages:
        client.post("/feeds/7/backfill", headers=_auth(token))
        with client.stream(
            "GET", "/feeds/7/backfill/progress", headers=_auth(token)
        ) as response:
            "".join(response.iter_text())
        messages.clear()

        grown = FakeSource(_channel(), _many_messages(5), live_ids=set(range(1, 6)))
        app.state.telegram_source_factory = lambda _link: grown
        client.post("/feeds/7/backfill", headers=_auth(token), json={"mode": "refresh"})
        with client.stream(
            "GET", "/feeds/7/backfill/progress", headers=_auth(token)
        ) as response:
            "".join(response.iter_text())

    logs = "\n".join(messages)
    assert "feed_job.progress: operation=fetch_latest_messages external_id=7" in logs
    assert "mode=refresh" in logs
    assert "fetched=5" in logs


def test_full_backfill_logs_rebackfill_progress(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    with _capture_app_logs() as messages:
        client.post("/feeds/7/backfill", headers=_auth(token))
        with client.stream(
            "GET", "/feeds/7/backfill/progress", headers=_auth(token)
        ) as response:
            "".join(response.iter_text())
        messages.clear()

        refetch = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
        app.state.telegram_source_factory = lambda _link: refetch
        client.post("/feeds/7/backfill", headers=_auth(token), json={"mode": "full"})
        with client.stream(
            "GET", "/feeds/7/backfill/progress", headers=_auth(token)
        ) as response:
            "".join(response.iter_text())

    logs = "\n".join(messages)
    assert "feed_job.progress: operation=rebackfill external_id=7" in logs
    assert "mode=full" in logs
    assert "phase=Reading channel history..." in logs


def test_stale_backfilling_subscription_is_reconciled_to_failed(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    with app.state.session_factory() as session:
        from verasig.features.accounts.tokens import read_user_id
        from verasig.features.feeds.feed_repository import set_status

        user_id = read_user_id(token, app.state.jwt_secret)
        set_status(session, user_id, 7, "backfilling")
        session.commit()

    listed = client.get("/feeds", headers=_auth(token))

    assert listed.status_code == 200
    assert listed.json()["feeds"][0]["status"] == "failed"


def test_backfill_foreign_user_is_not_found(client, app):
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, owner, source)

    response = client.post("/feeds/7/backfill", headers=_auth(other))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FEED_NOT_FOUND"


def test_backfill_progress_reports_missing_job_as_404(client, app):
    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    response = client.get("/feeds/7/backfill/progress", headers=_auth(token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"


def test_readd_after_delete_refetches_from_zero(client, app):
    from verasig.features.accounts.tokens import read_user_id
    from verasig.features.feeds import feed_repository, message_repository

    token = _register(client)
    source = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    _connect_and_subscribe(client, app, token, source)

    client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())
    assert client.get("/feeds", headers=_auth(token)).json()["feeds"][0]["fetched"] == 3

    assert client.delete("/feeds/7", headers=_auth(token)).status_code == 204

    user_id = read_user_id(token, app.state.jwt_secret)
    with app.state.session_factory() as session:
        assert message_repository.count_messages(session, user_id, 7) == 0
        assert feed_repository.read_cursor(session, user_id, 7) is None

    readded = FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    app.state.telegram_source_factory = lambda _link: readded
    assert (
        client.post("/feeds", headers=_auth(token), json={"tag": "@pilot"}).status_code
        == 201
    )
    client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())

    assert readded.requested_afters[0] is None
    assert sorted(readded.yielded_ids) == [1, 2, 3]
    assert client.get("/feeds", headers=_auth(token)).json()["feeds"][0]["fetched"] == 3
