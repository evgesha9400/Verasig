from verasig.config import Settings


def test_telegram_phone_loads_from_env(monkeypatch):
    monkeypatch.setenv("VERASIG_TELEGRAM_PHONE", "+15551234567")
    assert Settings().telegram_phone == "+15551234567"


def test_telegram_phone_defaults_to_none():
    assert Settings(_env_file=None).telegram_phone is None


def test_backfill_batch_size_defaults_to_200():
    assert Settings(_env_file=None).backfill_batch_size == 200


def test_backfill_batch_size_loads_from_env(monkeypatch):
    monkeypatch.setenv("VERASIG_BACKFILL_BATCH_SIZE", "50")
    assert Settings().backfill_batch_size == 50


def test_distiller_command_defaults_to_claude():
    assert Settings(_env_file=None).distiller_command == "claude"


def test_distiller_command_loads_from_env(monkeypatch):
    monkeypatch.setenv("VERASIG_DISTILLER_COMMAND", "codex")
    assert Settings().distiller_command == "codex"
