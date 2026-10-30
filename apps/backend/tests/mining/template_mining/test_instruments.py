"""Parity port of ``instruments.test.js``."""

from verasig.features.mining.template_mining.instruments import detect_instruments


def _normals(text: str) -> list[str]:
    return [entity.normalized for entity in detect_instruments(text)]


# --- direct symbols ---
def test_detects_a_metal_symbol():
    assert "XAUUSD" in _normals("XAUUSD BUY NOW")


def test_detects_a_forex_pair_by_known_currency_codes():
    assert "EURUSD" in _normals("Sell EURUSD 1.0860")


def test_detects_a_cross_pair_like_gbpjpy():
    assert "GBPJPY" in _normals("GBPJPY short @ 192.50")


def test_detects_an_index_symbol():
    assert "NAS100" in _normals("NAS100 SELL ZONE 19800-19850")


def test_detects_a_stock_ticker():
    assert "AAPL" in _normals("AAPL CALL above 210")


# --- alias normalization ---
def test_maps_gold_to_xauusd():
    assert "XAUUSD" in _normals("GOLD LONG")


def test_maps_xau_to_xauusd():
    assert "XAUUSD" in _normals("XAU buy")


def test_maps_bitcoin_and_btc_to_btcusdt():
    assert "BTCUSDT" in _normals("BITCOIN long")
    assert "BTCUSDT" in _normals("BTC long now")


def test_maps_ethereum_and_eth_to_ethusdt():
    assert "ETHUSDT" in _normals("ETHEREUM short")
    assert "ETHUSDT" in _normals("ETH short hit SL")


def test_maps_nasdaq_and_us100_to_nas100():
    assert "NAS100" in _normals("NASDAQ buy")
    assert "NAS100" in _normals("US100 buy")


def test_maps_dow_to_us30_and_dax_to_ger40():
    assert "US30" in _normals("DOW buy now")
    assert "GER40" in _normals("DAX sell")


def test_maps_sp500_and_snp500_to_spx500():
    assert "SPX500" in _normals("SP500 long")
    assert "SPX500" in _normals("S&P500 long")


# --- crypto pair formats ---
def test_detects_slash_pairs_and_normalizes_to_a_joined_symbol():
    assert "BTCUSDT" in _normals("LONG BTC/USDT")
    assert "ETHUSDT" in _normals("SHORT ETH/USDT")


def test_detects_an_arbitrary_slash_pair_not_in_the_dictionary():
    assert "ARBUSDT" in _normals("SCALP ARB/USDT long 1.124")


def test_splits_a_slash_less_concatenated_pair_into_base_and_quote():
    assert "LINKUSDT" in _normals("LINKUSDT long")


# --- guards ---
def test_does_not_treat_ordinary_six_letter_word_as_a_forex_pair():
    assert len(detect_instruments("MARKET orders only please")) == 0


def test_does_not_match_instrument_substring_inside_a_larger_word():
    assert len(detect_instruments("the solution is golden")) == 0


def test_returns_empty_for_text_with_no_instrument():
    assert len(detect_instruments("Good morning team, waiting for NY session")) == 0


def test_returns_entities_carrying_raw_match_and_positive_confidence():
    entity = detect_instruments("GOLD LONG")[0]
    assert entity.raw.lower() == "gold"
    assert entity.normalized == "XAUUSD"
    assert entity.confidence > 0


def test_deduplicates_repeated_instruments_to_one_entity_per_symbol():
    result = detect_instruments("BTC long, still bullish on BTC")
    assert len([e for e in result if e.normalized == "BTCUSDT"]) == 1


# --- overlay awareness ---
def test_recognises_a_custom_alias_from_the_overlay():
    without = detect_instruments("АПТ long here")
    assert not any(h.normalized == "APTUSDT" for h in without)

    overlay = {"instrumentAliases": {"АПТ": "APTUSDT"}}
    hits = detect_instruments("АПТ long here", overlay)
    assert any(h.normalized == "APTUSDT" for h in hits)


# --- concatenated pairs and word-like tickers ---
def test_accepts_a_concatenated_pair_with_an_unlisted_base():
    assert _normals("LDOUSDT long") == ["LDOUSDT"]


def test_accepts_digits_in_a_concatenated_base():
    assert _normals("1000PEPEUSDT short") == ["1000PEPEUSDT"]
    assert _normals("1INCHUSDT long") == ["1INCHUSDT"]


def test_keeps_a_concatenated_crypto_quote_verbatim():
    assert _normals("ETHBTC long") == ["ETHBTC"]
    assert _normals("ETHUSDC long") == ["ETHUSDC"]


def test_does_not_read_english_words_as_tickers():
    assert _normals("DO NOT BUY NOW") == []
    assert _normals("Link pinned above") == []
    assert _normals("OP NEAR LINK") == []


def test_reads_a_word_like_ticker_with_a_prefix_quote_or_coin_label():
    assert _normals("$NOT long") == ["NOTUSDT"]
    assert _normals("#OP short") == ["OPUSDT"]
    assert _normals("NEARUSDT long") == ["NEARUSDT"]
    assert _normals("Монета: LINK") == ["LINKUSDT"]


def test_does_not_read_an_english_word_ending_in_eth_as_a_pair():
    assert _normals("TEETH LONG") == []
    assert _normals("SEE YOU ON THE TWENTIETH") == []
