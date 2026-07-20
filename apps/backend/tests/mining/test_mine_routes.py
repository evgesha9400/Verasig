"""Unit tests for the mine job runner (`_run_mine`).

The SSE transport (`sse_stream`) and job registry are shared, already-tested
infrastructure; here we pin the mine-specific behavior: staged progress in order,
a JSON-serializable `{groups: [...]}` terminal payload, and graceful empty input.
"""

import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID

from verasig.features.mining import mine_routes
from verasig.features.mining.mining_review import MiningReview, MiningReviewInput
from verasig.features.mining.template_mining import ChatMessage


class _FakePublisher:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def progress(self, data: dict) -> None:
        self.events.append(data)


class _FakeSessionFactory:
    def __call__(self) -> "_FakeSessionFactory":
        return self

    def __enter__(self) -> "_FakeSessionFactory":
        return self

    def __exit__(self, *args) -> bool:
        return False

    def commit(self) -> None:
        pass


def _raw(message_id: int, text: str) -> ChatMessage:
    return ChatMessage(id=str(message_id), text=text)


def _run(messages, monkeypatch):
    review_input = MiningReviewInput(
        messages=messages,
        overlay={},
        capture_generation=0,
        input_revision="a" * 64,
    )
    monkeypatch.setattr(mine_routes, "read_input", lambda *_: review_input)
    saved: dict = {}

    def create(_session, user_id, channel_id, received_input, groups):
        review = MiningReview(
            review_id=UUID("10000000-0000-0000-0000-000000000001"),
            user_id=user_id,
            external_id=channel_id,
            input_revision=received_input.input_revision,
            groups=groups,
            messages=received_input.messages,
            overlay=received_input.overlay,
            created_at=datetime(2026, 7, 21, tzinfo=UTC),
        )
        saved.update(user_id=user_id, channel_id=channel_id, review=review)
        return review

    monkeypatch.setattr(mine_routes, "create_review", create)
    publisher = _FakePublisher()
    result = asyncio.run(
        mine_routes._run_mine(publisher, "user-1", 42, _FakeSessionFactory())
    )
    return publisher, result, saved


def test_run_mine_publishes_ordered_stages_and_returns_groups(monkeypatch):
    messages = [
        _raw(1, "XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355"),
        _raw(2, "XAUUSD BUY NOW\nSL 2300\nTP 2330\nTP 2350"),
        _raw(3, "gm team"),
    ]
    publisher, result, saved = _run(messages, monkeypatch)

    assert [event["stage"] for event in publisher.events] == [
        "loading",
        "extracting",
        "grouping",
        "complete",
    ]
    assert saved["user_id"] == "user-1"
    assert saved["channel_id"] == 42
    assert saved["review"].review_id == UUID("10000000-0000-0000-0000-000000000001")
    assert result["reviewId"] == "10000000-0000-0000-0000-000000000001"
    assert result["inputRevision"] == "a" * 64
    assert isinstance(result["groups"], list)
    assert len(result["groups"]) >= 1
    group = result["groups"][0]
    # Wire shape is the browser's camelCase JS shape…
    assert {"templateKey", "count", "suggestedAction", "examples"} <= set(group)
    assert "normalizedTemplate" in group and "confidenceAvg" in group
    # …except intentDistribution's inner keys, which the UI reads verbatim.
    assert set(group["intentDistribution"]) >= {"new_signal", "update"}
    # Raw messages ride along for the browser's verify audit preview.
    assert [m["id"] for m in result["messages"]] == ["1", "2", "3"]
    # Must be JSON-serializable — it is sent verbatim as the SSE `done` payload.
    json.dumps(result)


def test_run_mine_handles_empty_history(monkeypatch):
    publisher, result, saved = _run([], monkeypatch)
    assert result["groups"] == []
    assert result["messages"] == []
    assert saved["review"].messages == []
    assert [event["stage"] for event in publisher.events] == [
        "loading",
        "extracting",
        "grouping",
        "complete",
    ]
