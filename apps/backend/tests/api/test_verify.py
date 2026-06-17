from datetime import datetime, timezone
from uuid import UUID

from seed import insert_source

from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.filter_rule import FilterRule
from verasig.domain.message import RawTelegramMessage
from verasig.features.accounts.tokens import read_user_id
from verasig.features.rules import repository as rule_repository
from verasig.features.signals import event_repository
from verasig.features.sources import (
    feed_repository,
    message_repository,
)

SECRET = "s" * 32


def _register(client, email: str = "ada@example.com") -> tuple[str, UUID]:
    response = client.post(
        "/auth/register",
        json={
            "firstName": "Ada",
            "lastName": "Lovelace",
            "email": email,
            "password": "correct horse battery staple",
        },
    )
    body = response.json()
    return body["token"], read_user_id(body["token"], SECRET)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _seed(app, user_id: UUID) -> None:
    with app.state.session_factory() as session:
        insert_source(session, user_id)
        feed_repository.create_feed(
            session,
            user_id,
            TelegramChannel(
                channel_id=7,
                handle="pilot",
                title="Pilot Signals",
                is_private=False,
                first_seen_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            ),
            datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        messages = [
            RawTelegramMessage(
                channel_id=7,
                message_id=idx,
                text=("alpha" if idx <= 3 else "beta"),
                posted_at=datetime(2026, 6, idx, tzinfo=timezone.utc),
                captured_at=datetime(2026, 6, idx, tzinfo=timezone.utc),
                has_media=False,
                raw_payload={},
            )
            for idx in range(1, 7)
        ]
        message_repository.insert_messages(session, user_id, messages)
        event_repository.insert_signal_events(
            session,
            user_id,
            [
                RawSignalEvent(
                    channel_id=7,
                    message_id=message.message_id,
                    candidate_text=message.text,
                    materialized_by=MaterializationPath.SEED_HEURISTIC,
                )
                for message in messages
            ],
        )
        rule_repository.upsert_filter_rule(
            session,
            FilterRule(
                rule_id=f"{user_id}:7-filter-v1",
                user_id=user_id,
                channel_id=7,
                include_patterns=["alpha"],
            ),
        )
        session.commit()


def test_verify_samples_and_submit_verdicts(client, app):
    token, user_id = _register(client)
    _seed(app, user_id)

    samples = client.get("/chats/7/verify/samples", headers=_auth(token))
    mixed = client.post(
        "/chats/7/verify",
        headers=_auth(token),
        json={
            "verdicts": [
                {"messageId": str(idx), "verdict": "wrong" if idx == 4 else "correct"}
                for idx in range(1, 7)
            ]
        },
    )
    passed = client.post(
        "/chats/7/verify",
        headers=_auth(token),
        json={
            "verdicts": [
                {"messageId": str(idx), "verdict": "correct"} for idx in range(1, 7)
            ]
        },
    )

    assert samples.status_code == 200
    assert samples.json()["attempt"] == 1
    assert samples.json()["samples"][0]["predicted"] == "signal"
    assert mixed.json() == {"passed": False, "misclassified": ["4"]}
    assert passed.json() == {"passed": True, "misclassified": []}


def test_verify_rejects_too_few_verdicts(client, app):
    token, user_id = _register(client)
    _seed(app, user_id)

    response = client.post(
        "/chats/7/verify",
        headers=_auth(token),
        json={
            "verdicts": [
                {"messageId": str(idx), "verdict": "correct"} for idx in range(1, 6)
            ]
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VERIFY_TOO_FEW_VERDICTS"


def test_verify_routes_mask_foreign_user(client, app):
    owner, owner_id = _register(client, "owner@example.com")
    other, _other_id = _register(client, "other@example.com")
    _seed(app, owner_id)

    responses = [
        client.get("/chats/7/verify/samples", headers=_auth(other)),
        client.post(
            "/chats/7/verify",
            headers=_auth(other),
            json={
                "verdicts": [
                    {"messageId": str(idx), "verdict": "correct"} for idx in range(1, 7)
                ]
            },
        ),
    ]

    assert owner
    assert [response.status_code for response in responses] == [404, 404]
    assert {response.json()["error"]["code"] for response in responses} == {
        "CHAT_NOT_FOUND"
    }
