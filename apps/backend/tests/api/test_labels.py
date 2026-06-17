from datetime import datetime, timezone

from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.message import RawTelegramMessage
from verasig.features.accounts.tokens import read_user_id
from verasig.features.signals import event_repository
from verasig.features.sources import (
    feed_repository,
    message_repository,
)

SECRET = "s" * 32


def _register(client, email: str = "ada@example.com") -> tuple[str, str]:
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
    body = response.json()
    return body["token"], str(read_user_id(body["token"], SECRET))


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _instant(day: int) -> datetime:
    return datetime(2026, 6, day, 14, 32, tzinfo=timezone.utc)


def _seed_chat(app, user_id: str) -> None:
    with app.state.session_factory() as session:
        feed_repository.create_feed(
            session,
            user_id,
            TelegramChannel(
                channel_id=7,
                handle="pilot",
                title="Pilot Signals",
                is_private=False,
                first_seen_at=_instant(1),
            ),
            _instant(1),
        )
        message_repository.insert_messages(
            session,
            user_id,
            [
                RawTelegramMessage(
                    channel_id=7,
                    message_id=1,
                    text="BTC long",
                    posted_at=_instant(1),
                    captured_at=_instant(1),
                    has_media=False,
                    raw_payload={},
                ),
                RawTelegramMessage(
                    channel_id=7,
                    message_id=2,
                    text="ETH long",
                    posted_at=_instant(2),
                    captured_at=_instant(2),
                    has_media=True,
                    raw_payload={"document": {"id": 2}},
                ),
            ],
        )
        event_repository.insert_signal_events(
            session,
            user_id,
            [
                RawSignalEvent(
                    channel_id=7,
                    message_id=1,
                    candidate_text="BTC long",
                    materialized_by=MaterializationPath.SEED_HEURISTIC,
                ),
                RawSignalEvent(
                    channel_id=7,
                    message_id=2,
                    candidate_text="ETH long",
                    materialized_by=MaterializationPath.SEED_HEURISTIC,
                ),
            ],
        )
        session.commit()


def test_messages_label_and_counts(client, app):
    token, user_id = _register(client)
    _seed_chat(app, user_id)

    sample = client.get("/chats/7/messages", headers=_auth(token))
    first_label = client.post(
        "/chats/7/messages/1/label",
        headers=_auth(token),
        json={"label": "signal"},
    )
    relabel = client.post(
        "/chats/7/messages/1/label",
        headers=_auth(token),
        json={"label": "noise"},
    )
    counts = client.get("/chats/7/labels", headers=_auth(token))

    assert sample.status_code == 200
    assert [message["id"] for message in sample.json()["messages"]] == ["1", "2"]
    assert sample.json()["messages"][1]["media"] == "doc"
    assert first_label.status_code == 204
    assert relabel.status_code == 204
    assert counts.json() == {
        "signalCount": 0,
        "noiseCount": 1,
        "modifierCount": 0,
        "total": 1,
    }


def test_label_rejects_unknown_value(client, app):
    token, user_id = _register(client)
    _seed_chat(app, user_id)

    response = client.post(
        "/chats/7/messages/1/label",
        headers=_auth(token),
        json={"label": "maybe"},
    )

    assert response.status_code == 422


def test_label_routes_mask_foreign_user(client, app):
    owner, owner_id = _register(client, "owner@example.com")
    other, _other_id = _register(client, "other@example.com")
    _seed_chat(app, owner_id)

    responses = [
        client.get("/chats/7/messages", headers=_auth(other)),
        client.post(
            "/chats/7/messages/1/label",
            headers=_auth(other),
            json={"label": "signal"},
        ),
        client.get("/chats/7/labels", headers=_auth(other)),
    ]

    assert owner
    assert [response.status_code for response in responses] == [404, 404, 404]
    assert {response.json()["error"]["code"] for response in responses} == {
        "CHAT_NOT_FOUND"
    }
