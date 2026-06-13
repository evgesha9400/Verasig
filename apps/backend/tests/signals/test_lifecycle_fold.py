from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.lifecycle import FOLD_VERSION
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import EntryType, ExtractedSignal, Side, SignalEventType
from verasig.features.signals.fold import fold

_BASE = datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc)


def _at(minutes: int) -> datetime:
    return _BASE + timedelta(minutes=minutes)


def _message(message_id, minutes, text, reply_to=None) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=7,
        message_id=message_id,
        text=text,
        posted_at=_at(minutes),
        captured_at=_at(minutes),
        reply_to_message_id=reply_to,
        has_media=False,
        raw_payload={},
    )


def _entry(
    message_id,
    minutes,
    *,
    symbol="BTC",
    side=Side.LONG,
    entry_type=EntryType.LIMIT_SINGLE,
    entry_low=None,
    stop_loss=None,
    take_profits=(),
    text="entry",
):
    event_id = uuid4()
    signal = ExtractedSignal(
        event_id=event_id,
        channel_id=7,
        symbol=symbol,
        side=side,
        entry_type=entry_type,
        entry_low=entry_low,
        stop_loss=stop_loss,
        take_profits=list(take_profits),
    )
    event = RawSignalEvent(
        id=event_id,
        channel_id=7,
        message_id=message_id,
        candidate_text=text,
        materialized_by=MaterializationPath.SEED_HEURISTIC,
    )
    return signal, event, _message(message_id, minutes, text)


def test_standalone_entry_folds_to_single_new_entry_step():
    signal, event, message = _entry(
        1, 0, entry_low="65000", stop_loss="64000", take_profits=["67000"]
    )
    folded = fold([signal], [event], [message])
    assert len(folded) == 1
    assert folded[0].root_signal_id == signal.id
    assert folded[0].symbol == "BTCUSDT"
    assert folded[0].fold_version == FOLD_VERSION
    assert folded[0].closed_at is None
    timeline = folded[0].timeline
    assert len(timeline) == 1
    step = timeline[0]
    assert step.event_type is SignalEventType.NEW_ENTRY
    assert step.at == _at(0)
    assert step.effective_size == Decimal(1)
    assert step.effective_entry == Decimal("65000")
    assert step.effective_stop_loss == Decimal("64000")
    assert step.effective_take_profits == [Decimal("67000")]
    assert step.leg_size == Decimal(1)
    assert step.leg_price == Decimal("65000")


def test_move_sl_to_breakeven_reply_updates_effective_stop_to_entry():
    signal, event, entry_msg = _entry(1, 0, entry_low="65000", stop_loss="64000")
    reply = _message(2, 30, "move SL to BE", reply_to=1)
    folded = fold([signal], [event], [entry_msg, reply])
    timeline = folded[0].timeline
    assert len(timeline) == 2
    step = timeline[1]
    assert step.event_type is SignalEventType.MODIFY
    assert step.at == _at(30)
    assert step.source_message_id == 2
    assert step.effective_stop_loss == Decimal("65000")  # == effective entry
    assert step.leg_size is None  # SL-only modify, no size leg
    assert step.leg_price is None
    assert folded[0].closed_at is None


def test_chatter_reply_emits_no_phantom_step():
    signal, event, entry_msg = _entry(1, 0, entry_low="65000")
    chatter = _message(2, 30, "gm frens lovely day", reply_to=1)
    folded = fold([signal], [event], [entry_msg, chatter])
    assert len(folded[0].timeline) == 1  # chatter ignored, only the entry step


def test_priced_average_in_grows_size_and_size_weights_entry():
    signal, event, entry_msg = _entry(1, 0, entry_low="65000")
    reply = _message(2, 30, "add at 63000", reply_to=1)
    folded = fold([signal], [event], [entry_msg, reply])
    step = folded[0].timeline[1]
    assert step.event_type is SignalEventType.MODIFY
    assert step.effective_size == Decimal(2)
    assert step.effective_entry == Decimal("64000")  # (65000*1 + 63000*1) / 2
    assert step.leg_size == Decimal(1)
    assert step.leg_price == Decimal("63000")


