import asyncio
from types import SimpleNamespace

import pytest

from verasig.config import Settings
from verasig.foundation.telegram_session import (
    CredentialsMissingError,
    SessionMissingError,
    format_account,
    load_session_string,
    make_client,
    run_login,
    save_session_string,
)


def _user(**overrides):
    base = {
        "id": 12345,
        "username": "signal_operator",
        "first_name": "Jane",
        "last_name": "Doe",
        "phone": "15551234567",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


FAKE_SESSION = "1AaBbCc-fake-string-session-not-a-real-credential"


def _settings(tmp_path, **overrides):
    base = {
        "telegram_api_id": None,
        "telegram_api_hash": None,
        "session_path": str(tmp_path / "telegram.session"),
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)


def test_save_then_load_round_trips(tmp_path):
    path = str(tmp_path / "telegram.session")
    save_session_string(path, FAKE_SESSION)
    assert load_session_string(path) == FAKE_SESSION


def test_save_creates_missing_parent_dirs(tmp_path):
    path = str(tmp_path / "session" / "telegram.session")
    save_session_string(path, FAKE_SESSION)
    assert load_session_string(path) == FAKE_SESSION


def test_load_missing_file_raises_session_missing(tmp_path):
    with pytest.raises(SessionMissingError, match="run `login` first"):
        load_session_string(str(tmp_path / "absent.session"))


def test_load_blank_file_raises_session_missing(tmp_path):
    path = tmp_path / "blank.session"
    path.write_text("   \n")
    with pytest.raises(SessionMissingError, match="run `login` first"):
        load_session_string(str(path))


def test_make_client_without_credentials_raises_credentials_missing(tmp_path):
    with pytest.raises(CredentialsMissingError, match="VERASIG_TELEGRAM_API_ID"):
        make_client(_settings(tmp_path))


def test_make_client_checks_credentials_before_session(tmp_path):
    # creds present but session absent -> creds guard passes, session guard fires
    with pytest.raises(SessionMissingError, match="run `login` first"):
        make_client(_settings(tmp_path, telegram_api_id=1, telegram_api_hash="abc"))


def test_format_account_renders_all_fields_with_phone():
    assert (
        format_account(_user())
        == "logged in as @signal_operator · Jane Doe · id=12345 · +15551234567"
    )


def test_format_account_omits_missing_username():
    assert (
        format_account(_user(username=None))
        == "logged in as Jane Doe · id=12345 · +15551234567"
    )


def test_format_account_omits_missing_last_name():
    assert (
        format_account(_user(last_name=None))
        == "logged in as @signal_operator · Jane · id=12345 · +15551234567"
    )


def test_format_account_omits_missing_phone():
    assert (
        format_account(_user(phone=None))
        == "logged in as @signal_operator · Jane Doe · id=12345"
    )


def test_format_account_keeps_existing_plus_prefix_on_phone():
    assert format_account(_user(phone="+15551234567")).endswith("· +15551234567")


def test_run_login_without_credentials_fails_fast_offline(tmp_path):
    # guard fires before any Telegram contact, so this is safe to run offline
    with pytest.raises(CredentialsMissingError, match="VERASIG_TELEGRAM_API_ID"):
        asyncio.run(run_login(_settings(tmp_path)))
