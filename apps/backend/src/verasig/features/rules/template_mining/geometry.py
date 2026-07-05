"""Verasig - Template Mining: price-geometry validation.

A BUY's stop sits below and targets above the entry; a SELL is the mirror. When
there is no entry we fall back to the stop-vs-targets relationship. Violations
never hard-reject - they lower confidence and raise a warning so the family is
sent to review rather than silently dropped.

Faithful port of ``geometry.js``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .fields import SignalEntry, StructuredFields

VALID_BONUS = 2
VIOLATION_PENALTY = -3

_STOP_LOSS_ON_WRONG_SIDE = "stop_loss_on_wrong_side"
_TAKE_PROFIT_ON_WRONG_SIDE = "take_profit_on_wrong_side"
_STOP_LOSS_NOT_BELOW_TARGETS = "stop_loss_not_below_targets"
_STOP_LOSS_NOT_ABOVE_TARGETS = "stop_loss_not_above_targets"


@dataclass
class ParserIssue:
    """A structured parser issue that explains why a candidate needs review.

    ``field`` keeps the JS domain values (``stopLoss`` / ``takeProfits``).
    """

    code: str
    field: str
    label: str
    message: str
    price: float | None = None


@dataclass
class GeometryResult:
    is_valid: bool
    warnings: list[str] = field(default_factory=list)
    issues: list[ParserIssue] = field(default_factory=list)
    score_adjustment: int = 0


@dataclass
class _Bounds:
    low: float
    high: float


def _resolve_fields(input_) -> StructuredFields:
    if input_ is None:
        return StructuredFields()
    inner = getattr(input_, "fields", None)
    if inner is not None:
        return inner
    return input_


def _entry_bounds(entry: SignalEntry | None) -> _Bounds | None:
    # A range entry is two bounds, not a midpoint.
    if not entry:
        return None
    if entry.type == "range":
        return _Bounds(low=entry.min, high=entry.max)
    if isinstance(entry.price, (int, float)):
        return _Bounds(low=entry.price, high=entry.price)
    return None


def _side_label(direction: str | None) -> str:
    return "LONG" if direction == "BUY" else "SHORT"


def _relation_to_entry(value: float, bounds: _Bounds) -> str:
    if value < bounds.low:
        return "below"
    if value > bounds.high:
        return "above"
    if bounds.low == bounds.high:
        return "equal"
    return "inside"


def _opposite_side(side: str) -> str:
    return "above" if side == "below" else "below"


def _entry_relation_label(
    subject: str, direction: str | None, relation: str, expected_side: str
) -> str:
    if relation == "equal":
        return f"{subject} equals entry"
    if relation == "inside":
        return f"{subject} inside entry range for {_side_label(direction)}"
    return (
        f"{subject} {_opposite_side(expected_side)} entry for {_side_label(direction)}"
    )


def _side_requirement_message(
    label: str, subject: str, expected_side: str, direction: str | None, reference: str
) -> str:
    return (
        f"{label}. {subject} should sit {expected_side} {reference} "
        f"for a {_side_label(direction)}."
    )


def _entry_issue(
    code: str,
    field_name: str,
    subject: str,
    direction: str | None,
    bounds: _Bounds,
    value: float,
    expected_side: str,
) -> ParserIssue:
    label = _entry_relation_label(
        subject, direction, _relation_to_entry(value, bounds), expected_side
    )
    return ParserIssue(
        code=code,
        field=field_name,
        label=label,
        message=_side_requirement_message(
            label, subject, expected_side, direction, "entry"
        ),
        price=value,
    )


def _stop_loss_entry_issue(
    direction: str | None, bounds: _Bounds, stop_loss: float
) -> ParserIssue:
    expected = "below" if direction == "BUY" else "above"
    return _entry_issue(
        _STOP_LOSS_ON_WRONG_SIDE,
        "stopLoss",
        "Stop loss",
        direction,
        bounds,
        stop_loss,
        expected,
    )


def _take_profit_entry_issue(
    direction: str | None, bounds: _Bounds, target: float
) -> ParserIssue:
    expected = "above" if direction == "BUY" else "below"
    return _entry_issue(
        _TAKE_PROFIT_ON_WRONG_SIDE,
        "takeProfits",
        "Take profit",
        direction,
        bounds,
        target,
        expected,
    )


def _stop_loss_target_issue(direction: str | None, stop_loss: float) -> ParserIssue:
    is_buy = direction == "BUY"
    label = (
        "Stop loss not below take profits for LONG"
        if is_buy
        else "Stop loss not above take profits for SHORT"
    )
    expected = "below" if is_buy else "above"
    return ParserIssue(
        code=_STOP_LOSS_NOT_BELOW_TARGETS if is_buy else _STOP_LOSS_NOT_ABOVE_TARGETS,
        field="stopLoss",
        label=label,
        message=_side_requirement_message(
            label, "Stop loss", expected, direction, "take profits"
        ),
        price=stop_loss,
    )


def _check_against_entry(
    direction: str | None,
    bounds: _Bounds,
    stop_loss: float | None,
    take_profits: list[float],
    issues: list[ParserIssue],
) -> None:
    is_buy = direction == "BUY"
    if stop_loss is not None:
        stop_ok = stop_loss < bounds.low if is_buy else stop_loss > bounds.high
        if not stop_ok:
            issues.append(_stop_loss_entry_issue(direction, bounds, stop_loss))
    for target in take_profits:
        target_ok = target > bounds.high if is_buy else target < bounds.low
        if not target_ok:
            issues.append(_take_profit_entry_issue(direction, bounds, target))


def _check_stop_vs_targets(
    direction: str | None,
    stop_loss: float,
    take_profits: list[float],
    issues: list[ParserIssue],
) -> None:
    is_buy = direction == "BUY"
    boundary = min(take_profits) if is_buy else max(take_profits)
    violated = stop_loss >= boundary if is_buy else stop_loss <= boundary
    if violated:
        issues.append(_stop_loss_target_issue(direction, stop_loss))


def validate_price_geometry(input_) -> GeometryResult:
    fields = _resolve_fields(input_)
    direction = fields.direction
    stop_loss = fields.stop_loss if fields.stop_loss is not None else None
    take_profits = fields.take_profits if isinstance(fields.take_profits, list) else []
    bounds = _entry_bounds(fields.entry)
    issues: list[ParserIssue] = []

    can_check_against_entry = bounds is not None and (
        stop_loss is not None or len(take_profits) > 0
    )
    can_check_stop_vs_targets = (
        bounds is None and stop_loss is not None and len(take_profits) > 0
    )

    if not direction or (not can_check_against_entry and not can_check_stop_vs_targets):
        return GeometryResult(is_valid=True, warnings=[], issues=[], score_adjustment=0)

    if can_check_against_entry:
        _check_against_entry(direction, bounds, stop_loss, take_profits, issues)
    else:
        _check_stop_vs_targets(direction, stop_loss, take_profits, issues)

    is_valid = len(issues) == 0
    return GeometryResult(
        is_valid=is_valid,
        warnings=[issue.message for issue in issues],
        issues=issues,
        score_adjustment=VALID_BONUS if is_valid else VIOLATION_PENALTY,
    )
