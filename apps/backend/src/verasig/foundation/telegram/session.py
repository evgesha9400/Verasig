"""Per-user Telethon auth and source factory."""

from telethon import TelegramClient
from telethon.errors import (
    PasswordHashInvalidError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession

from verasig.domain.telegram_ports import (
    CodeInvalidError,
    PendingCode,
    TelegramSource,
    TwoFactorPasswordInvalidError,
    TwoFactorUnsupportedError,
)
from verasig.foundation.telegram.telethon_source import TelethonSource


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
    password: str | None = None,
) -> str:
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    try:
        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        except PhoneCodeInvalidError as error:
            raise CodeInvalidError() from error
        except SessionPasswordNeededError as error:
            if password is None:
                raise TwoFactorUnsupportedError() from error
            try:
                await client.sign_in(password=password)
            except PasswordHashInvalidError as error:
                raise TwoFactorPasswordInvalidError() from error
        return client.session.save()
    finally:
        await client.disconnect()


def make_user_source(session_string: str, api_id: int, api_hash: str) -> TelegramSource:
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    return TelethonSource(client)
