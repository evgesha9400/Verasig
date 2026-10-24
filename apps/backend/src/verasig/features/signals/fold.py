"""Signal-lifecycle fold (data-contracts.md §5; ADR 0007).

`fold` threads each entry `Signal`'s `reply_to` chain (transitive, through
manually linked modifiers too) into a time-ordered `FoldedSignal`: it seeds the
effective position from the entry, then applies each in-thread patch in
`posted_at` order, snapshotting the effective stop / take-profits / size / average
entry after every step. A reply that names a different instrument is skipped
(symbol guard). Pure + offline; the fold is never stored, only stamped
with `fold_version` so a past fold is reproducible.

Join chain: `Signal.message_id → RawTelegramMessage` (for `reply_to` + `posted_at`).
"""

from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID

from verasig.domain.lifecycle import FOLD_VERSION, FoldedSignal, FoldStep
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import EntryType, Signal, SignalEventType
from verasig.features.mining.template_mining.instruments import detect_instruments
from verasig.features.signals.patch import LifecyclePatch, classify_patch


@dataclass
class _Position:
    stop_loss: Decimal | None
    take_profits: list[Decimal]
    size: Decimal
    entry: Decimal | None


def _entry_message_ids(signals: list[Signal]) -> dict[int, Signal]:
    return {signal.message_id: signal for signal in signals}


def _nearest_root_message_id(
    message_id: int,
    messages_by_id: dict[int, RawTelegramMessage],
    entry_message_ids: dict[int, Signal],
    manual_roots: dict[int, int],
    root_cache: dict[int, int | None],
) -> int | None:
    """Walk up the reply chain to the first entry root or manually linked
    message (transitive, cycle-guarded). Every visited node's root is cached,
    so folding a whole feed walks each reply edge once."""
    path: dict[int, None] = {}  # insertion-ordered set of visited nodes
    root = None
    current: int | None = message_id
    while current is not None:
        if current in root_cache:
            root = root_cache[current]
            break
        if current in path:
            break  # a reply cycle reaches no root
        path[current] = None
        if current in entry_message_ids:
            root = current
            break
        if current in manual_roots:
            root = manual_roots[current]  # a linked modifier, or a reply to one
            break
        parent = messages_by_id.get(current)
        current = parent.reply_to_message_id if parent else None
    for node in path:
        root_cache[node] = root
    return root


def _members_by_root(
    entry_message_ids: dict[int, Signal],
    messages_by_id: dict[int, RawTelegramMessage],
    messages: list[RawTelegramMessage],
    manual_links: dict[int, UUID],
) -> dict[int, list[RawTelegramMessage]]:
    members: dict[int, list[RawTelegramMessage]] = {
        root: [] for root in entry_message_ids
    }
    root_by_signal_id = {
        signal.id: message_id for message_id, signal in entry_message_ids.items()
    }
    manual_roots = {
        message_id: root_by_signal_id[signal_id]
        for message_id, signal_id in manual_links.items()
        if signal_id in root_by_signal_id
    }
    root_cache: dict[int, int | None] = {}
    for message in messages:
        if message.message_id in entry_message_ids:
            continue  # an entry is its own root, never a member
        root = _nearest_root_message_id(
            message.message_id,
            messages_by_id,
            entry_message_ids,
            manual_roots,
            root_cache,
        )
        if root is not None:
            members[root].append(message)
    for member_list in members.values():
        member_list.sort(key=lambda member: member.posted_at)
    return members


def _seed_entry_price(signal: Signal) -> Decimal | None:
    if signal.entry_type is EntryType.MARKET:
        return None
    return signal.entry_low


def _seed_position(signal: Signal) -> _Position:
    return _Position(
        stop_loss=signal.stop_loss,
        take_profits=list(signal.take_profits),
        size=Decimal(1),
        entry=_seed_entry_price(signal),
    )


def _entry_step(
    signal: Signal, root_message: RawTelegramMessage, position: _Position
) -> FoldStep:
    return FoldStep(
        at=root_message.posted_at,
        source_signal_id=signal.id,
        source_message_id=root_message.message_id,
        event_type=SignalEventType.NEW_ENTRY,
        effective_stop_loss=position.stop_loss,
        effective_take_profits=list(position.take_profits),
        effective_size=position.size,
        effective_entry=position.entry,
        entry_low=signal.entry_low,
        entry_high=signal.entry_high or signal.entry_low,
        leg_size=Decimal(1),
        leg_price=position.entry,
    )


def _apply_stop_to_position(patch: LifecyclePatch, position: _Position) -> None:
    if patch.stop_to_breakeven:
        position.stop_loss = position.entry  # BE := current effective entry
    elif patch.set_stop_loss is not None:
        position.stop_loss = patch.set_stop_loss


def _apply_take_profits_to_position(patch: LifecyclePatch, position: _Position) -> None:
    if patch.set_take_profits is not None:
        position.take_profits = list(patch.set_take_profits)  # stated set replaces


