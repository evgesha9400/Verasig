"""Backfill progress presentation carries a coarse `stage` (backfill_job_run.py).

The frontend drives its stage strip off `stage` (secure/capture/index/rescan)
instead of parsing phase strings. Pure mapping, one place.
"""

from uuid import UUID

from verasig.features.feeds.backfill_job_run import BackfillProgress, present_progress

_JOB_ID = UUID("11111111-1111-1111-1111-111111111111")


def _progress(phase: str) -> dict:
    return present_progress(
        BackfillProgress(
            job_id=_JOB_ID,
            status="running",
            phase=phase,
            fetched=0,
            oldest_posted_at=None,
            cursor_message_id=None,
        )
    )


def test_capture_phases_map_to_capture_stage():
    assert _progress("Opening MTProto session...")["stage"] == "capture"
    assert _progress("Reading channel history...")["stage"] == "capture"
    assert _progress("Re-capturing history...")["stage"] == "capture"


def test_indexing_phase_maps_to_index_stage():
    assert _progress("Indexing message bodies...")["stage"] == "index"


def test_deletion_scan_phases_map_to_rescan_stage():
    assert _progress("Checking deleted messages...")["stage"] == "rescan"
    assert _progress("Checking deleted messages... (200 scanned)")["stage"] == "rescan"


def test_securing_evidence_phase_maps_to_secure_stage():
    assert _progress("Securing deletion evidence...")["stage"] == "secure"
