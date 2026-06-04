from decimal import Decimal

import pytest

from verasig.services.lifecycle.patch import LifecyclePatch, classify_patch


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
