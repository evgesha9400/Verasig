"""Pure LLM adapter seams."""

from typing import Protocol, runtime_checkable

from verasig.domain.signal import TradeIntent


@runtime_checkable
class LlmExtractor(Protocol):
    def extract(self, candidate_text: str) -> TradeIntent | None: ...
