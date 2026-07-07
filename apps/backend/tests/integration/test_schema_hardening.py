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
from verasig.features.feeds import deletion_repository

_CHANNEL_ID = 7
_USER_ID = UUID("80000000-0000-0000-0000-000000000001")
_SOURCE_ID = UUID("80000000-0000-0000-0000-000000000002")
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


def _insert_source(session) -> None:
    session.execute(
        text(
            """
            INSERT INTO source
                (id, user_id, name, status, config_encrypted, created_at, updated_at)
            VALUES
                (:id, :user_id, 'Telegram', 'connected', CAST('{}' AS jsonb),
                 :now, :now)
            """
        ),
        {"id": _SOURCE_ID, "user_id": _USER_ID, "now": _NOW},
    )


def _insert_feed(session) -> None:
    _insert_source(session)
    session.execute(
        text(
            """
            INSERT INTO feed
                (user_id, external_id, source_id, title, status,
                 metadata, first_seen_at, added_at)
            VALUES
                (:user_id, :external_id, :source_id, 'Pilot', 'new',
                 CAST('{}' AS jsonb), :now, :now)
            """
        ),
        {
            "user_id": _USER_ID,
            "external_id": _CHANNEL_ID,
            "source_id": _SOURCE_ID,
            "now": _NOW,
        },
    )


def _insert_captured_message(session, message_id: int) -> None:
    session.execute(
        text(
            """
            INSERT INTO raw_message
                (user_id, external_id, external_message_id, text, posted_at,
                 captured_at, has_media, raw_payload)
            VALUES
                (:user_id, :external_id, :message_id, 'BTC long', :now, :now,
                 false, CAST(:payload AS jsonb))
            """
        ),
        {
            "user_id": _USER_ID,
            "external_id": _CHANNEL_ID,
            "message_id": message_id,
            "now": _NOW,
            "payload": '{"id": 1}',
        },
    )


def test_null_user_id_insert_fails_at_db_level(db_session):
    _insert_account(db_session)
    _insert_feed(db_session)
    _insert_captured_message(db_session, 1)
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO raw_signal_event
                    (id, user_id, external_id, external_message_id, candidate_text,
                     materialized_by, created_at)
                VALUES
                    (:id, NULL, :external_id, 1, 'BTC long', 'SEED_HEURISTIC', :now)
                """
            ),
            {"id": uuid4(), "external_id": _CHANNEL_ID, "now": _NOW},
        )


def test_invalid_enum_string_fails_at_db_level(db_session):
    _insert_account(db_session)
    _insert_feed(db_session)
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO deleted_signal_evidence
                    (id, user_id, external_id, external_message_id, confidence,
                     method, detected_at, was_signal_candidate)
                VALUES
                    (:id, :user_id, :external_id, 99, 'MAYBE', 'ID_GAP', :now, false)
                """
            ),
            {
                "id": uuid4(),
                "user_id": _USER_ID,
                "external_id": _CHANNEL_ID,
                "now": _NOW,
            },
        )


def test_orphan_captured_message_links_fail_at_db_level(db_session):
    _insert_account(db_session)
    _insert_feed(db_session)
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO raw_signal_event
                    (id, user_id, external_id, external_message_id, candidate_text,
                     materialized_by, created_at)
                VALUES
                    (:id, :user_id, :external_id, 404, 'BTC long',
                     'SEED_HEURISTIC', :now)
                """
            ),
            {
                "id": uuid4(),
                "user_id": _USER_ID,
                "external_id": _CHANNEL_ID,
                "now": _NOW,
            },
        )


def test_deleted_signal_evidence_can_reference_uncaptured_messages(db_session):
    _insert_account(db_session)
    _insert_feed(db_session)
    db_session.commit()

    inserted = deletion_repository.upsert_deletion_evidence(
        db_session,
        _USER_ID,
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

    stored = deletion_repository.read_deletion_evidence(
        db_session, _USER_ID, _CHANNEL_ID
    )
    assert inserted == 1
    assert stored[0].message_id == 404
