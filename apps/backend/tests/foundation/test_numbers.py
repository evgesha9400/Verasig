from decimal import Decimal

import pytest

from verasig.shared.decimal_numbers import to_decimal


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("65000", Decimal("65000")),
        ("65,000", Decimal("65000")),
        ("65 000", Decimal("65000")),
        ("64000.5", Decimal("64000.5")),
        ("65k", Decimal("65000")),
        ("65K", Decimal("65000")),
        ("65К", Decimal("65000")),  # cyrillic К
        ("2m", Decimal("2000000")),
        ("2М", Decimal("2000000")),  # cyrillic М
    ],
)
def test_to_decimal_parses_numbers_commas_spaces_and_suffixes(raw, expected):
    assert to_decimal(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "abc", "k", "nan", "NaN", "inf", "-inf", "Infinity", "infinity"],
)
def test_to_decimal_returns_none_for_unparseable(raw):
    # "nan"/"inf" parse as valid Decimals but are never real prices → None.
    assert to_decimal(raw) is None
