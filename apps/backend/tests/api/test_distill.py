import json
from datetime import datetime, timezone

from seed import insert_source

from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.label import GoldenLabel, LabelKind
from verasig.domain.message import RawTelegramMessage
from verasig.features.accounts.tokens import read_user_id
from verasig.features.feeds import (
    feed_repository,
    message_repository,
)
from verasig.features.rules import repository as rule_repository
from verasig.features.rules.rule_distiller import AnthropicDistiller
from verasig.features.signals import event_repository

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


def _seed_chat(app, user_id, signal_count: int, noise_count: int = 0) -> None:
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
                first_seen_at=_instant(1),
            ),
            _instant(1),
        )
        signal_messages = [
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
        noise_messages = [
            RawTelegramMessage(
                channel_id=7,
                message_id=signal_count + idx,
                text=f"Market commentary {idx}",
                posted_at=_instant(signal_count + idx),
                captured_at=_instant(signal_count + idx),
                has_media=False,
                raw_payload={},
            )
            for idx in range(1, noise_count + 1)
        ]
        messages = [*signal_messages, *noise_messages]
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
                for message in signal_messages
            ],
        )
        rule_repository.upsert_labels(
            session,
            [
                GoldenLabel(
                    user_id=user_id,
                    channel_id=7,
                    message_id=message.message_id,
                    label=LabelKind.SIGNAL,
                )
                for message in signal_messages
            ]
            + [
                GoldenLabel(
                    user_id=user_id,
                    channel_id=7,
                    message_id=message.message_id,
                    label=LabelKind.NOISE,
                )
                for message in noise_messages
            ],
        )
        session.commit()


def test_distill_requires_five_signal_labels(client, app):
    token, user_id = _register(client)
    _seed_chat(app, user_id, signal_count=4)

    response = client.post("/feeds/7/distill", headers=_auth(token))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LABELS_INSUFFICIENT"


def test_distill_job_persists_rules_and_streams_progress(client, app):
    token, user_id = _register(client)
    _seed_chat(app, user_id, signal_count=5)
    responses = [
        json.dumps({"include_patterns": ["zzz"]}),
        json.dumps({"include_patterns": ["alpha"]}),
    ]

    def runner(_prompt: str) -> str:
        return responses.pop(0)

    app.state.distiller_factory = lambda: AnthropicDistiller(runner=runner)

    started = client.post("/feeds/7/distill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/distill/progress", headers=_auth(token)
    ) as response:
        body = "".join(response.iter_text())
    rules = client.get("/feeds/7/rules", headers=_auth(token))

    assert started.status_code == 202
    assert "Compiling filter ruleset" in body
    assert "event: done" in body
    assert responses == []
    assert rules.status_code == 200
    assert rules.json()["rules"] == [
        {
            "id": f"{user_id}:7-filter-v1:0",
            "label": "alpha",
            "detail": "alpha",
            "match": 100.0,
        }
    ]


def test_distill_job_emits_error_when_filter_never_validates(client, app):
    token, user_id = _register(client)
    _seed_chat(app, user_id, signal_count=5)
    responses = [json.dumps({"include_patterns": ["zzz"]}) for _ in range(3)]

    def runner(_prompt: str) -> str:
        return responses.pop(0)

    app.state.distiller_factory = lambda: AnthropicDistiller(runner=runner)

    started = client.post("/feeds/7/distill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/distill/progress", headers=_auth(token)
    ) as response:
        body = "".join(response.iter_text())
    rules = client.get("/feeds/7/rules", headers=_auth(token))

    assert started.status_code == 202
    assert "event: error" in body
    assert "filter distillation failed deterministic validation" in body
    assert "false_negative_message_ids" in body
    assert '"accuracy"' in body
    assert responses == []
    assert rules.json()["rules"] == []


def test_distill_progress_reports_missing_job_as_404(client, app):
    token, user_id = _register(client)
    _seed_chat(app, user_id, signal_count=5)

    response = client.get("/feeds/7/distill/progress", headers=_auth(token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"
