"""Telethon session store, guarded client factory, and login flow (spec §7).

The StringSession is persisted as a bare UTF-8 string at `settings.session_path`
(the writable `/session` volume). Load/persist/guard logic is pure and unit-tested;
the interactive `login` and live `whoami` calls are verified outside automated
tests. No test authenticates against real Telegram.
"""

from pathlib import Path

from telethon import TelegramClient
from telethon.errors import PhoneCodeInvalidError, SessionPasswordNeededError
from telethon.sessions import StringSession

from verasig.config import Settings
from verasig.domain.protocols import (
    CodeInvalidError,
    PendingCode,
    TelegramSource,
    TwoFactorUnsupportedError,
)
from verasig.foundation.telethon_source import TelethonSource

_SESSION_MISSING_HINT = "run `login` first"
_CREDENTIALS_MISSING_HINT = "set VERASIG_TELEGRAM_API_ID and VERASIG_TELEGRAM_API_HASH"


class SessionMissingError(RuntimeError):
    """No usable session string was found at the configured path."""


class CredentialsMissingError(RuntimeError):
    """Telegram api_id/api_hash are required to build a client but are unset."""


def load_session_string(path: str) -> str:
    session_file = Path(path)
    if not session_file.exists():
        raise SessionMissingError(_SESSION_MISSING_HINT)
    session_string = session_file.read_text(encoding="utf-8").strip()
    if not session_string:
        raise SessionMissingError(_SESSION_MISSING_HINT)
    return session_string


def save_session_string(path: str, session_string: str) -> None:
    session_file = Path(path)
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(session_string, encoding="utf-8")


def _require_credentials(settings: Settings) -> tuple[int, str]:
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise CredentialsMissingError(_CREDENTIALS_MISSING_HINT)
    return settings.telegram_api_id, settings.telegram_api_hash


def make_client(settings: Settings) -> TelegramClient:
    api_id, api_hash = _require_credentials(settings)
    session_string = load_session_string(settings.session_path)
    return TelegramClient(StringSession(session_string), api_id, api_hash)


async def run_login(settings: Settings) -> str:
    """Interactive one-time auth; returns the session string.

    The credential guard fires before any Telegram contact. Telethon prompts
    for the login code and the 2FA password; the phone comes from config or,
    if unset, an interactive prompt.
    """
    api_id, api_hash = _require_credentials(settings)
    client = TelegramClient(StringSession(), api_id, api_hash)
    phone = settings.telegram_phone or (lambda: input("phone (e.g. +15551234567): "))
    await client.start(phone=phone)
    session_string = client.session.save()
    await client.disconnect()
    return session_string


async def fetch_account(client: TelegramClient):
    """Connect, read the logged-in account, disconnect."""
    async with client:
        return await client.get_me()


async def send_code(api_id: int, api_hash: str, phone: str) -> PendingCode:
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
        return PendingCode(
            session_string=client.session.save(),
            phone_code_hash=sent.phone_code_hash,
        )
    finally:
        await client.disconnect()


async def sign_in(
    session_string: str,
    api_id: int,
    api_hash: str,
    phone: str,
    code: str,
    phone_code_hash: str,
) -> str:
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    try:
        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        except PhoneCodeInvalidError as error:
            raise CodeInvalidError() from error
        except SessionPasswordNeededError as error:
            raise TwoFactorUnsupportedError() from error
        return client.session.save()
    finally:
        await client.disconnect()


def make_user_source(session_string: str, api_id: int, api_hash: str) -> TelegramSource:
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    return TelethonSource(client)


def _normalize_phone(phone: str) -> str:
    return phone if phone.startswith("+") else f"+{phone}"


def format_account(user) -> str:
    parts: list[str] = []
    if getattr(user, "username", None):
        parts.append(f"@{user.username}")
    name = " ".join(
        piece
        for piece in (
            getattr(user, "first_name", None),
            getattr(user, "last_name", None),
        )
        if piece
    )
    if name:
        parts.append(name)
    parts.append(f"id={user.id}")
    if getattr(user, "phone", None):
        parts.append(_normalize_phone(user.phone))
    return "logged in as " + " · ".join(parts)
