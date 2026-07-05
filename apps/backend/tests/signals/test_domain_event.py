from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from verasig.domain.event import MatchReason, MaterializationPath, RawSignalEvent


def _event(**overrides) -> RawSignalEvent:
    base = {
        "channel_id": 1,
        "message_id": 2,
        "candidate_text": "BTC long entry 65k",
        "materialized_by": MaterializationPath.SEED_HEURISTIC,
    }
    base.update(overrides)
    return RawSignalEvent(**base)


def test_event_constructs_with_required_fields_and_defaults():
    event = _event()
    assert (event.channel_id, event.message_id) == (1, 2)
    assert event.candidate_text == "BTC long entry 65k"
    assert event.materialized_by is MaterializationPath.SEED_HEURISTIC
    assert isinstance(event.id, UUID)
    assert event.matched_reasons == []
    assert isinstance(event.created_at, datetime)


def test_event_records_matched_reasons_as_a_list():
    event = _event(
        matched_reasons=[MatchReason.DIRECTIONAL_KEYWORD, MatchReason.SYMBOL_TOKEN]
    )
    assert event.matched_reasons == [
        MatchReason.DIRECTIONAL_KEYWORD,
        MatchReason.SYMBOL_TOKEN,
    ]


def test_event_rejects_missing_candidate_text():
    with pytest.raises(ValidationError):
        RawSignalEvent(
            channel_id=1,
            message_id=2,
            materialized_by=MaterializationPath.SEED_HEURISTIC,
        )


def test_match_reason_has_the_three_seed_heuristics():
    assert {reason.value for reason in MatchReason} == {
        "DIRECTIONAL_KEYWORD",
        "SYMBOL_TOKEN",
        "PRICE_SHAPED",
    }


def test_materialization_path_has_the_provenance_values():
    assert {path.value for path in MaterializationPath} == {
        "SEED_HEURISTIC",
        "FILTER_RULE",
        "PARSER_BACKFILL",
        "HUMAN_AUDIT",
        "MINING",
    }
