from datetime import datetime, timedelta, timezone
from decimal import Decimal

from verasig.domain.lifecycle import FOLD_VERSION
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import EntryType, Side, Signal, SignalEventType
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
    signal = Signal(
        channel_id=7,
        message_id=message_id,
        candidate_text=text,
        symbol=symbol,
        side=side,
        entry_type=entry_type,
        entry_low=entry_low,
        stop_loss=stop_loss,
        take_profits=list(take_profits),
    )
    return signal, _message(message_id, minutes, text)


def test_standalone_entry_folds_to_single_new_entry_step():
    signal, message = _entry(
        1, 0, entry_low="65000", stop_loss="64000", take_profits=["67000"]
    )
    folded = fold([signal], [message])
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
    signal, entry_msg = _entry(1, 0, entry_low="65000", stop_loss="64000")
    reply = _message(2, 30, "move SL to BE", reply_to=1)
    folded = fold([signal], [entry_msg, reply])
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
    signal, entry_msg = _entry(1, 0, entry_low="65000")
    chatter = _message(2, 30, "gm frens lovely day", reply_to=1)
    folded = fold([signal], [entry_msg, chatter])
    assert len(folded[0].timeline) == 1  # chatter ignored, only the entry step


def test_priced_average_in_grows_size_and_size_weights_entry():
    signal, entry_msg = _entry(1, 0, entry_low="65000")
    reply = _message(2, 30, "add at 63000", reply_to=1)
    folded = fold([signal], [entry_msg, reply])
    step = folded[0].timeline[1]
    assert step.event_type is SignalEventType.MODIFY
    assert step.effective_size == Decimal(2)
    assert step.effective_entry == Decimal("64000")  # (65000*1 + 63000*1) / 2
    assert step.leg_size == Decimal(1)
    assert step.leg_price == Decimal("63000")


def test_market_average_in_leaves_entry_and_leg_price_pending():
    signal, entry_msg = _entry(1, 0, entry_low="65000")
    reply = _message(2, 30, "average", reply_to=1)
    folded = fold([signal], [entry_msg, reply])
    step = folded[0].timeline[1]
    assert step.effective_size == Decimal(2)
    assert step.effective_entry is None  # market leg waits for market data
    assert step.leg_size == Decimal(1)
    assert step.leg_price is None


def test_reduce_lowers_size_without_moving_entry():
    signal, entry_msg = _entry(1, 0, entry_low="65000")
    reply = _message(2, 30, "reduce half", reply_to=1)
    folded = fold([signal], [entry_msg, reply])
    step = folded[0].timeline[1]
    assert step.event_type is SignalEventType.MODIFY
    assert step.effective_size == Decimal("0.5")
    assert step.effective_entry == Decimal("65000")  # unchanged by a reduce
    assert step.leg_size == Decimal("-0.5")
    assert folded[0].closed_at is None


def test_full_close_keyword_terminates_with_close_step_and_closed_at():
    signal, entry_msg = _entry(1, 0, entry_low="65000")
    reply = _message(2, 30, "closed", reply_to=1)
    folded = fold([signal], [entry_msg, reply])
    step = folded[0].timeline[1]
    assert step.event_type is SignalEventType.CLOSE
    assert step.effective_size == Decimal(0)
    assert step.leg_size == Decimal(-1)
    assert folded[0].closed_at == _at(30)


def test_reduce_to_zero_sets_closed_at():
    signal, entry_msg = _entry(1, 0, entry_low="65000")
    reply = _message(2, 30, "reduce 100%", reply_to=1)
    folded = fold([signal], [entry_msg, reply])
    step = folded[0].timeline[1]
    assert step.effective_size == Decimal(0)
    assert folded[0].closed_at == _at(30)


def test_out_of_order_messages_are_folded_in_posted_at_order():
    signal, entry_msg = _entry(1, 0, entry_low="65000")
    add = _message(2, 30, "add at 63000", reply_to=1)
    reduce = _message(3, 60, "reduce half", reply_to=1)
    folded = fold([signal], [reduce, entry_msg, add])  # shuffled input
    timeline = folded[0].timeline
    assert [step.at for step in timeline] == [_at(0), _at(30), _at(60)]
    assert [step.effective_size for step in timeline] == [
        Decimal(1),
        Decimal(2),
        Decimal(1),
    ]


def test_transitive_reply_through_a_non_entry_message_joins_the_root():
    signal, entry_msg = _entry(1, 0, entry_low="65000")
    chatter = _message(2, 30, "thoughts?", reply_to=1)  # non-actionable, no step
    patch = _message(3, 60, "move SL to BE", reply_to=2)  # replies to the chatter
    folded = fold([signal], [entry_msg, chatter, patch])
    timeline = folded[0].timeline
    assert len(timeline) == 2  # entry + the transitively-threaded patch
    assert timeline[1].source_message_id == 3
    assert timeline[1].effective_stop_loss == Decimal("65000")


def test_manual_link_joins_unthreaded_modifier_to_root_signal():
    signal, entry_msg = _entry(1, 0, entry_low="65000")
    patch = _message(2, 30, "move SL to BE")

    folded = fold([signal], [entry_msg, patch], manual_links={2: signal.id})

    timeline = folded[0].timeline
    assert len(timeline) == 2
    assert timeline[1].source_message_id == 2
    assert timeline[1].effective_stop_loss == Decimal("65000")


def test_different_symbol_reply_that_is_a_signal_starts_its_own_root():
    btc, btc_msg = _entry(1, 0, symbol="BTC", entry_low="65000")
    eth, eth_msg = _entry(2, 30, symbol="ETH", entry_low="3000")
    eth_msg = _message(2, 30, "ETH long", reply_to=1)  # replies to the BTC entry
    folded = fold([btc, eth], [btc_msg, eth_msg])
    assert len(folded) == 2
    by_symbol = {f.symbol: f for f in folded}
    assert set(by_symbol) == {"BTCUSDT", "ETHUSDT"}
    assert len(by_symbol["BTCUSDT"].timeline) == 1  # ETH is not a member of BTC
    assert len(by_symbol["ETHUSDT"].timeline) == 1


