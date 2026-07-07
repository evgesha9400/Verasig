"""Parity port of ``template.test.js``."""

from verasig.features.rules.template_mining.template import (
    hash_string,
    normalize_template,
)


def _template_of(text: str) -> str:
    return normalize_template(
        {"message": {"id": "t", "text": text}}
    ).normalized_template


# --- matches the specified canonical forms ---
def test_normalizes_an_emoji_range_numbered_tp_signal():
    text = "\U0001f7e2 XAUUSD BUY\nEntry: 2320-2325\nSL: 2312\nTP1: 2340\nTP2: 2355"
    assert _template_of(text) == (
        "<SIDE_EMOJI> <INSTRUMENT> <SIDE>\nENTRY <RANGE>\n"
        "SL <PRICE>\nTP1 <PRICE>\nTP2 <PRICE>"
    )


def test_normalizes_a_market_order_with_a_target_list():
    text = "Gold long now\nStop below 2312\nTargets 2340 / 2355"
    assert _template_of(text) == (
        "<INSTRUMENT> <SIDE> MARKET\nSTOP BELOW <PRICE>\nTARGETS <PRICE_LIST>"
    )


def test_normalizes_an_at_entry_signal():
    text = "SELL EURUSD @ 1.0860\nSL 1.0900\nTP 1.0800"
    assert _template_of(text) == (
        "<SIDE> <INSTRUMENT> @ <PRICE>\nSL <PRICE>\nTP <PRICE>"
    )


def test_collapses_a_bare_hit_tp_update_to_a_structural_template():
    assert _template_of("XAUUSD BUY hit TP1") == "<INSTRUMENT> <SIDE> HIT TP<N>"


def test_does_not_corrupt_a_multi_digit_ordinal():
    assert _template_of("XAUUSD BUY hit TP10") == "<INSTRUMENT> <SIDE> HIT TP<N>"
    assert "TP10 <PRICE>" in _template_of("XAUUSD BUY\nTP10: 2340")


# --- grouping behaviour ---
def test_produces_the_same_template_for_structurally_identical_signals():
    a = normalize_template(
        {
            "message": {
                "text": "\U0001f7e2 XAUUSD BUY\nEntry: 2320-2325\n"
                "SL: 2312\nTP1: 2340\nTP2: 2355"
            }
        }
    )
    b = normalize_template(
        {
            "message": {
                "text": "\U0001f534 BTCUSDT SELL\nEntry: 68200-68400\n"
                "SL: 69000\nTP1: 67000\nTP2: 66000"
            }
        }
    )
    assert a.normalized_template == b.normalized_template
    assert a.template_key == b.template_key


def test_combines_redundant_limit_order_text_and_target_count_variants():
    multi_target = normalize_template(
        {
            "message": {
                "text": (
                    "\U0001fa99 МОНЕТА: #AAVE/USDT\n"
                    "\U0001f4c9\U0001f4c8 ПОКУПКА: SHORT\n"
                    "ПЛЕЧО: 18х\n"
                    "ВХОД: 159.81$\n"
                    "ФИКСИРУЕМ ПРИБЫЛЬ НА: 158.03$, 155.37$, 151.81$\n"
                    "СТОП: 172.23$"
                )
            }
        }
    )
    single_target = normalize_template(
        {
            "message": {
                "text": (
                    "\U0001fa99 МОНЕТА: #AAVE/USDT\n"
                    "\U0001f4c9\U0001f4c8 ПОКУПКА: SHORT LIMIT ORDER\n"
                    "ПЛЕЧО: 18х\n"
                    "ВХОД: 159.81$\n"
                    "ФИКСИРУЕМ ПРИБЫЛЬ НА: 158.03$\n"
                    "СТОП: 172.23$"
                )
            }
        }
    )
    assert single_target.normalized_template == multi_target.normalized_template
    assert single_target.template_key == multi_target.template_key


def test_produces_a_different_template_key_for_a_different_structure():
    a = normalize_template({"message": {"text": "BUY XAUUSD NOW\nSL 2312\nTP 2340"}})
    b = normalize_template(
        {"message": {"text": "SELL EURUSD @ 1.0860\nSL 1.0900\nTP 1.0800"}}
    )
    assert a.template_key != b.template_key


def test_returns_a_stable_non_empty_key_for_the_same_input():
    text = "BUY XAUUSD NOW\nSL 2312\nTP 2340"
    first = normalize_template({"message": {"text": text}})
    second = normalize_template({"message": {"text": text}})
    assert first.template_key == second.template_key
    assert len(first.template_key) > 0


def test_hash_string_matches_js_charcodeat_for_astral_chars():
    # JS charCodeAt iterates UTF-16 code units; hash_string must mirror that so an
    # astral char hashes identically on both sides (independent UTF-16 reference).
    text = "𝕏BTC"
    units = [
        int.from_bytes(text.encode("utf-16-le")[i : i + 2], "little")
        for i in range(0, len(text.encode("utf-16-le")), 2)
    ]
    h = 0
    for unit in units:
        h = (h * 31 + unit) & 0xFFFFFFFF
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    expected = "0"
    if h:
        expected = ""
        n = h
        while n:
            expected = digits[n % 36] + expected
            n //= 36
    assert hash_string(text) == expected
    assert hash_string(text) != hash_string("BTC")  # the astral char contributes
