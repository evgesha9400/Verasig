"""Parity port of ``realFormat.test.js`` - Russian-language crypto signals.

Монета: <COIN> / Купил в ЛОНГ|ШОРТ 🔼|🔽 / Вход / Стоп / Цели: on following
numbered (keycap-emoji) lines. Results use Результат / Заработано / принесла.
"""
# ruff: noqa: E501

from __future__ import annotations

from verasig.features.rules.template_mining.directions import detect_directions
from verasig.features.rules.template_mining.extract import attempt_extract_signal
from verasig.features.rules.template_mining.fields import extract_signal_fields
from verasig.features.rules.template_mining.instruments import detect_instruments
from verasig.features.rules.template_mining.prices import detect_prices

REAL_SIGNAL = """Монета: XRP ☝️

Купил в ШОРТ🔽


⚫️ Вход: $2.5445

⚫️ Стоп: $2.6632

⚪️ Цели:

1️⃣ 2.5190 💵
2️⃣ 2.4936 💵
3️⃣ 2.4681 💵


Решение о фиксации прибыли, вы принимаете самостоятельно"""

REAL_RESULT = """📊 Результат по сделке: XRP  ☝️

➕ Позиция принесла 50% прибыли, фиксируем часть и остальное, ставим стоп в бу ‼️

📈 Заработано: +$258"""


# --- primitives ---
def test_detects_the_coin_after_the_russian_coin_label():
    normals = [e.normalized for e in detect_instruments("Монета: XRP ☝️")]
    assert "XRPUSDT" in normals


def test_detects_a_bare_crypto_ticker():
    normals = [e.normalized for e in detect_instruments("Монета: DOGE")]
    assert "DOGEUSDT" in normals


def test_reads_russian_direction_words():
    assert "SELL" in [e.normalized for e in detect_directions("Купил в ШОРТ")]
    assert "BUY" in [e.normalized for e in detect_directions("Купил в ЛОНГ")]


def test_reads_the_up_down_trade_emojis():
    assert "SELL" in [e.normalized for e in detect_directions("XRP \U0001f53d")]
    assert "BUY" in [e.normalized for e in detect_directions("XRP \U0001f53c")]


def test_does_not_read_keycap_emoji_ordinals_as_prices():
    assert [p.value for p in detect_prices("1️⃣ 2.5190 💵")] == [2.519]


# --- extraction ---
def test_extracts_instrument_and_direction():
    fields = extract_signal_fields(REAL_SIGNAL)
    assert fields.instrument == "XRPUSDT"
    assert fields.direction == "SELL"


def test_extracts_the_entry_and_stop_from_russian_labels():
    fields = extract_signal_fields(REAL_SIGNAL)
    assert fields.entry.type == "single"
    assert fields.entry.price == 2.5445
    assert fields.stop_loss == 2.6632


def test_collects_targets_listed_under_the_celi_header_on_following_lines():
    fields = extract_signal_fields(REAL_SIGNAL)
    assert fields.take_profits == [2.519, 2.4936, 2.4681]


# --- dominant "Фиксируем прибыль на" target format ---
_AAVE = "🪙 МОНЕТА: #AAVE/USDT\n📉📈ПОКУПКА: SHORT\n ПЛЕЧО: 18х\n· Вход: 159.81$\n· Фиксируем прибыль на:158.03$, 155.37$, 151.81$\n· Стоп: 172.23$"


def test_extracts_instrument_direction_entry_and_stop_aave():
    fields = extract_signal_fields(_AAVE)
    assert fields.instrument == "AAVEUSDT"
    assert fields.direction == "SELL"
    assert fields.entry.type == "single"
    assert fields.entry.price == 159.81
    assert fields.stop_loss == 172.23


def test_collects_the_inline_target_list_under_the_profit_taking_label():
    fields = extract_signal_fields(_AAVE)
    assert fields.take_profits == [158.03, 155.37, 151.81]


# --- intent ---
def test_classifies_a_full_russian_signal_as_new_signal():
    assert attempt_extract_signal(REAL_SIGNAL).intent == "new_signal"


def test_classifies_a_russian_result_post_as_not_new_signal():
    candidate = attempt_extract_signal(REAL_RESULT)
    # result posts may lack a fresh direction; if parsed, they must not be new signals
    if candidate is not None:
        assert candidate.intent != "new_signal"
