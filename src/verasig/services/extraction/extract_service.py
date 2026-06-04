"""One-of extraction outcome (data-contracts.md §3 invariant; plan Slice 4).

`ExtractService` applies the ordered `ParserRule`s to a `RawSignalEvent` and
yields **exactly one** of `{ExtractedSignal, UnrecognizedSignal}`. The first rule
that produces a signal wins; a deterministic miss yields an `UnrecognizedSignal`
(`reason="no_match"`). The `fallback` (`LlmExtractor`) seam is accepted now but
wired in Slice 5, where a fallback success also emits one `ParserDriftWarning`.
"""

from dataclasses import dataclass, field

from verasig.domain.event import RawSignalEvent
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import (
    ExtractedSignal,
    ExtractionMethod,
    TradeIntent,
    UnrecognizedSignal,
)
from verasig.services.extraction.deterministic_parser import parse


@dataclass
class ExtractOutcome:
    signal: ExtractedSignal | None = None
    unrecognized: UnrecognizedSignal | None = None
    drift_warnings: list = field(default_factory=list)


def _link(
    intent: TradeIntent,
    event: RawSignalEvent,
    method: ExtractionMethod,
    rule_id: str | None,
) -> ExtractedSignal:
    return ExtractedSignal(
        **intent.model_dump(),
        event_id=event.id,
        channel_id=event.channel_id,
        extraction_method=method,
        rule_id=rule_id,
    )


class ExtractService:
    def __init__(self, rules: list[ParserRule], fallback=None) -> None:
        self._rules = rules
        self._fallback = fallback  # LlmExtractor seam; wired in Slice 5

    def extract(self, event: RawSignalEvent) -> ExtractOutcome:
        for rule in self._rules:
            intent = parse(rule, event.candidate_text)
            if intent is not None:
                signal = _link(
                    intent, event, ExtractionMethod.DETERMINISTIC, rule.rule_id
                )
                return ExtractOutcome(signal=signal)
        return ExtractOutcome(
            unrecognized=UnrecognizedSignal(
                event_id=event.id,
                reason="no_match",
                attempted_methods=[ExtractionMethod.DETERMINISTIC],
            )
        )
