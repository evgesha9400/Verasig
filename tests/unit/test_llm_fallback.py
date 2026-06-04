from decimal import Decimal
from pathlib import Path

from fakes import FakeExtractor

from verasig.domain.signal import Side, TradeIntent
from verasig.services.extraction.llm_fallback import (
    ClaudeCliExtractor,
    LlmExtractor,
    parse_extractor_output,
)

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "cli"
_PILOT = (_FIXTURES / "extract_pilot.txt").read_text(encoding="utf-8")
_MISS = (_FIXTURES / "extract_miss.txt").read_text(encoding="utf-8")


def test_parse_extractor_output_builds_trade_intent_from_fenced_json():
    intent = parse_extractor_output(_PILOT)
    assert isinstance(intent, TradeIntent)
    assert (intent.symbol, intent.side) == ("BTCUSDT", Side.LONG)
    assert intent.stop_loss == Decimal("64000")
    assert intent.take_profits == [Decimal("67000"), Decimal("68000")]


def test_parse_extractor_output_returns_none_when_no_json():
    assert parse_extractor_output(_MISS) is None


def test_parse_extractor_output_returns_none_on_invalid_json():
    assert parse_extractor_output("{not valid json}") is None


def test_parse_extractor_output_returns_none_when_symbol_side_missing():
    assert parse_extractor_output('{"entry_low": "100"}') is None


def test_parse_extractor_output_uppercases_side_and_normalizes_symbol():
    intent = parse_extractor_output('{"symbol": "eth", "side": "short"}')
    assert intent.side is Side.SHORT
    assert intent.symbol == "ETHUSDT"


def test_parse_extractor_output_drops_unknown_keys():
    intent = parse_extractor_output('{"symbol": "BTC", "side": "LONG", "hacked": "x"}')
    assert isinstance(intent, TradeIntent)


def test_claude_cli_extractor_satisfies_protocol():
    assert isinstance(ClaudeCliExtractor(), LlmExtractor)


def test_claude_cli_extractor_wires_runner_without_real_cli():
    prompts: list[str] = []

    def fake_runner(prompt: str) -> str:
        prompts.append(prompt)
        return _PILOT

    extractor = ClaudeCliExtractor(runner=fake_runner)
    intent = extractor.extract("BTC long entry 65000 sl 64000 tp 67000 68000")
    assert isinstance(intent, TradeIntent) and intent.symbol == "BTCUSDT"
    assert len(prompts) == 1  # one extraction call; no real CLI
    assert "BTC long entry 65000" in prompts[0]  # candidate text reaches the prompt


def test_fake_extractor_returns_canned_intent_and_counts_calls():
    intent = TradeIntent(symbol="BTC", side=Side.LONG)
    fake = FakeExtractor(returns=intent)
    assert isinstance(fake, LlmExtractor)
    assert fake.extract("anything") is intent
    assert fake.calls == 1
