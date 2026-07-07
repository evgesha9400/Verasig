import logging
from contextlib import contextmanager
from datetime import datetime, timezone

from conftest import _auth
from conftest import _register_token as _register
from fakes import FakeSource, FakeTelegramAuth
from fakes import channel as _channel

from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import Side, Signal
from verasig.features.accounts.tokens import read_user_id
from verasig.features.feeds import feed_repository, message_repository
from verasig.features.signals import outcome_repository

_CHANNEL_ID = 7
_INSTANT = datetime(2026, 6, 1, tzinfo=timezone.utc)


class _MessageLogHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.INFO)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


_APP_LOGGER_NAMES = (
    "verasig",
    "verasig.features.feeds.routes",
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


def _message(message_id: int, text: str) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=_CHANNEL_ID,
        message_id=message_id,
        text=text,
        posted_at=_INSTANT,
        captured_at=_INSTANT,
        has_media=False,
        raw_payload={},
    )


def _connect_and_subscribe(client, app, token: str) -> None:
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
    app.state.telegram_source_factory = lambda _link: FakeSource(_channel(), [])
    assert (
        client.post("/feeds", headers=_auth(token), json={"tag": "@pilot"}).status_code
        == 201
    )


def _user_id(token: str, app):
    return read_user_id(token, app.state.jwt_secret)


def _seed_feed_state(
    app, token: str, status: str, signal_message_ids: set[int]
) -> None:
    user_id = _user_id(token, app)
    messages = [
        _message(1, "gm"),
        _message(2, "BTC long 65000"),
        _message(3, "trail stop"),
        _message(5, "still live"),
    ]
    with app.state.session_factory() as session:
        message_repository.insert_messages(session, user_id, messages)
        if signal_message_ids:
            outcome_repository.insert_signals(
                session,
                [_signal(message_id) for message_id in sorted(signal_message_ids)],
                user_id,
            )
        feed_repository.set_status(session, user_id, _CHANNEL_ID, status)
        session.commit()


def _signal(message_id: int) -> Signal:
    return Signal(
        channel_id=_CHANNEL_ID,
        message_id=message_id,
        candidate_text="BTC long 65000",
        symbol="BTCUSDT",
        side=Side.LONG,
        extracted_at=_INSTANT,
    )


def _run_rescan(client, app, token: str, live_ids: set[int]) -> str:
    app.state.telegram_source_factory = lambda _link: FakeSource(
        _channel(), [], live_ids=live_ids
    )
    started = client.post("/feeds/7/deletion-rescan", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/deletion-rescan/progress", headers=_auth(token)
    ) as response:
        body = "".join(response.iter_text())
    assert started.status_code == 202
    return body


def test_deletion_rescan_streams_signal_deletion_and_keeps_status(client, app):
    token = _register(client)
    _connect_and_subscribe(client, app, token)
    _seed_feed_state(app, token, "verified", {2})

    body = _run_rescan(client, app, token, {1, 3, 4, 5})
    feed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert "event: progress" in body
    assert "event: done" in body
    assert '"newDeletedSignalCount": 1' in body
    assert '"newDeletedNonSignalCount": 0' in body
    assert '"totalDeletedCount": 1' in body
    assert '"signalDeletion": true' in body
    assert feed["status"] == "verified"
    assert feed["signalDeletion"] is True
    assert feed["deletedCount"] == 1


def test_deletion_rescan_logs_shared_scan_progress(client, app):
    token = _register(client)
    _connect_and_subscribe(client, app, token)
    _seed_feed_state(app, token, "verified", {2})

    with _capture_app_logs() as messages:
        _run_rescan(client, app, token, set(range(1, 206)) - {2})

    logs = "\n".join(messages)
    assert "feed_job.progress: operation=deletion_rescan external_id=7" in logs
    assert "phase=Checking deleted messages... (200 scanned)" in logs
    assert "scanned=200" in logs


def test_deletion_rescan_reports_non_signal_deletions_without_scam(client, app):
    token = _register(client)
    _connect_and_subscribe(client, app, token)
    _seed_feed_state(app, token, "analyzed", set())

    body = _run_rescan(client, app, token, {1, 5})
    feed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert '"newDeletedSignalCount": 0' in body
    assert '"newDeletedNonSignalCount": 2' in body
    assert (
        '"totalDeletedCount": 2' in body
    )  # confirmed only; the id-4 gap isn't counted
    assert '"signalDeletion": false' in body
    assert feed["status"] == "analyzed"
    assert feed["signalDeletion"] is False
    assert feed["deletedCount"] == 2


def test_deletion_rescan_rerun_reports_zero_new_evidence(client, app):
    token = _register(client)
    _connect_and_subscribe(client, app, token)
    _seed_feed_state(app, token, "verified", {2})

    _run_rescan(client, app, token, {1, 3, 4, 5})
    body = _run_rescan(client, app, token, {1, 3, 4, 5})
    feed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert '"newDeletedSignalCount": 0' in body
    assert '"newDeletedNonSignalCount": 0' in body
    assert '"totalDeletedCount": 1' in body
    assert '"signalDeletion": true' in body
    assert feed["deletedCount"] == 1


def test_deletion_rescan_empty_live_snapshot_errors_and_writes_nothing(client, app):
    token = _register(client)
    _connect_and_subscribe(client, app, token)
    _seed_feed_state(app, token, "verified", {2})

    body = _run_rescan(client, app, token, set())
    feed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert "event: error" in body
    assert "EMPTY_LIVE_SNAPSHOT" in body
    assert feed["signalDeletion"] is False
    assert feed["deletedCount"] == 0


def test_deletion_rescan_blocks_foreign_user(client, app):
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")
    _connect_and_subscribe(client, app, owner)
    _seed_feed_state(app, owner, "verified", {2})

    response = client.post("/feeds/7/deletion-rescan", headers=_auth(other))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FEED_NOT_FOUND"


def test_deletion_rescan_requires_reviewed_feed(client, app):
    token = _register(client)
    _connect_and_subscribe(client, app, token)
    _seed_feed_state(app, token, "backfilled", set())

    response = client.post("/feeds/7/deletion-rescan", headers=_auth(token))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DELETION_RESCAN_NOT_READY"
