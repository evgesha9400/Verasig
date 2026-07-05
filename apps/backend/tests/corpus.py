"""Loader for the committed golden corpus (tests/fixtures/messages)."""

import json
from pathlib import Path

from verasig.domain.message import RawTelegramMessage


def _lines(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_messages(path: Path) -> list[RawTelegramMessage]:
    return [RawTelegramMessage.model_validate(record) for record in _lines(path)]
