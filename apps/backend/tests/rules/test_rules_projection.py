from datetime import datetime, timezone
from uuid import uuid4

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import GoldenLabel, LabelKind
from verasig.domain.message import RawTelegramMessage
from verasig.features.accounts import repository as account_repository
from verasig.features.rules import repository as rule_repository
from verasig.features.rules.views import present_rules
from verasig.features.sources import (
    feed_repository,
    message_repository,
)


def _instant() -> datetime:
    return datetime(2026, 6, 1, tzinfo=timezone.utc)


def test_present_rules_projects_display_and_signal_match(db_session):
    account = account_repository.insert_account(
        db_session,
        UserAccount(
            id=uuid4(),
            email="user@example.com",
            password_hash="hash",
            first_name="Ada",
            last_name="Lovelace",
            plan=Plan.OBSERVER,
            pending_email=None,
            cancel_at=None,
            created_at=_instant(),
        ),
    )
    feed_repository.create_feed(
        db_session,
        account.id,
        TelegramChannel(
            channel_id=7,
            handle="pilot",
            title="Pilot",
            is_private=False,
            first_seen_at=_instant(),
        ),
        _instant(),
    )
    message_repository.insert_messages(
        db_session,
        account.id,
        [
            RawTelegramMessage(
                channel_id=7,
                message_id=1,
                text="alpha setup",
                posted_at=_instant(),
                captured_at=_instant(),
                has_media=False,
                raw_payload={},
            ),
            RawTelegramMessage(
                channel_id=7,
                message_id=2,
                text="beta setup",
                posted_at=_instant(),
                captured_at=_instant(),
                has_media=False,
                raw_payload={},
            ),
        ],
    )
    rule_repository.upsert_labels(
        db_session,
        [
            GoldenLabel(
                user_id=account.id, channel_id=7, message_id=1, label=LabelKind.SIGNAL
            ),
            GoldenLabel(
                user_id=account.id, channel_id=7, message_id=2, label=LabelKind.SIGNAL
            ),
        ],
    )
    rule_repository.upsert_filter_rule(
        db_session,
        FilterRule(
            rule_id=f"{account.id}:7-filter-v1",
            user_id=account.id,
            channel_id=7,
            include_patterns=["alpha"],
            display=[{"label": "Alpha", "detail": "Mentions alpha"}],
        ),
    )
    db_session.commit()

    assert present_rules(db_session, account.id, 7) == [
        {
            "id": f"{account.id}:7-filter-v1:0",
            "label": "Alpha",
            "detail": "Mentions alpha",
            "match": 50.0,
        }
    ]
