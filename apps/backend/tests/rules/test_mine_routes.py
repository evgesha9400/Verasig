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

    def __enter__(self) -> object:
        return object()

    def __exit__(self, *args) -> bool:
        return False


def _raw(message_id: int, text: str) -> SimpleNamespace:
    return SimpleNamespace(message_id=message_id, text=text, posted_at=None)


def _run(messages, monkeypatch):
    monkeypatch.setattr(
        mine_routes.message_repository, "read_messages", lambda *_: messages
    )
    monkeypatch.setattr(mine_routes, "read_overlay", lambda *_: {})
    publisher = _FakePublisher()
    result = asyncio.run(
        mine_routes._run_mine(publisher, "user-1", 42, _FakeSessionFactory())
    )
    return publisher, result


def test_run_mine_publishes_ordered_stages_and_returns_groups(monkeypatch):
    messages = [
        _raw(1, "XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355"),
        _raw(2, "XAUUSD BUY NOW\nSL 2300\nTP 2330\nTP 2350"),
        _raw(3, "gm team"),
    ]
    publisher, result = _run(messages, monkeypatch)

    assert [event["stage"] for event in publisher.events] == [
        "loading",
        "extracting",
        "grouping",
        "complete",
    ]
    assert isinstance(result["groups"], list)
    assert len(result["groups"]) >= 1
    group = result["groups"][0]
    assert {"template_key", "count", "suggested_action", "examples"} <= set(group)
    # Raw messages ride along for the browser's verify audit preview.
    assert [m["id"] for m in result["messages"]] == ["1", "2", "3"]
    # Must be JSON-serializable — it is sent verbatim as the SSE `done` payload.
    json.dumps(result)


def test_run_mine_handles_empty_history(monkeypatch):
    publisher, result = _run([], monkeypatch)
    assert result == {"groups": [], "messages": []}
    assert [event["stage"] for event in publisher.events] == [
        "loading",
        "extracting",
        "grouping",
        "complete",
    ]
