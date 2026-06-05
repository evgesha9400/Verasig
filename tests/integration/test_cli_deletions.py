"""Offline `deletions` reader (ADR 0008).

Seeds evidence via the repo, then drives `verasig deletions <ref>` with the
CliRunner — no Telegram, no rescan. Asserts signal-confirmed deletions show with
their original text, chatter-confirmed deletions are hidden, and suspected gaps
are summarised; an unknown channel exits non-zero.
"""

from datetime import datetime, timezone

from typer.testing import CliRunner

from verasig.cli import app
from verasig.domain.channel import TelegramChannel
from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.storage import repositories as repo

runner = CliRunner()

_CHANNEL_ID = 7
_FIRST = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
_DETECTED = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)


def _confirmed(message_id: int, text: str, *, candidate: bool) -> DeletedSignalEvidence:
    return DeletedSignalEvidence(
        channel_id=_CHANNEL_ID,
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
        channel_id=_CHANNEL_ID,
        message_id=message_id,
        confidence=DeletionConfidence.SUSPECTED,
        method=DeletionMethod.ID_GAP,
        detected_at=_DETECTED,
        was_signal_candidate=False,
    )


def _seed_evidence(session_factory) -> None:
    with session_factory() as session:
        repo.upsert_channel(
            session,
            TelegramChannel(
                channel_id=_CHANNEL_ID,
                handle="pilot",
                title="Pilot",
                is_private=False,
                first_seen_at=_FIRST,
            ),
        )
        repo.upsert_deletion_evidence(
            session,
            [
                _confirmed(2, "BTC long 65k erased", candidate=True),
                _confirmed(3, "gm frens chatter", candidate=False),
                _suspected(4),
            ],
        )
        session.commit()


def test_deletions_cli_shows_signals_hides_chatter_counts_gaps(
    session_factory, monkeypatch, pg_url
):
    _seed_evidence(session_factory)
    monkeypatch.setenv("VERASIG_DATABASE_URL", pg_url)
    result = runner.invoke(app, ["deletions", "@pilot"])
    assert result.exit_code == 0
    output = result.output
    assert "Pilot" in output and "id=7" in output
    assert '#2 2026-06-01T12:00Z "BTC long 65k erased"' in output  # signal shown
    assert "gm frens chatter" not in output  # chatter hidden
    assert "SUSPECTED gaps: 1" in output


def test_deletions_cli_unknown_channel_exits_nonzero(monkeypatch, pg_url):
    monkeypatch.setenv("VERASIG_DATABASE_URL", pg_url)
    result = runner.invoke(app, ["deletions", "@ghost"])
    assert result.exit_code == 1
