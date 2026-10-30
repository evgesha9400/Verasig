from datetime import datetime, timezone
from uuid import uuid4

from verasig.domain.account import Plan, UserAccount
from verasig.features.accounts import repository as account_repository
from verasig.features.parser_overlay.repository import read_overlay, upsert_overlay


def _account():
    return UserAccount(
        id=uuid4(),
        email="overlay@example.com",
        password_hash="hash",
        first_name="Ada",
        last_name="Lovelace",
        plan=Plan.FREE,
        pending_email=None,
        cancel_at=None,
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )


def test_read_overlay_defaults_to_empty(db_session):
    account = account_repository.insert_account(db_session, _account())
    assert read_overlay(db_session, account.id) == {}


def test_upsert_overlay_round_trips_and_replaces(db_session):
    account = account_repository.insert_account(db_session, _account())
    upsert_overlay(db_session, account.id, {"instrumentAliases": {"АПТ": "APTUSDT"}})
    db_session.commit()
    assert read_overlay(db_session, account.id) == {
        "instrumentAliases": {"АПТ": "APTUSDT"}
    }

    upsert_overlay(db_session, account.id, {"rejectPhrases": ["closed"]})
    db_session.commit()
    assert read_overlay(db_session, account.id) == {"rejectPhrases": ["closed"]}
