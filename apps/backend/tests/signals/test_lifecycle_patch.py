from decimal import Decimal

import pytest

from verasig.features.signals.patch import LifecyclePatch, classify_patch


# --- breakeven (EN + RU); BE wins over a numeric stop -------------------------
@pytest.mark.parametrize(
    "text",
    [
        "move SL to BE",
        "to b/e",
        "breakeven now",
        "break even",
        "в безубыток",
        "безубыток",
    ],
)
def test_breakeven_is_recognized(text):
    assert classify_patch(text).stop_to_breakeven is True


def test_breakeven_does_not_also_set_a_numeric_stop():
    patch = classify_patch("move SL to BE")
    assert patch.stop_to_breakeven is True
    assert patch.set_stop_loss is None


# --- set stop-loss (EN + RU) --------------------------------------------------
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("SL 64000", Decimal("64000")),
        ("sl: 64,000", Decimal("64000")),
        ("move stop to 65k", Decimal("65000")),
        ("stop loss 64000", Decimal("64000")),
        ("стоп 64000", Decimal("64000")),
    ],
)
def test_set_stop_loss_parses_the_stated_number(text, expected):
    assert classify_patch(text).set_stop_loss == expected


# --- set take-profits (stated set replaces) -----------------------------------
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("TP 67000", [Decimal("67000")]),
        ("TP 67000 68000", [Decimal("67000"), Decimal("68000")]),
        ("targets 67000, 68000", [Decimal("67000"), Decimal("68000")]),
        ("тейк 67000", [Decimal("67000")]),
    ],
)
def test_set_take_profits_collects_the_stated_numbers(text, expected):
    assert classify_patch(text).set_take_profits == expected


# --- average-in / scale-in ----------------------------------------------------
def test_add_priced_sets_multiplier_one_and_price():
    patch = classify_patch("add at 64000")
    assert patch.add_multiplier == Decimal(1)
    assert patch.add_price == Decimal("64000")


@pytest.mark.parametrize(
    "text", ["average", "avg here", "DCA", "scale in", "усредняю", "докупил"]
)
def test_add_market_sets_multiplier_one_and_no_price(text):
    patch = classify_patch(text)
    assert patch.add_multiplier == Decimal(1)
    assert patch.add_price is None


def test_add_half_size_sets_fractional_multiplier():
    patch = classify_patch("add 50%")
    assert patch.add_multiplier == Decimal("0.5")
    assert patch.add_price is None


def test_add_multiplier_x_notation():
    assert classify_patch("add 2x").add_multiplier == Decimal(2)


# --- reduce / partial ---------------------------------------------------------
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("reduce half", Decimal("0.5")),
        ("close 25%", Decimal("0.25")),
        ("close half", Decimal("0.5")),
        ("take partial", Decimal("0.5")),
        ("сократить наполовину", Decimal("0.5")),
    ],
)
def test_reduce_sets_fraction_and_is_not_a_full_close(text, expected):
    patch = classify_patch(text)
    assert patch.reduce_fraction == expected
    assert patch.close is False


# --- full close (EN + RU) — only when NOT a fractional reduce -----------------
@pytest.mark.parametrize(
    "text",
    [
        "close",
        "closed",
        "close it",
        "fully closed",
        "all out",
        "exit",
        "stopped out",
        "TP hit",
        "SL hit",
        "закрыл",
        "закрытие",
        "стоп выбит",
    ],
)
def test_full_close_is_recognized(text):
    patch = classify_patch(text)
    assert patch.close is True
    assert patch.reduce_fraction is None


# --- chatter is inert (no phantom step) ---------------------------------------
@pytest.mark.parametrize("text", ["gm frens lovely day", "🚀🚀🚀", "great call!"])
def test_chatter_is_not_actionable(text):
    assert classify_patch(text).is_actionable is False


def test_default_patch_is_not_actionable():
    assert LifecyclePatch().is_actionable is False


def test_a_recognized_patch_is_actionable():
    assert classify_patch("move SL to BE").is_actionable is True


# --- outcome reports are not new take-profits ---------------------------------
@pytest.mark.parametrize(
    "text",
    [
        "Move BTC stop to entry (break-even). First target 66.5k tagged",
        "TP 1 hit",
        "TP 67000 reached",
        "target 67000 smashed",
        "TP 67000 done",
        "тейк 67000 взят",
        "тейк 67000 достигнут",
    ],
)
def test_take_profit_outcome_report_does_not_set_take_profits(text):
    assert classify_patch(text).set_take_profits is None


def test_outcome_report_in_another_clause_keeps_the_stated_take_profits():
    patch = classify_patch("TP 67000. Close if 60000 is hit")
    assert patch.set_take_profits == [Decimal("67000")]


# --- add price binds to the add clause only -----------------------------------
def test_add_with_a_stop_does_not_steal_the_stop_as_add_price():
    patch = classify_patch("add here, SL 62000")
    assert patch.add_multiplier == Decimal(1)
    assert patch.add_price is None  # market-at-time
    assert patch.set_stop_loss == Decimal("62000")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("add more at 63000, SL 62000", Decimal("63000")),
        ("add @ 63000", Decimal("63000")),
        ("add 63000 SL 62000", Decimal("63000")),
        ("averaging at 63k", Decimal("63000")),
    ],
)
def test_add_price_is_the_price_bound_to_the_add_clause(text, expected):
    assert classify_patch(text).add_price == expected


