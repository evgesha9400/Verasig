"""Compatibility facade for focused storage repository modules."""

from verasig.storage.channel_repository import (
    advance_cursor,
    find_channel,
    read_cursor,
    upsert_channel,
)
from verasig.storage.deletion_repository import (
    read_deletion_evidence,
    upsert_deletion_evidence,
)
from verasig.storage.drift_repository import (
    insert_drift_warnings,
    read_drift_warnings,
    read_parser_drift_warnings,
)
from verasig.storage.event_repository import insert_signal_events, read_signal_events
from verasig.storage.message_repository import (
    candidate_message_ids,
    count_messages,
    insert_messages,
    read_message,
    read_message_page,
    read_messages,
)
from verasig.storage.outcome_repository import (
    insert_extracted_signals,
    insert_unrecognized_signals,
    read_extracted_signals,
    read_unrecognized_signals,
    record_outcome,
)
from verasig.storage.rule_repository import (
    read_filter_rules,
    read_labels,
    read_parser_rules,
    upsert_filter_rule,
    upsert_labels,
    upsert_parser_rules,
)

__all__ = [
    "advance_cursor",
    "candidate_message_ids",
    "count_messages",
    "find_channel",
    "insert_drift_warnings",
    "insert_extracted_signals",
    "insert_messages",
    "insert_signal_events",
    "insert_unrecognized_signals",
    "read_cursor",
    "read_deletion_evidence",
    "read_drift_warnings",
    "read_extracted_signals",
    "read_filter_rules",
    "read_labels",
    "read_message",
    "read_message_page",
    "read_messages",
    "read_parser_drift_warnings",
    "read_parser_rules",
    "read_signal_events",
    "read_unrecognized_signals",
    "record_outcome",
    "upsert_channel",
    "upsert_deletion_evidence",
    "upsert_filter_rule",
    "upsert_labels",
    "upsert_parser_rules",
]