def test_market_average_in_leaves_entry_and_leg_price_pending():
    signal, event, entry_msg = _entry(1, 0, entry_low="65000")
    reply = _message(2, 30, "average", reply_to=1)
    folded = fold([signal], [event], [entry_msg, reply])
    step = folded[0].timeline[1]
    assert step.effective_size == Decimal(2)
    assert step.effective_entry is None  # market leg waits for market data
    assert step.leg_size == Decimal(1)
    assert step.leg_price is None


def test_reduce_lowers_size_without_moving_entry():
    signal, event, entry_msg = _entry(1, 0, entry_low="65000")
    reply = _message(2, 30, "reduce half", reply_to=1)
    folded = fold([signal], [event], [entry_msg, reply])
    step = folded[0].timeline[1]
    assert step.event_type is SignalEventType.MODIFY
    assert step.effective_size == Decimal("0.5")
    assert step.effective_entry == Decimal("65000")  # unchanged by a reduce
    assert step.leg_size == Decimal("-0.5")
    assert folded[0].closed_at is None


def test_full_close_keyword_terminates_with_close_step_and_closed_at():
    signal, event, entry_msg = _entry(1, 0, entry_low="65000")
    reply = _message(2, 30, "closed", reply_to=1)
    folded = fold([signal], [event], [entry_msg, reply])
    step = folded[0].timeline[1]
    assert step.event_type is SignalEventType.CLOSE
    assert step.effective_size == Decimal(0)
    assert step.leg_size == Decimal(-1)
    assert folded[0].closed_at == _at(30)


def test_reduce_to_zero_sets_closed_at():
    signal, event, entry_msg = _entry(1, 0, entry_low="65000")
    reply = _message(2, 30, "reduce 100%", reply_to=1)
    folded = fold([signal], [event], [entry_msg, reply])
    step = folded[0].timeline[1]
    assert step.effective_size == Decimal(0)
    assert folded[0].closed_at == _at(30)


def test_out_of_order_messages_are_folded_in_posted_at_order():
    signal, event, entry_msg = _entry(1, 0, entry_low="65000")
    add = _message(2, 30, "add at 63000", reply_to=1)
    reduce = _message(3, 60, "reduce half", reply_to=1)
    folded = fold([signal], [event], [reduce, entry_msg, add])  # shuffled input
    timeline = folded[0].timeline
    assert [step.at for step in timeline] == [_at(0), _at(30), _at(60)]
    assert [step.effective_size for step in timeline] == [
        Decimal(1),
        Decimal(2),
        Decimal(1),
    ]


def test_transitive_reply_through_a_non_entry_message_joins_the_root():
    signal, event, entry_msg = _entry(1, 0, entry_low="65000")
    chatter = _message(2, 30, "thoughts?", reply_to=1)  # non-actionable, no step
    patch = _message(3, 60, "move SL to BE", reply_to=2)  # replies to the chatter
    folded = fold([signal], [event], [entry_msg, chatter, patch])
    timeline = folded[0].timeline
    assert len(timeline) == 2  # entry + the transitively-threaded patch
    assert timeline[1].source_message_id == 3
    assert timeline[1].effective_stop_loss == Decimal("65000")


def test_manual_link_joins_unthreaded_modifier_to_root_signal():
    signal, event, entry_msg = _entry(1, 0, entry_low="65000")
    patch = _message(2, 30, "move SL to BE")

    folded = fold([signal], [event], [entry_msg, patch], manual_links={2: signal.id})

    timeline = folded[0].timeline
    assert len(timeline) == 2
    assert timeline[1].source_message_id == 2
    assert timeline[1].effective_stop_loss == Decimal("65000")


def test_different_symbol_reply_that_is_a_signal_starts_its_own_root():
    btc, btc_event, btc_msg = _entry(1, 0, symbol="BTC", entry_low="65000")
    eth, eth_event, eth_msg = _entry(2, 30, symbol="ETH", entry_low="3000")
    eth_msg = _message(2, 30, "ETH long", reply_to=1)  # replies to the BTC entry
    folded = fold([btc, eth], [btc_event, eth_event], [btc_msg, eth_msg])
    assert len(folded) == 2
    by_symbol = {f.symbol: f for f in folded}
    assert set(by_symbol) == {"BTCUSDT", "ETHUSDT"}
    assert len(by_symbol["BTCUSDT"].timeline) == 1  # ETH is not a member of BTC
    assert len(by_symbol["ETHUSDT"].timeline) == 1
