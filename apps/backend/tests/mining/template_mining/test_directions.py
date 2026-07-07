"""Parity port of ``directions.test.js``."""

from verasig.features.mining.template_mining.directions import detect_directions


def _sides(text: str) -> list[str]:
    return [entity.normalized for entity in detect_directions(text)]


# --- buy words ---
def test_detects_buy():
    assert "BUY" in _sides("XAUUSD BUY NOW")


def test_detects_long():
    assert "BUY" in _sides("GOLD LONG")


def test_detects_bullish():
    assert "BUY" in _sides("looking bullish here")


def test_detects_call():
    assert "BUY" in _sides("AAPL CALL above 210")


# --- sell words ---
def test_detects_sell():
    assert "SELL" in _sides("Sell EURUSD 1.0860")


def test_detects_short():
    assert "SELL" in _sides("ETH short hit SL")


def test_detects_bearish():
    assert "SELL" in _sides("bearish below support")


def test_detects_put():
    assert "SELL" in _sides("TSLA PUT 180")


# --- case and absence ---
def test_is_case_insensitive():
    assert "BUY" in _sides("Buy gold")


def test_returns_nothing_when_no_direction_word_or_emoji_exists():
    assert len(detect_directions("Good morning team, waiting for NY session")) == 0


def test_does_not_treat_bare_calls_prose_as_a_direction():
    assert len(detect_directions("premium leveraged calls and 1:1 mentoring")) == 0


# --- emojis are lower confidence ---
def test_reads_a_green_circle_as_buy():
    assert "BUY" in _sides("\U0001f7e2 GOLD entry 2320")


def test_reads_a_red_circle_as_sell():
    assert "SELL" in _sides("\U0001f534 EURUSD entry 1.0860")


def test_reads_arrows_as_direction():
    assert "BUY" in _sides("XAUUSD ⬆️ 2320")
    assert "SELL" in _sides("XAUUSD ⬇️ 2320")


def test_scores_an_emoji_only_direction_below_a_word_direction():
    emoji = detect_directions("\U0001f7e2")[0]
    word = detect_directions("buy")[0]
    assert emoji.confidence < word.confidence


def test_carries_the_raw_token_and_span():
    entity = detect_directions("GOLD LONG")[0]
    assert entity.raw.lower() == "long"
    assert entity.normalized == "BUY"
    assert entity.start >= 0


# --- overlay awareness ---
def test_recognises_a_custom_direction_token_at_word_strength():
    assert not any(
        h.normalized == "BUY" and h.confidence == 0.9
        for h in detect_directions("\U0001f680 entry now")
    )

    overlay = {"directionTokens": {"\U0001f680": "BUY"}}
    hits = detect_directions("\U0001f680 entry now", overlay)
    assert any(h.normalized == "BUY" and h.confidence == 0.9 for h in hits)
