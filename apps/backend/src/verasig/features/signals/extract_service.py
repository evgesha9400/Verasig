"""One-of extraction outcome (data-contracts.md §3 invariant; ADR 0006).

`ExtractService` applies the ordered `ParserRule`s to a `RawSignalEvent` and
yields **exactly one** of `{ExtractedSignal, UnrecognizedSignal}` plus any drift.
The first rule that produces a `TradeIntent` wins (method=DETERMINISTIC). On a
deterministic miss the optional `LlmExtractor` fallback runs: a hit is linked
(method=LLM_FALLBACK) and emits exactly one `ParserDriftWarning`; a miss yields
`UnrecognizedSignal(reason="fallback_failed")`. With no fallback, a miss yields
`reason="no_match"`. `_link` is the single linkage site for both paths.
"""

from verasig.domain.drift import ParserDriftWarning
from verasig.domain.event import RawSignalEvent
from verasig.domain.extraction_outcome import ExtractOutcome
from verasig.domain.llm_ports import LlmExtractor
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import (
    ExtractedSignal,
    ExtractionMethod,
    TradeIntent,
    UnrecognizedSignal,
)
from verasig.features.signals.deterministic_parser import parse


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
    def __init__(
        self, rules: list[ParserRule], fallback: LlmExtractor | None = None
    ) -> None:
        self._rules = rules
        self._fallback = fallback

    def extract(self, event: RawSignalEvent) -> ExtractOutcome:
        deterministic = self._deterministic_outcome(event)
        if deterministic is not None:
            return deterministic
        if self._fallback is not None:
            return self._fallback_outcome(event)
        return ExtractOutcome(unrecognized=self._unrecognized(event, "no_match"))

    def _deterministic_outcome(self, event: RawSignalEvent) -> ExtractOutcome | None:
        for rule in self._rules:
            intent = parse(rule, event.candidate_text)
            if intent is not None:
                signal = _link(
                    intent, event, ExtractionMethod.DETERMINISTIC, rule.rule_id
                )
                return ExtractOutcome(signal=signal)
        return None

    def _fallback_outcome(self, event: RawSignalEvent) -> ExtractOutcome:
        intent = self._fallback.extract(event.candidate_text)
        if intent is None:
            return ExtractOutcome(
                unrecognized=self._unrecognized(event, "fallback_failed")
            )
        signal = _link(intent, event, ExtractionMethod.LLM_FALLBACK, rule_id=None)
        drift = ParserDriftWarning(
            event_id=event.id,
            channel_id=event.channel_id,
            fallback_signal_id=signal.id,
        )
        return ExtractOutcome(signal=signal, drift_warnings=[drift])

    @staticmethod
    def _unrecognized(event: RawSignalEvent, reason: str) -> UnrecognizedSignal:
        attempted = [ExtractionMethod.DETERMINISTIC]
        if reason == "fallback_failed":
            attempted.append(ExtractionMethod.LLM_FALLBACK)
        return UnrecognizedSignal(
            event_id=event.id, reason=reason, attempted_methods=attempted
        )