def test_reply_to_a_manually_linked_modifier_joins_the_same_root():
    signal, entry_msg = _entry(1, 0, entry_low="65000", stop_loss="64000")
    linked = _message(2, 30, "SL 64500")  # unthreaded, linked by hand
    reply = _message(3, 60, "SL 64800", reply_to=2)  # replies to the linked one
    deeper = _message(4, 90, "SL 64900", reply_to=3)  # transitively
    folded = fold(
        [signal], [entry_msg, linked, reply, deeper], manual_links={2: signal.id}
    )
    timeline = folded[0].timeline
    assert [step.source_message_id for step in timeline] == [1, 2, 3, 4]
    assert timeline[-1].effective_stop_loss == Decimal("64900")


def test_reply_naming_another_instrument_does_not_patch_the_signal():
    signal, entry_msg = _entry(1, 0, symbol="BTC", entry_low="65000", stop_loss="64000")
    reply = _message(2, 30, "ETH move SL to 3000", reply_to=1)
    folded = fold([signal], [entry_msg, reply])
    timeline = folded[0].timeline
    assert len(timeline) == 1  # the ETH reply is skipped for the BTCUSDT signal
    assert timeline[0].effective_stop_loss == Decimal("64000")


def test_reply_naming_the_same_instrument_patches_the_signal():
    signal, entry_msg = _entry(1, 0, symbol="BTC", entry_low="65000", stop_loss="64000")
    reply = _message(2, 30, "BTC move SL to 64500", reply_to=1)
    folded = fold([signal], [entry_msg, reply])
    timeline = folded[0].timeline
    assert len(timeline) == 2
    assert timeline[1].effective_stop_loss == Decimal("64500")


def test_reduce_beyond_the_whole_position_closes_without_going_negative():
    signal, entry_msg = _entry(1, 0, entry_low="65000")
    reply = _message(2, 30, "reduce 150%", reply_to=1)
    folded = fold([signal], [entry_msg, reply])
    step = folded[0].timeline[1]
    assert step.event_type is SignalEventType.CLOSE
    assert step.effective_size == Decimal(0)
    assert step.leg_size == Decimal(-1)
    assert folded[0].closed_at == _at(30)


def test_size_reduction_after_close_is_ignored():
    signal, entry_msg = _entry(1, 0, entry_low="65000")
    close = _message(2, 30, "closed", reply_to=1)
    again = _message(3, 60, "reduce half", reply_to=1)
    folded = fold([signal], [entry_msg, close, again])
    timeline = folded[0].timeline
    assert len(timeline) == 2  # a size-only reply after close adds no step
    assert timeline[-1].effective_size == Decimal(0)
    assert folded[0].closed_at == _at(30)


def test_stop_update_after_close_still_applies_without_a_size_leg():
    signal, entry_msg = _entry(1, 0, entry_low="65000", stop_loss="64000")
    close = _message(2, 30, "closed", reply_to=1)
    late = _message(3, 60, "close half, SL 64500", reply_to=1)
    folded = fold([signal], [entry_msg, close, late])
    step = folded[0].timeline[-1]
    assert step.source_message_id == 3
    assert step.event_type is SignalEventType.MODIFY
    assert step.effective_stop_loss == Decimal("64500")
    assert step.effective_size == Decimal(0)
    assert step.leg_size is None
    assert folded[0].closed_at == _at(30)


def test_an_add_after_close_does_not_reopen_the_position():
    signal, entry_msg = _entry(1, 0, entry_low="65000")
    close = _message(2, 30, "closed", reply_to=1)
    add = _message(3, 60, "add 1x at 64000", reply_to=1)
    folded = fold([signal], [entry_msg, close, add])
    assert len(folded[0].timeline) == 2
    assert folded[0].timeline[-1].effective_size == Decimal(0)


def test_reply_naming_an_overlay_instrument_does_not_patch_the_signal():
    # "WIFFY" is an instrument only through the user's parser overlay; the symbol
    # guard must honour it exactly as the miner does.
    signal, entry_msg = _entry(1, 0, symbol="BTC", entry_low="65000", stop_loss="64000")
    reply = _message(2, 30, "WIFFY move SL to 3000", reply_to=1)
    overlay = {"instrumentAliases": {"WIFFY": "WIFUSDT"}}

    without_overlay = fold([signal], [entry_msg, reply])
    with_overlay = fold([signal], [entry_msg, reply], overlay=overlay)

    assert len(without_overlay[0].timeline) == 2
    assert len(with_overlay[0].timeline) == 1


def test_deep_reply_chain_folds_every_member_once():
    signal, entry_msg = _entry(1, 0, entry_low="65000", stop_loss="60000")
    chain = [
        _message(index, index, f"SL {60000 + index}", reply_to=index - 1)
        for index in range(2, 202)
    ]

    folded = fold([signal], [entry_msg, *reversed(chain)])

    timeline = folded[0].timeline
    assert [step.source_message_id for step in timeline] == list(range(1, 202))
    assert timeline[-1].effective_stop_loss == Decimal("60201")


def test_reply_cycle_without_a_root_is_not_a_member():
    signal, entry_msg = _entry(1, 0, entry_low="65000", stop_loss="64000")
    first = _message(2, 30, "SL 64500", reply_to=3)
    second = _message(3, 60, "SL 64800", reply_to=2)

    folded = fold([signal], [entry_msg, first, second])

    assert len(folded[0].timeline) == 1
