"""Pure LLM adapter seams."""

from typing import Protocol, runtime_checkable

from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import GoldenLabel
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import TradeIntent


@runtime_checkable
class LlmExtractor(Protocol):
    def extract(self, candidate_text: str) -> TradeIntent | None: ...


@runtime_checkable
class RuleDistiller(Protocol):
    def distill_filter(self, labels: list[GoldenLabel]) -> FilterRule: ...
    def distill_parsers(self, labels: list[GoldenLabel]) -> list[ParserRule]: ...
