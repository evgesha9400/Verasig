from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from verasig.domain.account import Plan
from verasig.domain.label import LabelKind
from verasig.domain.lifecycle import FoldedSignal, FoldStep
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import Side, SignalEventType
from verasig.services.lifecycle.fold import fold
from verasig.services.lifecycle.patch import LifecyclePatch, classify_patch
from verasig.services.projection.dates import format_short, format_time
from verasig.storage import (
    backtest_repository,
    lifecycle_link_repository,
    user_channel_repository,
)
from verasig.storage import (
    repositories as repo,
)

OBSERVER_SIGNAL_LIMIT = 200


def present_signals(
    session: Session,
    user_id: UUID,
    feed_id: str | None = None,
    status: str | None = None,
    plan: Plan = Plan.DESK,
) -> dict:
    signals, orphan_mods = _project_user_signals(session, user_id, feed_id)
    if status is not None:
        signals = [signal for signal in signals if signal["status"] == status]
    limit_reached = plan is Plan.OBSERVER and len(signals) > OBSERVER_SIGNAL_LIMIT
    if limit_reached:
        signals = signals[:OBSERVER_SIGNAL_LIMIT]
    return {
        "signals": signals,
        "orphanMods": orphan_mods,
        "limitReached": limit_reached,
    }


def present_signal(session: Session, user_id: UUID, signal_id: UUID) -> dict | None:
    result = present_signals(session, user_id, plan=Plan.DESK)
    return next(
        (signal for signal in result["signals"] if signal["id"] == str(signal_id)),
        None,
    )


def link_modifier(
    session: Session, user_id: UUID, signal_id: UUID, mod_id: int
) -> dict | None:
    signal = present_signal(session, user_id, signal_id)
    if signal is None:
        return None
    lifecycle_link_repository.insert_link(
        session,
        user_id,
        int(signal["feedId"]),
        mod_id,
        signal_id,
        datetime.now(tz=UTC),
    )
    session.flush()
    return present_signal(session, user_id, signal_id)


def _project_user_signals(
    session: Session, user_id: UUID, feed_id: str | None
) -> tuple[list[dict], list[dict]]:
    subscriptions = user_channel_repository.read_subscriptions(session, user_id)
    channel_ids = [subscription.channel_id for subscription in subscriptions]
    if feed_id is not None:
        channel_ids = [
            channel_id for channel_id in channel_ids if str(channel_id) == feed_id
        ]
    latest_results = backtest_repository.read_latest_results(session, user_id)
    signals: list[dict] = []
    orphan_mods: list[dict] = []
    for channel_id in channel_ids:
        projected, orphans = _project_channel(
            session, user_id, channel_id, latest_results.get(channel_id)
        )
        signals.extend(projected)
        orphan_mods.extend(orphans)
    return signals, orphan_mods


def _project_channel(
    session: Session, user_id: UUID, channel_id: int, result
) -> tuple[list[dict], list[dict]]:
    messages = repo.read_messages(session, channel_id)
    events = repo.read_signal_events(session, channel_id)
    signals = repo.read_extracted_signals(session, channel_id, user_id)
    manual_links = {
        link.message_id: link.root_signal_id
        for link in lifecycle_link_repository.read_links(session, user_id, channel_id)
    }
    folded = fold(signals, events, messages, manual_links=manual_links)
    message_by_id = {message.message_id: message for message in messages}
    event_message_ids = {event.id: event.message_id for event in events}
    signal_message_ids = {
        signal.id: event_message_ids[signal.event_id]
        for signal in signals
        if signal.event_id in event_message_ids
    }
    outcome_by_signal_id = _outcomes_by_signal_id(result)
    deleted_message_ids = _deleted_message_ids(session, channel_id)
    rows = [
        _signal_row(
            item,
            message_by_id,
            signal_message_ids,
            outcome_by_signal_id.get(str(item.root_signal_id)),
            deleted_message_ids,
            set(manual_links),
        )
        for item in folded
    ]
    used_message_ids = {
        step.source_message_id for item in folded for step in item.timeline
    }
    return rows, _orphan_mods(
        session, user_id, channel_id, messages, rows, used_message_ids
    )


def _signal_row(
    folded: FoldedSignal,
    messages: dict[int, RawTelegramMessage],
    signal_message_ids: dict[UUID, int],
    outcome: dict | None,
    deleted_message_ids: set[int],
    manual_message_ids: set[int],
) -> dict:
    first = folded.timeline[0]
    message = messages[first.source_message_id]
    return {
        "id": str(folded.root_signal_id),
        "feedId": str(message.channel_id),
        "side": folded.side.value,
        "symbol": folded.symbol,
        **_outcome_fields(outcome),
        "date": format_short(first.at),
        "time": format_time(first.at),
        "entry": _decimal_text(first.effective_entry),
        "stop": _decimal_text(first.effective_stop_loss),
        "tp": [_decimal_text(value) for value in first.effective_take_profits],
        "deleted": signal_message_ids.get(first.source_signal_id)
        in deleted_message_ids,
        "cancelled": folded.closed_at is not None,
        "mods": _mods(folded, messages, manual_message_ids),
        "effective": _effective(folded),
    }


