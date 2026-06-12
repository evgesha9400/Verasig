"""Loaders for the committed golden corpus (tests/fixtures/messages|labels).

`load_labels` enriches each positive label's `expected` with placeholder linkage
(`event_id`, `channel_id`) so it validates as an `ExtractedSignal` — the operator
states trade-shape fields only; the harness compares symbol+side, never linkage.
"""

import json
from pathlib import Path
from uuid import uuid4

from verasig.domain.label import GoldenLabel
from verasig.domain.message import RawTelegramMessage


def _lines(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_messages(path: Path) -> list[RawTelegramMessage]:
    return [RawTelegramMessage.model_validate(record) for record in _lines(path)]


def _new_uuid_text() -> str:
    return uuid4().urn.removeprefix("urn:uuid:")


def load_labels(path: Path, channel_id: int) -> list[GoldenLabel]:
    labels = []
    for record in _lines(path):
        expected = record.get("expected")
        if expected is not None:
            record = {
                **record,
                "expected": {
                    **expected,
                    "event_id": _new_uuid_text(),
                    "channel_id": channel_id,
                },
            }
        labels.append(GoldenLabel.model_validate(record))
    return labels
