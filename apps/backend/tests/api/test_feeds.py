from datetime import datetime, timezone

from conftest import _auth
from conftest import _register_token as _register
from fakes import FakeSource, FakeTelegramAuth
from fakes import channel as _channel

from verasig.domain.channel_reference import ChannelReferenceResolutionError


def _connect_telegram(client, app, token: str) -> None:
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
            "/telegram/verify",
            headers=_auth(token),
            json={"code": "12345"},
        ).status_code
        == 200
    )


def test_get_feeds_empty(client):
    token = _register(client)

    response = client.get("/feeds", headers=_auth(token))

    assert response.status_code == 200
    assert response.json() == {"feeds": []}


def test_post_feed_subscribes_via_user_source(client, app):
    token = _register(client)
    _connect_telegram(client, app, token)
    app.state.telegram_source_factory = lambda _link: FakeSource(_channel(), [])

    created = client.post("/feeds", headers=_auth(token), json={"tag": "@pilot"})
    listed = client.get("/feeds", headers=_auth(token))

    assert created.status_code == 201
    assert created.json()["id"] == "7"
    assert listed.json()["feeds"][0]["name"] == "Pilot Signals"


def test_post_feed_unresolvable_channel_returns_404(client, app):
    token = _register(client)
    _connect_telegram(client, app, token)
    app.state.telegram_source_factory = lambda _link: FakeSource(
        _channel(),
        [],
        resolve_error=ChannelReferenceResolutionError("no such channel"),
    )

    response = client.post("/feeds", headers=_auth(token), json={"tag": "@ghost"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CHANNEL_NOT_FOUND"
    assert response.json()["error"]["message"] == "no such channel"


def test_post_feed_requires_telegram_link(client):
    token = _register(client)

    response = client.post("/feeds", headers=_auth(token), json={"tag": "@pilot"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TELEGRAM_NOT_CONNECTED"


def test_observer_second_feed_hits_source_limit(client, app):
    token = _register(client)
    _connect_telegram(client, app, token)
    app.state.telegram_source_factory = lambda _link: FakeSource(_channel(7), [])
    assert (
        client.post("/feeds", headers=_auth(token), json={"tag": "@pilot"}).status_code
        == 201
    )
    app.state.telegram_source_factory = lambda _link: FakeSource(_channel(8), [])

    response = client.post("/feeds", headers=_auth(token), json={"tag": "@other"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PLAN_LIMIT_SOURCES"


def test_observer_can_re_add_existing_feed_without_hitting_limit(client, app):
    # re-adding a feed the user already owns (same channel) is not a new source;
    # it must not be blocked by the observer single-source limit.
    token = _register(client)
    _connect_telegram(client, app, token)
    app.state.telegram_source_factory = lambda _link: FakeSource(_channel(7), [])
    assert (
        client.post("/feeds", headers=_auth(token), json={"tag": "@pilot"}).status_code
        == 201
    )

    response = client.post("/feeds", headers=_auth(token), json={"tag": "@pilot"})

    assert response.status_code == 201


def test_non_numeric_feed_id_returns_404_not_500(client, app):
    # require_feed casts external_id to int; a non-numeric id must 404, not 500.
    token = _register(client)

    response = client.delete("/feeds/not-a-number", headers=_auth(token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FEED_NOT_FOUND"


def test_delete_feed_purges_feed_and_masks_foreign_user(client, app):
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")
    _connect_telegram(client, app, owner)
    app.state.telegram_source_factory = lambda _link: FakeSource(_channel(), [])
    assert (
        client.post("/feeds", headers=_auth(owner), json={"tag": "@pilot"}).status_code
        == 201
    )

    foreign = client.delete("/feeds/7", headers=_auth(other))
    deleted = client.delete("/feeds/7", headers=_auth(owner))
    listed = client.get("/feeds", headers=_auth(owner))

    assert foreign.status_code == 404
    assert foreign.json()["error"]["code"] == "FEED_NOT_FOUND"
    assert deleted.status_code == 204
    assert listed.json() == {"feeds": []}


def test_delete_source_cascades_feeds_and_capture(client, app):
    from verasig.domain.message import RawTelegramMessage
    from verasig.features.accounts.tokens import read_user_id
    from verasig.features.feeds import (
        feed_repository,
        message_repository,
    )
    from verasig.features.sources import source_repository

    token = _register(client)
    _connect_telegram(client, app, token)
    app.state.telegram_source_factory = lambda _link: FakeSource(_channel(), [])
    assert (
        client.post("/feeds", headers=_auth(token), json={"tag": "@pilot"}).status_code
        == 201
    )

    user_id = read_user_id(token, app.state.jwt_secret)
    with app.state.session_factory() as session:
        message_repository.insert_messages(
            session,
            user_id,
            [
                RawTelegramMessage(
                    channel_id=7,
                    message_id=1,
                    posted_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
                    captured_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
                    has_media=False,
                    raw_payload={},
                )
            ],
        )
        session.commit()
        assert message_repository.count_messages(session, user_id, 7) == 1

    with app.state.session_factory() as session:
        source_repository.delete_source(session, user_id, "Telegram")
        session.commit()

    with app.state.session_factory() as session:
        assert feed_repository.read_feed(session, user_id, 7) is None
        assert message_repository.count_messages(session, user_id, 7) == 0
    assert client.get("/feeds", headers=_auth(token)).json() == {"feeds": []}