def _mods(
    folded: FoldedSignal,
    messages: dict[int, RawTelegramMessage],
    manual_message_ids: set[int],
) -> list[dict]:
    return [
        _mod_row(folded, step, messages[step.source_message_id], manual_message_ids)
        for step in folded.timeline[1:]
    ]


def _mod_row(
    folded: FoldedSignal,
    step: FoldStep,
    message: RawTelegramMessage,
    manual_message_ids: set[int],
) -> dict:
    patch = classify_patch(message.text or "")
    return {
        "id": str(message.message_id),
        "kind": _mod_kind(folded.side, step, patch),
        "date": format_short(step.at),
        "time": format_time(step.at),
        "via": "inferred" if message.message_id in manual_message_ids else "reply",
        "text": message.text,
    }


def _mod_kind(side: Side, step: FoldStep, patch: LifecyclePatch) -> str:
    if patch.close:
        return "close"
    if patch.reduce_fraction is not None:
        return "partial"
    if patch.add_multiplier is not None:
        return _average_kind(side, step)
    return "move_stop"


def _average_kind(side: Side, step: FoldStep) -> str:
    if step.leg_price is None or step.effective_entry is None:
        return "avg_down"
    if side is Side.LONG:
        return "avg_down" if step.leg_price < step.effective_entry else "avg_up"
    return "avg_up" if step.leg_price < step.effective_entry else "avg_down"


def _effective(folded: FoldedSignal) -> dict:
    final = folded.timeline[-1]
    effective = {
        "entry": _decimal_text(final.effective_entry),
        "stop": _decimal_text(final.effective_stop_loss),
        "tp": [_decimal_text(value) for value in final.effective_take_profits],
    }
    if final.event_type is SignalEventType.CLOSE:
        effective["closedBy"] = "author"
    return effective


def _outcome_fields(outcome: dict | None) -> dict:
    if outcome is None:
        return {"status": "untested", "outcome": None, "pnl": None}
    if outcome.get("kind") == "UNFILLED":
        return {"status": "skipped", "outcome": None, "pnl": None}
    pnl = outcome.get("pctReturn")
    return {
        "status": "tested",
        "outcome": "profit" if pnl is not None and pnl > 0 else "loss",
        "pnl": pnl,
    }


def _orphan_mods(
    session: Session,
    user_id: UUID,
    channel_id: int,
    messages: list[RawTelegramMessage],
    signals: list[dict],
    used_message_ids: set[int],
) -> list[dict]:
    labels = [
        label
        for label in repo.read_labels(session, channel_id, user_id)
        if label.label is LabelKind.MODIFIER
        and label.message_id not in used_message_ids
    ]
    messages_by_id = {message.message_id: message for message in messages}
    return [
        _orphan_row(messages_by_id[label.message_id], signals)
        for label in labels
        if label.message_id in messages_by_id
    ]


def _orphan_row(message: RawTelegramMessage, signals: list[dict]) -> dict:
    return {
        "id": str(message.message_id),
        "feedId": str(message.channel_id),
        "symbol": _suggested_symbol(message.text, signals),
        "date": format_short(message.posted_at),
        "time": format_time(message.posted_at),
        "text": message.text,
        "suggestId": _suggested_signal_id(message.text, signals),
        "reason": "No reply link found",
    }


def _suggested_signal_id(text: str | None, signals: list[dict]) -> str | None:
    symbol = _suggested_symbol(text, signals)
    for signal in reversed(signals):
        if signal["symbol"] == symbol:
            return signal["id"]
    return signals[-1]["id"] if signals else None


def _suggested_symbol(text: str | None, signals: list[dict]) -> str | None:
    normalized = (text or "").upper()
    for signal in reversed(signals):
        base = signal["symbol"].removesuffix("USDT")
        if base in normalized:
            return signal["symbol"]
    return signals[-1]["symbol"] if signals else None


def _outcomes_by_signal_id(result) -> dict[str, dict]:
    if result is None:
        return {}
    return {outcome["rootSignalId"]: outcome for outcome in result.outcomes}


def _deleted_message_ids(session: Session, channel_id: int) -> set[int]:
    return {
        evidence.message_id
        for evidence in repo.read_deletion_evidence(session, channel_id)
        if evidence.confidence.value == "CONFIRMED" and evidence.was_signal_candidate
    }


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text
