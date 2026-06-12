import json
from datetime import datetime, timezone

from fakes import FakeDistiller

from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.label import GoldenLabel, LabelKind
from verasig.domain.message import RawTelegramMessage
from verasig.services.accounts.tokens import read_user_id
from verasig.storage import repositories as repo
from verasig.storage import user_channel_repository

SECRET = "s" * 32


def _register(client) -> tuple[str, object]:
    response = client.post(
        "/auth/register",
        json={
            "firstName": "Ada",
            "lastName": "Lovelace",
            "email": "ada@example.com",
            "password": "correct horse battery staple",
        },
    )
    body = response.json()
    return body["token"], read_user_id(body["token"], SECRET)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _instant(day: int) -> datetime:
    return datetime(2026, 6, day, 14, 32, tzinfo=timezone.utc)


def _seed_chat(app, user_id, signal_count: int) -> None:
    with app.state.session_factory() as session:
        repo.upsert_channel(
            session,
            TelegramChannel(
                channel_id=7,
                handle="pilot",
                title="Pilot Signals",
                is_private=False,
                first_seen_at=_instant(1),
            ),
        )
        messages = [
            RawTelegramMessage(
                channel_id=7,
                message_id=idx,
                text=f"BTC alpha long {idx}",
                posted_at=_instant(idx),
                captured_at=_instant(idx),
                has_media=False,
                raw_payload={},
            )
            for idx in range(1, signal_count + 1)
        ]
        repo.insert_messages(session, messages)
        repo.insert_signal_events(
            session,
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
        repo.upsert_labels(
            session,
            [
                GoldenLabel(
                    user_id=user_id,
                    channel_id=7,
                    message_id=message.message_id,
                    label=LabelKind.SIGNAL,
                )
                for message in messages
            ],
        )
        user_channel_repository.subscribe(session, user_id, 7, _instant(1))
        session.commit()


def _distiller_stdout() -> str:
    return json.dumps(
        {
            "filter_rule": {
                "include_patterns": ["alpha"],
                "display": [{"label": "Alpha", "detail": "Mentions alpha"}],
            },
            "parser_rules": [],
        }
    )


def test_distill_requires_five_signal_labels(client, app):
    token, user_id = _register(client)
    _seed_chat(app, user_id, signal_count=4)

    response = client.post("/chats/7/distill", headers=_auth(token))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LABELS_INSUFFICIENT"


def test_distill_job_persists_rules_and_streams_progress(client, app):
    token, user_id = _register(client)
    _seed_chat(app, user_id, signal_count=5)
    app.state.distiller_factory = lambda: FakeDistiller(_distiller_stdout())

    started = client.post("/chats/7/distill", headers=_auth(token))
    with client.stream(
        "GET", "/chats/7/distill/progress", headers=_auth(token)
    ) as response:
        body = "".join(response.iter_text())
    rules = client.get("/chats/7/rules", headers=_auth(token))

    assert started.status_code == 202
    assert "Compiling filter ruleset" in body
    assert "event: done" in body
    assert rules.status_code == 200
    assert rules.json()["rules"] == [
        {
            "id": f"{user_id}:7-filter-v1:0",
            "label": "Alpha",
            "detail": "Mentions alpha",
            "match": 100.0,
        }
    ]