def _averaged_entry(
    position: _Position, multiplier: Decimal, price: Decimal | None, new_size: Decimal
) -> Decimal | None:
    if position.entry is None or price is None:
        return None  # a market leg leaves the average entry unresolved
    return (position.entry * position.size + price * multiplier) / new_size


def _apply_add(
    patch: LifecyclePatch, position: _Position
) -> tuple[Decimal, Decimal | None]:
    multiplier = patch.add_multiplier
    price = patch.add_price
    new_size = position.size + multiplier
    position.entry = _averaged_entry(position, multiplier, price, new_size)
    position.size = new_size
    return multiplier, price  # leg_size (+add), leg_price (None ⇒ market)


def _apply_reduce(patch: LifecyclePatch, position: _Position) -> tuple[Decimal, None]:
    leg_size = -(position.size * patch.reduce_fraction)
    position.size = position.size * (Decimal(1) - patch.reduce_fraction)
    return leg_size, None  # entry unchanged: proportional scaling keeps the avg


def _apply_close(position: _Position) -> tuple[Decimal, None]:
    leg_size = -position.size
    position.size = Decimal(0)
    return leg_size, None  # entry carries (informational)


def _apply_size_op(
    patch: LifecyclePatch, position: _Position
) -> tuple[Decimal | None, Decimal | None, bool]:
    """Return (leg_size, leg_price, is_close) for this patch's one size operation."""
    if patch.close:
        leg_size, leg_price = _apply_close(position)
        return leg_size, leg_price, True
    if patch.reduce_fraction is not None:
        leg_size, leg_price = _apply_reduce(patch, position)
        return leg_size, leg_price, False
    if patch.add_multiplier is not None:
        leg_size, leg_price = _apply_add(patch, position)
        return leg_size, leg_price, False
    return None, None, False


def _apply_patch(
    signal: Signal,
    message: RawTelegramMessage,
    patch: LifecyclePatch,
    position: _Position,
) -> FoldStep:
    _apply_stop_to_position(patch, position)
    _apply_take_profits_to_position(patch, position)
    leg_size, leg_price, is_close = _apply_size_op(patch, position)
    event_type = SignalEventType.CLOSE if is_close else SignalEventType.MODIFY
    return FoldStep(
        at=message.posted_at,
        source_signal_id=signal.id,
        source_message_id=message.message_id,
        event_type=event_type,
        effective_stop_loss=position.stop_loss,
        effective_take_profits=list(position.take_profits),
        effective_size=position.size,
        effective_entry=position.entry,
        leg_size=leg_size,
        leg_price=leg_price,
    )


def _names_other_instrument(text: str, symbol: str, overlay: dict | None) -> bool:
    named = {entity.normalized for entity in detect_instruments(text, overlay)}
    return bool(named) and symbol not in named


def applicable_patch(patch: LifecyclePatch, size_before: Decimal) -> LifecyclePatch:
    """The part of ``patch`` that applies to a position of ``size_before``: a
    closed position takes no further size op (add/reduce/close); its stop/TP
    may still move."""
    if size_before > 0:
        return patch
    return replace(
        patch, add_multiplier=None, add_price=None, reduce_fraction=None, close=False
    )


def _fold_one(
    signal: Signal,
    root_message: RawTelegramMessage,
    members: list[RawTelegramMessage],
    version: int,
    overlay: dict | None,
) -> FoldedSignal:
    position = _seed_position(signal)
    timeline = [_entry_step(signal, root_message, position)]
    closed_at = None
    for message in members:
        text = message.text or ""
        if _names_other_instrument(text, signal.symbol, overlay):
            continue  # "ETH move SL" never patches a BTCUSDT signal
        patch = applicable_patch(classify_patch(text), position.size)
        if not patch.is_actionable:
            continue  # inert reply: no phantom lifecycle step
        step = _apply_patch(signal, message, patch, position)
        timeline.append(step)
        if closed_at is None and position.size <= 0:
            closed_at = step.at
    return FoldedSignal(
        root_signal_id=signal.id,
        symbol=signal.symbol,
        side=signal.side,
        timeline=timeline,
        closed_at=closed_at,
        fold_version=version,
    )


def fold(
    signals: list[Signal],
    messages: list[RawTelegramMessage],
    version: int = FOLD_VERSION,
    manual_links: dict[int, UUID] | None = None,
    overlay: dict | None = None,
) -> list[FoldedSignal]:
    """Fold each entry signal + its reply-chain patches into a FoldedSignal.
    ``overlay`` is the user's parser overlay, so the symbol guard recognizes
    the same custom instruments the miner does."""
    entry_message_ids = _entry_message_ids(signals)
    messages_by_id = {message.message_id: message for message in messages}
    members = _members_by_root(
        entry_message_ids, messages_by_id, messages, manual_links or {}
    )
    return [
        _fold_one(
            signal, messages_by_id[message_id], members[message_id], version, overlay
        )
        for message_id, signal in entry_message_ids.items()
        if message_id in messages_by_id
    ]
