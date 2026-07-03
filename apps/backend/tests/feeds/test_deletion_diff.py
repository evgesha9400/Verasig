"""Pure deletion detector (features/sources/deletion_diff.py; ADR 0008).

`detect_deletions` diffs the durable STORED message set against a fresh LIVE
re-fetch over `range = [min..max]` of `stored ∪ live`:
- CONFIRMED / SNAPSHOT_DIFF = `stored − live` — we captured it, it is gone now
  (original text + first_seen_at retained).
- SUSPECTED / ID_GAP = `range − stored − live` — absent from both snapshots
  (never captured, now gone; no content).
A still-present id sits in `live` and is therefore never flagged. Crafted id
sets only — zero Telegram / network.
"""

from datetime import datetime, timezone

from verasig.domain.deletion import DeletionConfidence, DeletionMethod
from verasig.domain.message import RawTelegramMessage
from verasig.features.feeds.deletion_diff import detect_deletions

_DETECTED_AT = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)


def _seen_at(message_id: int) -> datetime:
    return datetime(2026, 6, 1, 12, message_id, tzinfo=timezone.utc)


def _message(message_id: int, text: str) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=7,
        message_id=message_id,
        text=text,
        posted_at=_seen_at(message_id),
        captured_at=_seen_at(message_id),
        has_media=False,
        raw_payload={},
    )


def _detect(stored, live_ids, candidate_ids):
    return detect_deletions(
        channel_id=7,
        stored=stored,
        live_message_ids=live_ids,
        candidate_message_ids=candidate_ids,
        detected_at=_DETECTED_AT,
    )


def test_captured_then_absent_signal_is_confirmed_with_original_text():
    stored = [_message(1, "first"), _message(2, "BTC long 65k"), _message(3, "third")]
    evidence = _detect(stored, live_ids={1, 3}, candidate_ids={2})
    assert len(evidence) == 1
    gone = evidence[0]
    assert (gone.channel_id, gone.message_id) == (7, 2)
    assert gone.confidence is DeletionConfidence.CONFIRMED
    assert gone.method is DeletionMethod.SNAPSHOT_DIFF
    assert gone.original_text == "BTC long 65k"
    assert gone.first_seen_at == _seen_at(2)
    assert gone.was_signal_candidate is True
    assert gone.detected_at == _DETECTED_AT


def test_gap_absent_from_both_is_suspected_without_content():
    stored = [_message(1, "first"), _message(4, "fourth")]
    evidence = _detect(stored, live_ids={1, 4}, candidate_ids=set())
    assert {item.message_id for item in evidence} == {2, 3}
    for gap in evidence:
        assert gap.confidence is DeletionConfidence.SUSPECTED
        assert gap.method is DeletionMethod.ID_GAP
        assert gap.original_text is None
        assert gap.first_seen_at is None
        assert gap.was_signal_candidate is False
        assert gap.detected_at == _DETECTED_AT


def test_gap_below_oldest_stored_message_is_not_suspected():
    # depth-limited capture starts at id 5; id 1 is still live but below our
    # capture floor, so the 2-4 slots are pre-window and must NOT be SUSPECTED
    stored = [_message(5, "fifth"), _message(6, "sixth")]
    evidence = _detect(stored, live_ids={1, 5, 6}, candidate_ids=set())
    assert evidence == []


def test_still_present_id_is_never_flagged_even_if_never_captured():
    # id 3 is live (present now) though never captured; only id 2 (in neither) flags
    evidence = _detect([_message(1, "first")], live_ids={1, 3}, candidate_ids=set())
    assert {item.message_id for item in evidence} == {2}
    assert evidence[0].confidence is DeletionConfidence.SUSPECTED


def test_contiguous_all_live_yields_no_evidence():
    stored = [_message(1, "a"), _message(2, "b"), _message(3, "c")]
    assert _detect(stored, live_ids={1, 2, 3}, candidate_ids=set()) == []


def test_empty_universe_yields_no_evidence():
    assert _detect(stored=[], live_ids=set(), candidate_ids=set()) == []


def test_confirmed_chatter_is_stored_but_not_a_candidate():
    stored = [_message(1, "gm frens"), _message(2, "still here")]
    evidence = _detect(stored, live_ids={2}, candidate_ids=set())
    assert len(evidence) == 1
    assert (evidence[0].message_id, evidence[0].original_text) == (1, "gm frens")
    assert evidence[0].confidence is DeletionConfidence.CONFIRMED
    assert evidence[0].was_signal_candidate is False
