from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

from typer.testing import CliRunner

from verasig.cli import app
from verasig.domain.channel import TelegramChannel
from verasig.domain.message import DeliveryMode, RawTelegramMessage
from verasig.domain.telegram import TelegramDeliveryEvent, TelegramLiveEvent
from verasig.storage import repositories as repo

runner = CliRunner()

_CHANNEL_ID = 7
_POSTED = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


class FakeClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class FakeLiveSource:
    def __init__(self, events: list[TelegramLiveEvent]) -> None:
        self.events = events
        self.resolved_references: list[str | int] = []
        self.requested_channel_ids: list[list[int]] = []

    async def resolve_channel(self, reference: str | int) -> TelegramChannel:
        self.resolved_references.append(reference)
        return TelegramChannel(
            channel_id=_CHANNEL_ID,
            handle="pilot",
            title="Pilot",
            is_private=False,
            first_seen_at=_POSTED,
        )

    def live_events(self, channel_ids: list[int]) -> AsyncIterator[TelegramLiveEvent]:
        async def _events() -> AsyncIterator[TelegramLiveEvent]:
            self.requested_channel_ids.append(channel_ids)
            for event in self.events:
                yield event

        return _events()


def _delivery() -> TelegramDeliveryEvent:
    captured_at = _POSTED + timedelta(seconds=1)
    return TelegramDeliveryEvent(
        message=RawTelegramMessage(
            channel_id=_CHANNEL_ID,
            message_id=10,
            text="BTC long 65000",
            posted_at=_POSTED,
            captured_at=captured_at,
            has_media=False,
            raw_payload={"id": 10},
        ),
        mode=DeliveryMode.PUSH,
        captured_at=captured_at,
        gap_closed=False,
    )


def test_live_cli_wires_source_session_and_persists_message(
    session_factory, monkeypatch, pg_url
):
    source = FakeLiveSource([_delivery()])
    monkeypatch.setenv("VERASIG_DATABASE_URL_OVERRIDE", pg_url)
    monkeypatch.setattr("verasig.cli.make_client", lambda settings: FakeClient())
    monkeypatch.setattr("verasig.cli._make_live_source", lambda client: source)

    result = runner.invoke(app, ["live", "@pilot"])

    assert result.exit_code == 0
    assert "live: channels=7 · +1 captured · duplicates=0 · deleted=0" in result.output
    assert source.resolved_references == ["@pilot"]
    assert source.requested_channel_ids == [[_CHANNEL_ID]]
    with session_factory() as session:
        assert repo.count_messages(session, _CHANNEL_ID) == 1
