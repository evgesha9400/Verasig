"""Pure lifecycle patch classifier (data-contracts.md §5; ADR 0007).

A reply in a signal's `reply_to` chain rarely parses as a `TradeIntent` — it
patches the live position: move the stop (incl. to breakeven), set the
take-profits, average in, reduce, or close it. `classify_patch` reads such a
reply as a `LifecyclePatch` of effective-state deltas that the fold applies.
Table-driven, EN + RU, offline. An inert reply yields a non-actionable patch
so the fold emits no phantom lifecycle step.
"""

import re
from dataclasses import dataclass
from decimal import Decimal

from verasig.services.numbers import to_decimal

_HALF = Decimal("0.5")

# Bare "BE" is matched case-sensitively to dodge the English verb "be"; the
# unambiguous "b/e" and spelled-out forms (+ cyrillic) are case-insensitive.
_BREAKEVEN_ABBREV = re.compile(r"\bBE\b")
_BREAKEVEN_SPELLED = re.compile(r"b/e|break[\s-]?even|безуб", re.IGNORECASE)

_NUMBER = re.compile(r"\d[\d.,]*[kmкм]?", re.IGNORECASE)
_STOP = re.compile(
    r"(?:sl|stop\s*loss|stop|стоп\w*)\b\D{0,6}?(\d[\d.,]*[kmкм]?)", re.IGNORECASE
)
_TAKE_PROFITS = re.compile(
    r"(?:tps?|targets?|тейк\w*)\b\s*[:=@]?\s*((?:\d[\d.,]*[kmкм]?[\s,]*)+)",
    re.IGNORECASE,
)

_ADD = re.compile(
    r"\badd\b|averag|\bavg\b|\bdca\b|scale\s*in|усред|добав|докуп", re.IGNORECASE
)
_REDUCE = re.compile(r"reduc|trim|partial|сократ|частичн", re.IGNORECASE)
_CLOSE = re.compile(
    r"\bclos(?:e|ed|ing)|all\s*out|\bexit\b|stopped\s*out"
    r"|(?:sl|tp|stop|take\s*profit)\s*hit|закры|стоп\s*выбит",
    re.IGNORECASE,
)

_FACTOR = re.compile(r"(\d[\d.,]*)\s*(%|[xх])", re.IGNORECASE)
_HALF_WORD = re.compile(r"\bhalf\b|½|наполовину", re.IGNORECASE)
_PRICE = re.compile(r"\b(\d[\d.,]*[kmкм]?)\b(?!\s*[%xхХ])", re.IGNORECASE)


@dataclass
class LifecyclePatch:
    set_stop_loss: Decimal | None = None
    stop_to_breakeven: bool = False
    set_take_profits: list[Decimal] | None = None
    add_multiplier: Decimal | None = None  # average-in size delta
    add_price: Decimal | None = None  # None + add_multiplier ⇒ market-at-time
    reduce_fraction: Decimal | None = None  # 0..1 of current size
    close: bool = False

    @property
    def is_actionable(self) -> bool:
        return any(
            (
                self.set_stop_loss is not None,
                self.stop_to_breakeven,
                self.set_take_profits is not None,
                self.add_multiplier is not None,
                self.reduce_fraction is not None,
                self.close,
            )
        )


def _mentions_breakeven(text: str) -> bool:
    return bool(_BREAKEVEN_ABBREV.search(text) or _BREAKEVEN_SPELLED.search(text))


def _stated_stop_loss(text: str) -> Decimal | None:
    match = _STOP.search(text)
    return to_decimal(match.group(1)) if match else None


def _stated_take_profits(text: str) -> list[Decimal] | None:
    match = _TAKE_PROFITS.search(text)
    if match is None:
        return None
    prices = [to_decimal(token) for token in _NUMBER.findall(match.group(1))]
    found = [price for price in prices if price is not None]
    return found or None


def _stated_factor(text: str) -> Decimal | None:
    match = _FACTOR.search(text)
    if match is not None:
        value = to_decimal(match.group(1))
        if value is None:
            return None
        return value / 100 if match.group(2) == "%" else value
    return _HALF if _HALF_WORD.search(text) else None


def _stated_price(text: str) -> Decimal | None:
    match = _PRICE.search(text)
    return to_decimal(match.group(1)) if match else None


def _classify_stop(text: str, patch: LifecyclePatch) -> None:
    if _mentions_breakeven(text):
        patch.stop_to_breakeven = True
        return
    patch.set_stop_loss = _stated_stop_loss(text)


def _classify_take_profits(text: str, patch: LifecyclePatch) -> None:
    patch.set_take_profits = _stated_take_profits(text)


def _close_or_partial(patch: LifecyclePatch, factor: Decimal | None) -> None:
    if factor is None:
        patch.close = True
    else:
        patch.reduce_fraction = factor  # "close half" / "close 25%"


def _classify_size(text: str, patch: LifecyclePatch) -> None:
    factor = _stated_factor(text)
    if _ADD.search(text):
        patch.add_multiplier = factor or Decimal(1)
        patch.add_price = _stated_price(text)
        return
    if _REDUCE.search(text):
        patch.reduce_fraction = factor or _HALF
        return
    if _CLOSE.search(text):
        _close_or_partial(patch, factor)


def classify_patch(text: str) -> LifecyclePatch:
    """Recognize an in-thread reply as a position patch (SL/BE/TP/add/reduce/close)."""
    patch = LifecyclePatch()
    _classify_stop(text, patch)
    _classify_take_profits(text, patch)
    _classify_size(text, patch)
    return patch
