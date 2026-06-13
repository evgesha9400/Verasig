from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.features.sources import deletion_repository

_CHANNEL_ID = 7
_USER_ID = UUID("80000000-0000-0000-0000-000000000001")
_NOW = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)


def _insert_account(session) -> None:
    session.execute(
        text(
            """
            INSERT INTO user_account
                (id, email, password_hash, first_name, last_name, plan, created_at)
            VALUES
                (:id, 'hardening@example.com', 'hash', 'Ada', 'Lovelace',
                 'observer', :now)
            """
        ),
        {"id": _USER_ID, "now": _NOW},
    )


def _insert_channel(session) -> None:
    session.execute(
        text(
            """
            INSERT INTO telegram_channel
                (channel_id, title, is_private, first_seen_at)
            VALUES
                (:channel_id, 'Pilot', false, :now)
            """
        ),
        {"channel_id": _CHANNEL_ID, "now": _NOW},
    )


def _insert_captured_message(session, message_id: int) -> None:
    session.execute(
        text(
            """
            INSERT INTO raw_telegram_message
                (channel_id, message_id, text, posted_at, captured_at,
                 has_media, raw_payload)
            VALUES
                (:channel_id, :message_id, 'BTC long', :now, :now,
                 false, CAST(:payload AS jsonb))
            """
        ),
        {
            "channel_id": _CHANNEL_ID,
            "message_id": message_id,
            "now": _NOW,
            "payload": '{"id": 1}',
        },
    )


def test_null_user_id_insert_fails_at_db_level(db_session):
    _insert_channel(db_session)
    _insert_captured_message(db_session, 1)
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO golden_label
                    (id, user_id, channel_id, message_id, label, labeled_at)
                VALUES
                    (:id, NULL, :channel_id, 1, 'signal', :now)
                """
            ),
            {"id": uuid4(), "channel_id": _CHANNEL_ID, "now": _NOW},
        )


def test_invalid_enum_string_fails_at_db_level(db_session):
    _insert_channel(db_session)
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO deleted_signal_evidence
                    (id, channel_id, message_id, confidence, method, detected_at,
                     was_signal_candidate)
                VALUES
                    (:id, :channel_id, 99, 'MAYBE', 'ID_GAP', :now, false)
                """
            ),
            {"id": uuid4(), "channel_id": _CHANNEL_ID, "now": _NOW},
        )


def test_orphan_captured_message_links_fail_at_db_level(db_session):
    _insert_account(db_session)
    _insert_channel(db_session)
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO raw_signal_event
                    (id, channel_id, message_id, candidate_text, materialized_by,
                     matched_reasons, created_at)
                VALUES
                    (:id, :channel_id, 404, 'BTC long', 'SEED_HEURISTIC',
                     CAST('[]' AS jsonb), :now)
                """
            ),
            {"id": uuid4(), "channel_id": _CHANNEL_ID, "now": _NOW},
        )
    db_session.rollback()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO golden_label
                    (id, user_id, channel_id, message_id, label, labeled_at)
                VALUES
                    (:id, :user_id, :channel_id, 404, 'signal', :now)
                """
            ),
            {
                "id": uuid4(),
                "user_id": _USER_ID,
                "channel_id": _CHANNEL_ID,
                "now": _NOW,
            },
        )


def test_deleted_signal_evidence_can_reference_uncaptured_messages(db_session):
    _insert_channel(db_session)
    db_session.commit()

    inserted = deletion_repository.upsert_deletion_evidence(
        db_session,
        [
            DeletedSignalEvidence(
                channel_id=_CHANNEL_ID,
                message_id=404,
                confidence=DeletionConfidence.SUSPECTED,
                method=DeletionMethod.ID_GAP,
                detected_at=_NOW,
                was_signal_candidate=False,
            )
        ],
    )
    db_session.commit()

    stored = deletion_repository.read_deletion_evidence(db_session, _CHANNEL_ID)
    assert inserted == 1
    assert stored[0].message_id == 404
