"""LLM fallback extraction (data-contracts.md §3; ADR 0006).

When the deterministic parser misses, an `LlmExtractor` attempts the same
`text -> TradeIntent | None` contract via a one-task LLM call. The model emits
EXACTLY a `TradeIntent` JSON (no self-grading, no lifecycle classification);
`parse_extractor_output` tolerantly extracts it and returns None on absent/invalid
JSON or a missing symbol+side — a fallback miss, not a crash (contrast the
distiller, which raises). `ClaudeCliExtractor` mirrors `ClaudeCliDistiller`: an
injectable subprocess runner so no test touches the real CLI; pass
`command="codex"` to drive Codex instead.
"""

import json
import subprocess
from collections.abc import Callable
from typing import Protocol, runtime_checkable

from pydantic import ValidationError

from verasig.domain.signal import TradeIntent
from verasig.services.json_extract import find_json_object

_TRADE_INTENT_KEYS = {
    "symbol",
    "side",
    "entry_type",
    "entry_low",
    "entry_high",
    "stop_loss",
    "take_profits",
    "leverage",
    "confidence",
}


@runtime_checkable
class LlmExtractor(Protocol):
    def extract(self, candidate_text: str) -> TradeIntent | None: ...


def _content(payload: dict) -> dict:
    content = {
        key: value for key, value in payload.items() if key in _TRADE_INTENT_KEYS
    }
    if isinstance(content.get("side"), str):
        content["side"] = content["side"].upper()  # canonical LONG/SHORT, defensively
    return content


def parse_extractor_output(stdout: str) -> TradeIntent | None:
    raw = find_json_object(stdout)
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    try:
        return TradeIntent(**_content(payload))
    except ValidationError:
        return None


def _extraction_prompt(candidate_text: str) -> str:
    return (
        "Extract the single trade from the message below. Return ONLY a JSON object "
        '{"symbol": "...", "side": "LONG"|"SHORT", "entry_type": '
        '"MARKET"|"LIMIT_SINGLE"|"LIMIT_RANGE", "entry_low": null, "entry_high": null, '
        '"stop_loss": null, "take_profits": [], "leverage": null, "confidence": null} '
        "using null for unknown fields and no commentary. If the message has no "
        "tradable signal, reply 'No tradable signal.' with no JSON.\n\n"
        f"Message:\n{candidate_text}"
    )


def _subprocess_runner(command: str) -> Callable[[str], str]:
    def run(prompt: str) -> str:
        completed = subprocess.run(
            [command],
            input=prompt,
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout

    return run


class ClaudeCliExtractor:
    """Real LLM-CLI fallback extractor (manual acceptance / go-ahead-gated).

    The subprocess runner is injectable so tests drive it with canned stdout and
    never touch the real CLI. Pass `command="codex"` to drive Codex instead.
    """

    def __init__(
        self,
        command: str = "claude",
        runner: Callable[[str], str] | None = None,
    ) -> None:
        self._runner = runner or _subprocess_runner(command)

    def extract(self, candidate_text: str) -> TradeIntent | None:
        stdout = self._runner(_extraction_prompt(candidate_text))
        return parse_extractor_output(stdout)
