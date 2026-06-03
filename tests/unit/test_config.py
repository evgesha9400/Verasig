from verasig.config import Settings


def test_telegram_phone_loads_from_env(monkeypatch):
    monkeypatch.setenv("VERASIG_TELEGRAM_PHONE", "+15551234567")
    assert Settings().telegram_phone == "+15551234567"


def test_telegram_phone_defaults_to_none():
    assert Settings(_env_file=None).telegram_phone is None
