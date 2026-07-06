"""Mining Confirmed read endpoint end-to-end (resume source for Verify).

GET /feeds/{id}/mining/confirmed lists the accepted template keys recovered from
persisted ExtractedSignals (``rule_id`` == ``template_key``) — no re-mine, no
migration. Only signal-bearing families ever appear. Mirrors the confirm-route
harness so the two endpoints share exactly one setup path.
"""

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
    texts = {
        1: "BTC LONG entry 100 sl 95 tp 110",
        2: "gm everyone",
        3: "ETH LONG entry 200 sl 190 tp 210",
    }
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
        for message_id, text in texts.items()
    ]


def _connect_and_subscribe(client, app, token: str, source) -> None:
    app.state.telegram_auth = FakeTelegramAuth()
    client.post(
        "/telegram/connect",
        headers=_auth(token),
        json={"apiId": 123, "apiHash": "api-secret", "phone": "+441234568821"},
    )
    client.post("/telegram/verify", headers=_auth(token), json={"code": "12345"})
    app.state.telegram_source_factory = lambda _link: source
    assert (
        client.post("/feeds", headers=_auth(token), json={"tag": "@pilot"}).status_code
        == 201
    )


def _backfill_to_done(client, app, token: str, source) -> None:
    _connect_and_subscribe(client, app, token, source)
    client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())


def _mined_keys(client, app, token: str) -> list[str]:
    """The template_keys the miner yields for the stored feed — what the client
    reviews and accepts before POSTing confirm (see test_mining_confirm_route)."""
    from verasig.features.accounts.tokens import read_user_id
    from verasig.features.feeds import message_repository
    from verasig.features.parser_overlay.repository import read_overlay
    from verasig.features.rules.mining_confirm import _to_chat_message
    from verasig.features.rules.template_mining import mine_template_groups

    user_id = read_user_id(token, app.state.jwt_secret)
    with app.state.session_factory() as session:
        messages = message_repository.read_messages(session, user_id, 7)
        overlay = read_overlay(session, user_id)
    groups = mine_template_groups([_to_chat_message(m) for m in messages], overlay)
    return [group.template_key for group in groups]


def test_confirmed_lists_accepted_keys_after_confirm(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))
    keys = _mined_keys(client, app, token)

    client.post(
        "/feeds/7/mining/confirm",
        headers=_auth(token),
        json={"acceptedTemplateKeys": keys},
    )
    response = client.get("/feeds/7/mining/confirmed", headers=_auth(token))

    assert response.status_code == 200
    confirmed = response.json()["acceptedTemplateKeys"]
    assert confirmed  # signal-bearing families persisted a rule_id to recover
    assert set(confirmed) <= set(keys)  # never a key we did not accept


def test_confirmed_is_empty_before_any_confirm(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))

    response = client.get("/feeds/7/mining/confirmed", headers=_auth(token))

    assert response.status_code == 200
    assert response.json()["acceptedTemplateKeys"] == []


def test_confirmed_is_empty_when_confirm_accepted_no_keys(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))

    client.post(
        "/feeds/7/mining/confirm",
        headers=_auth(token),
        json={"acceptedTemplateKeys": []},
    )
    response = client.get("/feeds/7/mining/confirmed", headers=_auth(token))

    assert response.status_code == 200
    assert response.json()["acceptedTemplateKeys"] == []


def test_confirmed_on_foreign_feed_is_404(client, app):
    token = _register(client)
    response = client.get("/feeds/999/mining/confirmed", headers=_auth(token))
    assert response.status_code == 404
