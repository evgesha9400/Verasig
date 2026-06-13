from fakes import FakeExchange

from verasig.domain.market_ports import Exchange
from verasig.foundation.market_data.static_exchange import StaticExchange


def test_static_exchange_lists_major_base_coins():
    exchange = StaticExchange()
    assert {"BTC", "ETH", "SOL"} <= exchange.base_symbols()


def test_static_exchange_is_listed_normalizes_dollar_suffix_and_case():
    exchange = StaticExchange()
    assert exchange.is_listed("BTC")
    assert exchange.is_listed("$BTC")
    assert exchange.is_listed("btc")
    assert exchange.is_listed("BTCUSDT")
    assert exchange.is_listed("ETH/USDT")


def test_static_exchange_rejects_non_symbol_tokens():
    exchange = StaticExchange()
    assert not exchange.is_listed("LONG")
    assert not exchange.is_listed("gm")
    assert not exchange.is_listed("USDT")


def test_static_exchange_satisfies_protocol():
    assert isinstance(StaticExchange(), Exchange)


def test_fake_exchange_satisfies_protocol_and_honours_injected_symbols():
    exchange = FakeExchange({"BTC", "ETH"})
    assert isinstance(exchange, Exchange)
    assert exchange.is_listed("$BTC")
    assert not exchange.is_listed("DOGE")
