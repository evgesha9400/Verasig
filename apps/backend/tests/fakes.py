"""In-memory TelegramSource fake for offline backfill tests.

Simulates Telegram's history: holds a fixed message set, yields it
oldest->newest in batches, can interrupt mid-stream (resume tests), and
records every `after_message_id` it was asked for (refetch assertions).
"""

from collections.abc import AsyncIterator, Callable
from datetime import datetime, timezone

from verasig.domain.channel import TelegramChannel
from verasig.domain.message import RawTelegramMessage
from verasig.domain.telegram_ports import (
    CodeInvalidError,
    PendingCode,
    TwoFactorPasswordInvalidError,
    TwoFactorUnsupportedError,
)
from verasig.foundation.market_data.static_exchange import normalize_base_symbol


def channel(channel_id: int = 7) -> TelegramChannel:
    """Canonical "Pilot Signals" channel shared by the feed/mining API tests."""
    return TelegramChannel(
        channel_id=channel_id,
        handle="pilot",
        title="Pilot Signals",
        is_private=False,
        subscriber_count=1234,
        first_seen_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )


def messages() -> list[RawTelegramMessage]:
    """Canonical three-message set (two signals + noise) for the mining tests."""
    texts = {
        1: "BTC LONG entry 100 sl 95 tp 110",
        2: "gm everyone",
        3: "ETH LONG entry 200 sl 190 tp 210",
    }
    return [
        RawTelegramMessage(
            channel_id=7,
            message_id=message_id,
            text=text,
            posted_at=datetime(2026, 6, message_id, tzinfo=timezone.utc),
            captured_at=datetime(2026, 6, message_id, tzinfo=timezone.utc),
            has_media=False,
            raw_payload={},
        )
        for message_id, text in texts.items()
    ]


class FakeStreamInterrupted(RuntimeError):
    """Raised by FakeSource to simulate a mid-backfill crash."""


class FakeTelegramAuth:
    def __init__(
        self,
        *,
        valid_code: str = "12345",
        pending_session: str = "pending-session",
        final_session: str = "final-session",
        phone_code_hash: str = "phone-code-hash",
        requires_password: bool = False,
        valid_password: str = "two-factor-password",
    ) -> None:
        self.valid_code = valid_code
        self.pending_session = pending_session
        self.final_session = final_session
        self.phone_code_hash = phone_code_hash
        self.requires_password = requires_password
        self.valid_password = valid_password
        self.sent_codes: list[tuple[int, str, str]] = []
        self.sign_ins: list[tuple[str, int, str, str, str, str, str | None]] = []

    async def send_code(self, api_id: int, api_hash: str, phone: str) -> PendingCode:
        self.sent_codes.append((api_id, api_hash, phone))
        return PendingCode(
            session_string=self.pending_session,
            phone_code_hash=self.phone_code_hash,
        )

    async def sign_in(
        self,
        session_string: str,
        api_id: int,
        api_hash: str,
        phone: str,
        code: str,
        phone_code_hash: str,
        password: str | None = None,
    ) -> str:
        self.sign_ins.append(
            (session_string, api_id, api_hash, phone, code, phone_code_hash, password)
        )
        if code != self.valid_code:
            raise CodeInvalidError()
        if self.requires_password and password is None:
            raise TwoFactorUnsupportedError()
        if self.requires_password and password != self.valid_password:
            raise TwoFactorPasswordInvalidError()
        return self.final_session


class FakeSource:
    def __init__(
        self,
        channel: TelegramChannel,
        messages: list[RawTelegramMessage],
        *,
        live_ids: set[int] | None = None,
        fail_after_batch: int | None = None,
        before_batch: Callable[[int, int], None] | None = None,
        resolve_error: Exception | None = None,
    ) -> None:
        self.channel = channel
        self.messages = sorted(messages, key=lambda message: message.message_id)
        self.live_ids = set() if live_ids is None else set(live_ids)
        self.fail_after_batch = fail_after_batch
        self.before_batch = before_batch
        self.resolve_error = resolve_error
        self.requested_afters: list[int | None] = []
        self.requested_befores: list[int | None] = []
        self.requested_sinces: list[object] = []
        self.yielded_ids: list[int] = []

    async def __aenter__(self) -> "FakeSource":
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        return None

    async def resolve_channel(self, _reference: str | int) -> TelegramChannel:
        if self.resolve_error is not None:
            raise self.resolve_error
        return self.channel

    async def fetch_older_batches(
        self,
        _channel_id: int,
        before_message_id: int | None,
        batch_size: int,
        since=None,
    ) -> AsyncIterator[list[RawTelegramMessage]]:
        # newest -> oldest, strictly below `before_message_id`, stopping at `since`
        self.requested_befores.append(before_message_id)
        self.requested_sinces.append(since)
        pending = [
            m
            for m in self.messages
            if (before_message_id is None or m.message_id < before_message_id)
            and (since is None or m.posted_at >= since)
        ]
        pending.sort(key=lambda message: message.message_id, reverse=True)
        for batch in self._emit_batches(pending, batch_size):
            yield batch

    async def fetch_newer_batches(
        self,
        _channel_id: int,
        after_message_id: int | None,
        batch_size: int,
    ) -> AsyncIterator[list[RawTelegramMessage]]:
        # newest -> oldest, strictly above `after_message_id` (REFRESH)
        self.requested_afters.append(after_message_id)
        after = after_message_id or 0
        pending = [m for m in self.messages if m.message_id > after]
        pending.sort(key=lambda message: message.message_id, reverse=True)
        for batch in self._emit_batches(pending, batch_size):
            yield batch

    def _emit_batches(self, pending, batch_size):
        yielded = 0
        for index, start in enumerate(range(0, len(pending), batch_size)):
            if self.fail_after_batch is not None and index == self.fail_after_batch:
                raise FakeStreamInterrupted
            if self.before_batch is not None:
                self.before_batch(index, yielded)
            batch = pending[start : start + batch_size]
            self.yielded_ids.extend(message.message_id for message in batch)
            yielded += len(batch)
            yield batch

    async def live_message_ids(
        self, _channel_id: int, on_progress: Callable[[int], None] | None = None
    ) -> set[int]:
        # canned live snapshot for rescan tests; reports the running count per id
        # so progress-during-rescan assertions can observe a non-silent re-fetch
        scanned = 0
        for _message_id in sorted(self.live_ids):
            scanned += 1
            if on_progress is not None:
                on_progress(scanned)
        return set(self.live_ids)

    @staticmethod
    async def live_events(_channel_ids: list[int]):
        yield None  # unused by backfill tests


class FakeExchange:
    """In-memory Exchange for offline seed-filter tests (injected symbol set)."""

    def __init__(self, symbols: set[str]) -> None:
        self._symbols = {normalize_base_symbol(symbol) for symbol in symbols}

    def base_symbols(self) -> set[str]:
        return set(self._symbols)

    def is_listed(self, token: str) -> bool:
        return normalize_base_symbol(token) in self._symbols
