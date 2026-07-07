from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from verasig.domain.account import Plan
from verasig.domain.lifecycle import FoldedSignal, FoldStep
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import Side, SignalEventType
from verasig.features.feeds import (
    deletion_repository,
    feed_repository,
    message_repository,
)
from verasig.features.feeds.feed_views import feed_initials, feed_tint
from verasig.features.signals import (
    event_repository,
    lifecycle_link_repository,
    outcome_repository,
)
from verasig.features.signals.fold import fold
from verasig.features.signals.materialization import materialize_missing_signal_outcomes
from verasig.features.signals.patch import LifecyclePatch, classify_patch
from verasig.features.simulation import repository as backtest_repository
from verasig.shared.time import format_short, format_time

OBSERVER_SIGNAL_LIMIT = 200
SIGNAL_FEED_STATUSES = {"verified", "analyzed"}


def present_signals(
    session: Session,
    user_id: UUID,
    feed_id: str | None = None,
    status: str | None = None,
    plan: Plan = Plan.DESK,
) -> dict:
    signals = _project_user_signals(session, user_id, feed_id)
    if status is not None:
        signals = [signal for signal in signals if signal["status"] == status]
    # newest first, so the observer truncation below keeps the most recent signals
    signals.sort(key=lambda signal: signal["at"], reverse=True)
    limit_reached = plan is Plan.OBSERVER and len(signals) > OBSERVER_SIGNAL_LIMIT
    if limit_reached:
        signals = signals[:OBSERVER_SIGNAL_LIMIT]
    return {
        "signals": signals,
        "orphanMods": [],
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
) -> list[dict]:
    feeds = [
        feed
        for feed in feed_repository.read_feeds(session, user_id)
        if feed.status in SIGNAL_FEED_STATUSES
    ]
    if feed_id is not None:
        feeds = [feed for feed in feeds if str(feed.external_id) == feed_id]
    latest_results = backtest_repository.read_latest_results(session, user_id)
    signals: list[dict] = []
    for feed in feeds:
        signals.extend(
            _project_channel(
                session, user_id, feed, latest_results.get(feed.external_id)
            )
        )
    return signals


def _project_channel(session: Session, user_id: UUID, feed, result) -> list[dict]:
    channel_id = feed.external_id
    materialize_missing_signal_outcomes(session, user_id, channel_id)
    session.flush()
    messages = message_repository.read_messages(session, user_id, channel_id)
    events = event_repository.read_signal_events(session, user_id, channel_id)
    signals = outcome_repository.read_extracted_signals(session, channel_id, user_id)
    manual_links = {
        link.external_message_id: link.root_signal_id
        for link in lifecycle_link_repository.read_links(session, user_id, channel_id)
    }
    folded = fold(signals, events, messages, manual_links=manual_links)
    message_by_id = {message.message_id: message for message in messages}
    events_by_id = {event.id: event for event in events}
    event_message_ids = {event.id: event.message_id for event in events}
    event_text_by_signal_id = {
        signal.id: events_by_id[signal.event_id].candidate_text
        for signal in signals
        if signal.event_id in events_by_id
    }
    signal_message_ids = {
        signal.id: event_message_ids[signal.event_id]
        for signal in signals
        if signal.event_id in event_message_ids
    }
    outcome_by_signal_id = _outcomes_by_signal_id(result)
    deleted_message_ids = _deleted_message_ids(session, user_id, channel_id)
    return [
        _signal_row(
            item,
            feed,
            message_by_id,
            signal_message_ids,
            event_text_by_signal_id,
            outcome_by_signal_id.get(str(item.root_signal_id)),
            deleted_message_ids,
            set(manual_links),
        )
        for item in folded
    ]


