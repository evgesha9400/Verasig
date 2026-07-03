"""Mining Confirm endpoint end-to-end (ADR 0015).

POST /feeds/{id}/mining/rules persists the browser-compiled ruleset, re-derives
extraction, marks the feed verified server-side, and thereby unlocks Check gaps.
"""

from datetime import datetime, timezone

from fakes import FakeSource, FakeTelegramAuth

from verasig.domain.channel import TelegramChannel
from verasig.domain.message import RawTelegramMessage

_VALID_RULES = {
    "filterRule": {"includePatterns": ["LONG"]},
    "parserRules": [
        {
            "patterns": [r"(?P<symbol>\w+)\s+(?P<side>LONG|SHORT)"],
            "fieldMap": {"symbol": "symbol", "side": "side"},
            "sideAliases": {"long": "LONG", "short": "SHORT"},
        }
    ],
}


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
    texts = {1: "BTC LONG entry 100", 2: "gm everyone", 3: "ETH LONG entry 200"}
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


def _set_feed_status(app, token: str, status: str) -> None:
    from verasig.features.accounts.tokens import read_user_id
    from verasig.features.feeds import feed_repository

    user_id = read_user_id(token, app.state.jwt_secret)
    with app.state.session_factory() as session:
        feed_repository.set_status(session, user_id, 7, status)
        session.commit()


def test_confirm_mining_rules_persists_and_marks_verified(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))

    response = client.post(
        "/feeds/7/mining/rules", headers=_auth(token), json=_VALID_RULES
    )
    listed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert response.status_code == 200
    body = response.json()
    assert body["feedStatus"] == "verified"
    assert body["version"] == 1
    assert body["pipeline"]["signalsExtracted"] == 2
    assert listed["status"] == "verified"
    assert listed["hasRisk"] is True


def test_confirm_mining_rules_rejects_uncompilable_regex(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))

    bad = {
        "filterRule": {"includePatterns": ["(unclosed"]},
        "parserRules": _VALID_RULES["parserRules"],
    }
    response = client.post("/feeds/7/mining/rules", headers=_auth(token), json=bad)

    assert response.status_code == 422


def test_confirm_mining_rules_conflicts_while_backfilling(client, app):
    token = _register(client)
    _connect_and_subscribe(client, app, token, FakeSource(_channel(), _messages()))
    _set_feed_status(app, token, "backfilling")

    response = client.post(
        "/feeds/7/mining/rules", headers=_auth(token), json=_VALID_RULES
    )

    assert response.status_code == 409


def test_confirm_mining_rules_unlocks_check_gaps(client, app):
    token = _register(client)
    _backfill_to_done(
        client, app, token, FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    )

    before = client.post("/feeds/7/deletion-rescan", headers=_auth(token))
    client.post("/feeds/7/mining/rules", headers=_auth(token), json=_VALID_RULES)
    after = client.post("/feeds/7/deletion-rescan", headers=_auth(token))

    assert before.status_code == 409  # DELETION_RESCAN_NOT_READY before rules
    assert after.status_code == 202  # confirm unlocked it


def test_confirm_mining_rules_on_foreign_feed_is_404(client, app):
    token = _register(client)
    response = client.post(
        "/feeds/999/mining/rules", headers=_auth(token), json=_VALID_RULES
    )
    assert response.status_code == 404
