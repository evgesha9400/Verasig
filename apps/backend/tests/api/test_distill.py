import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from seed import insert_source

from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import DistillationExample, GoldenLabel, LabelKind
from verasig.domain.message import RawTelegramMessage
from verasig.features.accounts.tokens import read_user_id
from verasig.features.feeds import (
    feed_repository,
    message_repository,
)
from verasig.features.rules import distill_routes
from verasig.features.rules import repository as rule_repository
from verasig.features.rules.rule_distiller import AnthropicDistiller
from verasig.features.signals import event_repository
from verasig.foundation.jobs.registry import JobRegistry

SECRET = "s" * 32


class _RecordLogHandler(logging.Handler):
    def __init__(self, level: int = logging.INFO) -> None:
        super().__init__(level)
        self.records: list[logging.LogRecord] = []

    @property
    def text(self) -> str:
        return "\n".join(record.getMessage() for record in self.records)

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@contextmanager
def _capture_logger(name: str, level: int = logging.INFO):
    handler = _RecordLogHandler(level)
    logger = logging.getLogger(name)
    previous_level = logger.level
    previous_disabled = logger.disabled
    logger.setLevel(level)
    logger.disabled = False
    logger.addHandler(handler)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.disabled = previous_disabled


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
    _seed_chat(app, user_id, signal_count=5, noise_count=2)
    responses = [
        json.dumps({"include_patterns": ["zzz"]}),
        json.dumps({"include_patterns": ["alpha"]}),
        json.dumps(
            {
                "parser_rules": [
                    {
                        "patterns": [r"(?P<symbol>BTC)\s+alpha\s+(?P<side>long)"],
                        "field_map": {"symbol": "symbol", "side": "side"},
                        "side_aliases": {"long": "LONG"},
                    }
                ]
            }
        ),
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
    with app.state.session_factory() as session:
        parser_rules = rule_repository.read_parser_rules(session, 7, user_id)

    assert started.status_code == 202
    for stage in (
        "labels_read",
        "filter_distilling",
        "filter_validating",
        "parser_distilling",
        "rules_persisting",
        "rules_complete",
    ):
        assert f'"stage": "{stage}"' in body
    assert '"signalLabels": 5' in body
    assert '"noiseLabels": 2' in body
    assert "event: done" in body
    assert responses == []
    assert len(parser_rules) == 1
    assert parser_rules[0].field_map == {"symbol": "symbol", "side": "side"}
    assert rules.status_code == 200
    assert rules.json()["rules"] == [
        {
            "id": f"{user_id}:7-filter-v1:0",
            "label": "alpha",
            "detail": "alpha",
            "match": 100.0,
        }
    ]


def test_distill_job_logs_successful_progress(client, app):
    token, user_id = _register(client)
    _seed_chat(app, user_id, signal_count=5, noise_count=2)

    class ImmediateDistiller:
        def distill_filter(self, _examples):
            return FilterRule(rule_id="filter", include_patterns=["alpha"])

        def distill_parsers(self, _examples):
            return []

    app.state.distiller_factory = ImmediateDistiller

    with _capture_logger(distill_routes.__name__) as logs:
        client.post("/feeds/7/distill", headers=_auth(token))
        with client.stream(
            "GET", "/feeds/7/distill/progress", headers=_auth(token)
        ) as response:
            body = "".join(response.iter_text())

    assert "event: done" in body
    for stage in (
        "labels_read",
        "filter_distilling",
        "filter_validating",
        "parser_distilling",
        "rules_persisting",
        "rules_complete",
    ):
        assert (
            f"feed_job.progress: operation=distill external_id=7 "
            f"phase={distill_routes.DISTILL_STAGE_BY_KEY[stage]['phase']}"
        ) in logs.text
        assert f"stage={stage}" in logs.text
    assert "step=1" in logs.text
    assert "total_steps=6" in logs.text
    assert "signal_labels=5" in logs.text
    assert "noise_labels=2" in logs.text
    assert "attempt=None" in logs.text


def test_distill_job_emits_error_when_filter_never_validates(client, app):
    token, user_id = _register(client)
    _seed_chat(app, user_id, signal_count=5)
    responses = [json.dumps({"include_patterns": ["zzz"]}) for _ in range(3)]

    def runner(_prompt: str) -> str:
        return responses.pop(0)

    app.state.distiller_factory = lambda: AnthropicDistiller(runner=runner)

    with _capture_logger(distill_routes.__name__, logging.WARNING) as logs:
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
    assert "distill.failed: external_id=7 stage=filter_distilling" in logs.text
    assert "reason=filter distillation failed deterministic validation" in logs.text
    assert any(record.exc_info for record in logs.records)


def test_distill_job_logs_parser_failure_with_exception_details(client, app):
    token, user_id = _register(client)
    _seed_chat(app, user_id, signal_count=5)
    responses = [
        json.dumps({"include_patterns": ["alpha"]}),
        *[
            json.dumps(
                {
                    "parser_rules": [
                        {
                            "patterns": [r"(?P<symbol>BTC)"],
                            "field_map": {"symbol": "symbol"},
                            "side_aliases": {},
                        }
                    ]
                }
            )
            for _ in range(3)
        ],
    ]

    def runner(_prompt: str) -> str:
        return responses.pop(0)

    app.state.distiller_factory = lambda: AnthropicDistiller(runner=runner)

    with _capture_logger(distill_routes.__name__, logging.WARNING) as logs:
        started = client.post("/feeds/7/distill", headers=_auth(token))
        with client.stream(
            "GET", "/feeds/7/distill/progress", headers=_auth(token)
        ) as response:
            body = "".join(response.iter_text())

    assert started.status_code == 202
    assert "event: error" in body
    assert "parser distillation failed deterministic validation" in body
    assert responses == []
    assert "distill.failed: external_id=7 stage=parser_distilling" in logs.text
    assert "reason=parser distillation failed deterministic validation" in logs.text
    assert any(record.exc_info for record in logs.records)


@pytest.mark.asyncio
async def test_distill_progress_is_observable_while_filter_distiller_blocks(
    monkeypatch,
):
    user_id = uuid4()
    registry = JobRegistry()
    filter_finished = False

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_exc_info):
            return None

        def commit(self):
            return None

    class SlowDistiller:
        def distill_filter(self, _examples):
            nonlocal filter_finished
            time.sleep(0.2)
            filter_finished = True
            return FilterRule(rule_id="filter", include_patterns=["alpha"])

        def distill_parsers(self, _examples):
            return []

    monkeypatch.setattr(
        distill_routes,
        "read_distillation_examples",
        lambda *_args: [
            DistillationExample(
                channel_id=7, message_id=1, label=LabelKind.SIGNAL, text="alpha"
            ),
            DistillationExample(
                channel_id=7, message_id=2, label=LabelKind.NOISE, text="noise"
            ),
        ],
    )
    monkeypatch.setattr(distill_routes, "upsert_filter_rule", lambda *_args: None)
    monkeypatch.setattr(distill_routes, "upsert_parser_rules", lambda *_args: None)

    registry.start(
        "job",
        lambda publisher: distill_routes._run_distill(
            publisher,
            user_id,
            7,
            lambda: Session(),
            SlowDistiller,
        ),
    )

    async for _event, payload in registry.stream("job"):
        if payload.get("stage") == "filter_distilling":
            break

    assert filter_finished is False
    await registry.channel("job").task


def test_distill_progress_reports_missing_job_as_404(client, app):
    token, user_id = _register(client)
    _seed_chat(app, user_id, signal_count=5)

    response = client.get("/feeds/7/distill/progress", headers=_auth(token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"