def test_add_price_never_takes_a_take_profit_number():
    patch = classify_patch("add, TP 70000")
    assert patch.add_price is None
    assert patch.set_take_profits == [Decimal("70000")]


@pytest.mark.parametrize(
    "text",
    [
        "price holding above the 50 moving average",
        "цена над 50 скользящей средней",
    ],
)
def test_moving_average_is_not_an_average_in(text):
    patch = classify_patch(text)
    assert patch.add_multiplier is None
    assert patch.add_price is None
    assert patch.is_actionable is False


# --- negated / non-close wording is not a size operation ----------------------
@pytest.mark.parametrize(
    "text",
    [
        "do not close",
        "don't close yet",
        "dont exit",
        "never add to losers",
        "not reduce",
        "closely watch price",
    ],
)
def test_negated_or_lookalike_size_wording_is_not_a_size_op(text):
    patch = classify_patch(text)
    assert patch.close is False
    assert patch.reduce_fraction is None
    assert patch.add_multiplier is None


def test_negated_close_keeps_the_stop_update():
    patch = classify_patch("do not close, SL 64000")
    assert patch.close is False
    assert patch.set_stop_loss == Decimal("64000")


# --- signed PnL percentages are not size factors ------------------------------
@pytest.mark.parametrize(
    "text",
    [
        "Closed at 66,500 for +3.9%",
        "closed -2.5%",
        "closed −1.2%",
    ],
)
def test_signed_pnl_percentage_is_a_full_close_not_a_partial(text):
    patch = classify_patch(text)
    assert patch.close is True
    assert patch.reduce_fraction is None


@pytest.mark.parametrize(
    "text", ["close all, 3.9% profit", "all out 12%", "fully closed 40%"]
)
def test_explicit_full_close_wins_over_an_unsigned_percentage(text):
    patch = classify_patch(text)
    assert patch.close is True
    assert patch.reduce_fraction is None


# --- stated factor bounds -----------------------------------------------------
@pytest.mark.parametrize("text", ["reduce 0%", "close 0%", "add 0x"])
def test_zero_factor_is_not_actionable(text):
    assert classify_patch(text).is_actionable is False


@pytest.mark.parametrize("text", ["reduce 100%", "reduce 150%", "close 100%"])
def test_reduce_by_whole_position_or_more_is_a_full_close(text):
    patch = classify_patch(text)
    assert patch.close is True
    assert patch.reduce_fraction is None


def test_an_outcome_clause_does_not_hide_a_new_target_in_the_next_clause():
    assert classify_patch("TP1 hit, new TP 70000").set_take_profits == [
        Decimal("70000")
    ]


def test_a_spaced_dash_is_a_separator_not_a_pnl_sign():
    assert classify_patch("Close - 30%").reduce_fraction == Decimal("0.3")


def test_closes_is_a_close_verb():
    assert classify_patch("closes half").reduce_fraction == Decimal("0.5")


# --- negation and conditions bind to their own clause -------------------------
@pytest.mark.parametrize(
    "text",
    [
        "do not move SL to BE",
        "don't move stop to breakeven",
        "не переносить в безубыток",
    ],
)
def test_negated_breakeven_is_not_a_stop_move(text):
    patch = classify_patch(text)
    assert patch.stop_to_breakeven is False
    assert patch.is_actionable is False


def test_a_negated_clause_does_not_suppress_the_next_clause():
    patch = classify_patch("Do not close, reduce 25%")
    assert patch.close is False
    assert patch.reduce_fraction == Decimal("0.25")


@pytest.mark.parametrize(
    "text",
    [
        "Close if price reaches 90",
        "close when 4H candle closes below 60000",
        "закрываем, если пробьет 60000",
    ],
)
def test_a_conditional_close_is_not_a_close(text):
    patch = classify_patch(text)
    assert patch.close is False
    assert patch.reduce_fraction is None


def test_a_conditional_clause_keeps_the_unconditional_stop():
    patch = classify_patch("SL 64000. If it breaks 70k, close")
    assert patch.set_stop_loss == Decimal("64000")
    assert patch.close is False


# --- add price never reads a decimal factor or another clause -----------------
@pytest.mark.parametrize(
    ("text", "multiplier"),
    [("add 2.5x at market", Decimal("2.5")), ("add 12.5% here", Decimal("0.125"))],
)
def test_add_factor_is_never_read_as_the_add_price(text, multiplier):
    patch = classify_patch(text)
    assert patch.add_multiplier == multiplier
    assert patch.add_price is None


def test_add_price_stops_at_the_clause_break():
    patch = classify_patch("add 50% at market, close at 110")
    assert patch.add_multiplier == Decimal("0.5")
    assert patch.add_price is None


# --- decimal commas -----------------------------------------------------------
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("SL 0,20", Decimal("0.20")),
        ("стоп 1,25", Decimal("1.25")),
        ("SL 0,005", Decimal("0.005")),
        ("SL 1,000", Decimal("1000")),
        ("SL 65,000.5", Decimal("65000.5")),
    ],
)
def test_decimal_comma_is_a_decimal_point_and_grouping_comma_is_dropped(text, expected):
    assert classify_patch(text).set_stop_loss == expected


@pytest.mark.parametrize("text", ["Cancelled", "cancel this one", "Отмена"])
def test_a_cancel_is_a_full_close(text):
    patch = classify_patch(text)
    assert patch.close is True
    assert patch.reduce_fraction is None


def test_a_cancel_condition_is_not_a_close():
    assert classify_patch("cancel if 4H closes below 90").close is False