def _signal_row(
    folded: FoldedSignal,
    feed,
    messages: dict[int, RawTelegramMessage],
    signal_message_ids: dict[UUID, int],
    event_text_by_signal_id: dict[UUID, str],
    outcome: dict | None,
    deleted_message_ids: set[int],
    manual_message_ids: set[int],
) -> dict:
    first = folded.timeline[0]
    message = messages[first.source_message_id]
    deleted = signal_message_ids.get(first.source_signal_id) in deleted_message_ids
    return {
        "id": str(folded.root_signal_id),
        **_feed_fields(feed),
        "side": folded.side.value,
        "symbol": folded.symbol,
        "text": message.text or event_text_by_signal_id.get(first.source_signal_id),
        **_outcome_fields(outcome, deleted),
        "at": first.at.isoformat(),  # sortable key; display uses date/time below
        "date": format_short(first.at),
        "time": format_time(first.at),
        "entry": _entry_text(first),
        "stop": _decimal_text(first.effective_stop_loss),
        "tp": [_decimal_text(value) for value in first.effective_take_profits],
        "tpText": _targets_text(first.effective_take_profits),
        "deleted": deleted,
        "cancelled": folded.closed_at is not None,
        "mods": _mods(folded, messages, manual_message_ids),
        "effective": _effective(folded),
    }


def _feed_fields(feed) -> dict:
    handle = feed.meta.get("handle")
    return {
        "feedId": str(feed.external_id),
        "feedName": feed.title,
        "feedTag": f"@{handle}" if handle else None,
        "feedInitials": feed_initials(feed.title),
        "feedTint": feed_tint(feed.title),
        "source": "telegram",
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
        "price": _mod_price(step, patch),
        "text": message.text,
        "effect": _mod_effect(step, patch),
    }


def _mod_kind(side: Side, step: FoldStep, patch: LifecyclePatch) -> str:
    if patch.close:
        return "close"
    if patch.reduce_fraction is not None:
        return "partial"
    if patch.add_multiplier is not None:
        return _average_kind(side, step)
    if patch.set_stop_loss is not None or patch.stop_to_breakeven:
        return "move_stop"
    if patch.set_take_profits is not None:
        # a take-profit-only update is not a stop move; label it distinctly.
        return "move_target"
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


def _outcome_fields(outcome: dict | None, deleted: bool) -> dict:
    if deleted:
        return {"status": "deleted", "outcome": None, "pnl": None}
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


def _outcomes_by_signal_id(result) -> dict[str, dict]:
    if result is None:
        return {}
    return {outcome["rootSignalId"]: outcome for outcome in result.outcomes}


def _deleted_message_ids(session: Session, user_id: UUID, channel_id: int) -> set[int]:
    return {
        evidence.message_id
        for evidence in deletion_repository.read_deletion_evidence(
            session, user_id, channel_id
        )
        if evidence.confidence.value == "CONFIRMED" and evidence.was_signal_candidate
    }


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _entry_text(step: FoldStep) -> str | None:
    low = _decimal_text(step.entry_low or step.effective_entry)
    high = _decimal_text(step.entry_high)
    if low is None:
        return None
    if high is None or high == low:
        return low
    return f"{low} - {high}"


def _targets_text(values: list[Decimal]) -> str | None:
    targets = [_decimal_text(value) for value in values]
    return " / ".join(value for value in targets if value) or None


def _mod_price(step: FoldStep, patch: LifecyclePatch) -> str | None:
    if step.leg_price is not None:
        return _decimal_text(step.leg_price)
    if patch.set_stop_loss is not None:
        return _decimal_text(patch.set_stop_loss)
    if patch.stop_to_breakeven:
        return _decimal_text(step.effective_stop_loss)
    return None


def _mod_effect(step: FoldStep, patch: LifecyclePatch) -> str | None:
    if patch.close:
        return "Closed by author"
    if patch.reduce_fraction is not None:
        pct = _decimal_text(patch.reduce_fraction * Decimal(100))
        return f"{pct}% out" if pct else "Reduced position"
    if patch.add_multiplier is not None:
        entry = _decimal_text(step.effective_entry)
        size = _decimal_text(step.effective_size)
        if entry and size:
            return f"Avg entry -> {entry} - size x{size}"
        return "Averaged position"
    if patch.stop_to_breakeven or patch.set_stop_loss is not None:
        stop = _decimal_text(step.effective_stop_loss)
        return f"Stop -> {stop}" if stop else "Stop updated"
    if patch.set_take_profits is not None:
        targets = _targets_text(step.effective_take_profits)
        return f"Targets -> {targets}" if targets else "Targets updated"
    return None
