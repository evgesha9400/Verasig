"""Pure Telegram adapter seams."""

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from verasig.domain.channel import TelegramChannel
from verasig.domain.message import RawTelegramMessage
from verasig.domain.telegram import TelegramLiveEvent


@dataclass(frozen=True)
class PendingCode:
    session_string: str
    phone_code_hash: str


class CodeInvalidError(Exception):
    """Telegram rejected the submitted login code."""


class TwoFactorUnsupportedError(Exception):
    """Telegram account requires a two-factor password to continue."""


class TwoFactorPasswordInvalidError(Exception):
    """Telegram rejected the two-factor password."""


@runtime_checkable
class TelegramAuth(Protocol):
    async def send_code(
        self, api_id: int, api_hash: str, phone: str
    ) -> PendingCode: ...

    async def sign_in(
        self,
        session_string: str,
        api_id: int,
        api_hash: str,
        phone: str,
        code: str,
        phone_code_hash: str,
        password: str | None = None,
    ) -> str: ...


@runtime_checkable
class TelegramSource(Protocol):
    async def resolve_channel(self, reference: str | int) -> TelegramChannel: ...

    def backfill_batches(
        self, channel_id: int, after_message_id: int | None, batch_size: int
    ) -> AsyncIterator[list[RawTelegramMessage]]: ...

    async def live_message_ids(
        self, channel_id: int, on_progress: Callable[[int], None] | None = None
    ) -> set[int]: ...

    def live_events(
        self, channel_ids: list[int]
    ) -> AsyncIterator[TelegramLiveEvent]: ...
