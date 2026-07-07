"""Unit tests for the mine job runner (`_run_mine`).

The SSE transport (`sse_stream`) and job registry are shared, already-tested
infrastructure; here we pin the mine-specific behavior: staged progress in order,
a JSON-serializable `{groups: [...]}` terminal payload, and graceful empty input.
"""

import asyncio
import json
from types import SimpleNamespace

from verasig.features.rules import mine_routes


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


def _raw(message_id: int, text: str) -> SimpleNamespace:
    return SimpleNamespace(message_id=message_id, text=text, posted_at=None)


def _run(messages, monkeypatch):
    monkeypatch.setattr(
        mine_routes.message_repository, "read_messages", lambda *_: messages
    )
    monkeypatch.setattr(mine_routes, "read_overlay", lambda *_: {})
    saved: dict = {}
    monkeypatch.setattr(
        mine_routes,
        "upsert_mine_result",
        lambda session, user_id, channel_id, payload: saved.update(
            user_id=user_id, channel_id=channel_id, payload=payload
        ),
    )
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
    # The terminal payload is cached per feed so reopening skips the re-scan.
    assert saved == {"user_id": "user-1", "channel_id": 42, "payload": result}
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
    assert result == {"groups": [], "messages": []}
    assert saved["payload"] == {"groups": [], "messages": []}
    assert [event["stage"] for event in publisher.events] == [
        "loading",
        "extracting",
        "grouping",
        "complete",
    ]
