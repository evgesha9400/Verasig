"""Pure deletion formatter (cli.format_deletions; ADR 0008).

Displays only signal-CONFIRMED deletions (with #id, date, original text) plus a
per-channel SUSPECTED-gap count; chatter-confirmed deletions (stored for audit)
are hidden — the "chatter affects nothing" rule is enforced at display.
"""

from datetime import datetime, timezone

from verasig.cli import format_deletions
from verasig.domain.channel import TelegramChannel
from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)

_FIRST = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
_DETECTED = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)


def _channel() -> TelegramChannel:
    return TelegramChannel(
        channel_id=7,
        handle="pilot",
        title="Pilot",
        is_private=False,
        first_seen_at=_FIRST,
    )


def _confirmed(message_id: int, text: str, *, candidate: bool) -> DeletedSignalEvidence:
    return DeletedSignalEvidence(
        channel_id=7,
        message_id=message_id,
        confidence=DeletionConfidence.CONFIRMED,
        method=DeletionMethod.SNAPSHOT_DIFF,
        original_text=text,
        first_seen_at=_FIRST,
        detected_at=_DETECTED,
        was_signal_candidate=candidate,
    )


def _suspected(message_id: int) -> DeletedSignalEvidence:
    return DeletedSignalEvidence(
        channel_id=7,
        message_id=message_id,
        confidence=DeletionConfidence.SUSPECTED,
        method=DeletionMethod.ID_GAP,
        detected_at=_DETECTED,
        was_signal_candidate=False,
    )


def _evidence() -> list[DeletedSignalEvidence]:
    return [
        _confirmed(2, "BTC long 65k", candidate=True),
        _confirmed(3, "gm frens chatter", candidate=False),
        _suspected(4),
        _suspected(9),
    ]


def test_header_carries_channel_identity():
    header = format_deletions(_channel(), _evidence()).splitlines()[0]
    assert "Pilot" in header
    assert "@pilot" in header
    assert "id=7" in header


def test_signal_confirmed_deletion_shows_id_date_and_text():
    output = format_deletions(_channel(), _evidence())
    assert '#2 2026-06-01T12:00Z "BTC long 65k"' in output


def test_chatter_confirmed_deletion_is_hidden():
    output = format_deletions(_channel(), _evidence())
    assert "gm frens chatter" not in output
    assert "#3" not in output


def test_suspected_gaps_are_summarised_per_channel():
    footer = format_deletions(_channel(), _evidence()).splitlines()[-1]
    assert footer == "SUSPECTED gaps: 2"


def test_no_deletions_still_prints_header_and_zero_gaps():
    output = format_deletions(_channel(), [])
    assert output.splitlines()[0].startswith("Pilot")
    assert output.splitlines()[-1] == "SUSPECTED gaps: 0"
