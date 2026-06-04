"""In-memory TelegramSource fake for offline backfill tests.

Simulates Telegram's history: holds a fixed message set, yields it
oldest->newest in batches, can interrupt mid-stream (resume tests), and
records every `after_message_id` it was asked for (refetch assertions).
"""

from collections.abc import AsyncIterator, Callable

from verasig.domain.channel import TelegramChannel
from verasig.domain.label import GoldenLabel
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import TradeIntent
from verasig.foundation.exchange import normalize_base_symbol
from verasig.services.distillation.rule_distiller import parse_distiller_output


class FakeStreamInterrupted(RuntimeError):
    """Raised by FakeSource to simulate a mid-backfill crash."""


class FakeSource:
    def __init__(
        self,
        channel: TelegramChannel,
        messages: list[RawTelegramMessage],
        *,
        fail_after_batch: int | None = None,
        before_batch: Callable[[int, int], None] | None = None,
    ) -> None:
        self.channel = channel
        self.messages = sorted(messages, key=lambda message: message.message_id)
        self.fail_after_batch = fail_after_batch
        self.before_batch = before_batch
        self.requested_afters: list[int | None] = []
        self.yielded_ids: list[int] = []

    async def resolve_channel(self, reference: str | int) -> TelegramChannel:
        return self.channel

    async def backfill_batches(
        self, channel_id: int, after_message_id: int | None, batch_size: int
    ) -> AsyncIterator[list[RawTelegramMessage]]:
        self.requested_afters.append(after_message_id)
        after = after_message_id or 0
        pending = [m for m in self.messages if m.message_id > after]
        yielded = 0
        for index, start in enumerate(range(0, len(pending), batch_size)):
            if self.fail_after_batch is not None and index == self.fail_after_batch:
                raise FakeStreamInterrupted
            if self.before_batch is not None:
                self.before_batch(index, yielded)
            batch = pending[start : start + batch_size]
            self.yielded_ids.extend(message.message_id for message in batch)
            yielded += len(batch)
            yield batch

    async def live_events(self, channel_ids: list[int]):
        yield None  # unused in Slice 2


class FakeExchange:
    """In-memory Exchange for offline seed-filter tests (injected symbol set)."""

    def __init__(self, symbols: set[str]) -> None:
        self._symbols = {normalize_base_symbol(symbol) for symbol in symbols}

    def base_symbols(self) -> set[str]:
        return set(self._symbols)

    def is_listed(self, token: str) -> bool:
        return normalize_base_symbol(token) in self._symbols


class FakeDistiller:
    """Offline RuleDistiller: serves rules parsed from canned LLM stdout."""

    def __init__(self, stdout: str, version: int = 1) -> None:
        self._stdout = stdout
        self._version = version

    def _parse(self, labels: list[GoldenLabel]):
        return parse_distiller_output(
            self._stdout,
            channel_id=labels[0].channel_id,
            label_ids=[label.id for label in labels],
            version=self._version,
        )

    def distill_filter(self, labels: list[GoldenLabel]):
        return self._parse(labels)[0]

    def distill_parsers(self, labels: list[GoldenLabel]):
        return self._parse(labels)[1]


class FakeExtractor:
    """Offline LlmExtractor: returns a canned TradeIntent (or None), counts calls."""

    def __init__(self, returns: TradeIntent | None = None) -> None:
        self._returns = returns
        self.calls = 0

    def extract(self, candidate_text: str) -> TradeIntent | None:
        self.calls += 1
        return self._returns
