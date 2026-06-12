from datetime import datetime, timezone
from uuid import uuid4

import pytest

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.filter_rule import FilterRule
from verasig.domain.message import RawTelegramMessage
from verasig.services.verification.service import (
    TooFewVerdictsError,
    apply_verdicts,
    verification_samples,
)
from verasig.storage import (
    account_repository,
    user_channel_repository,
)
from verasig.storage import (
    repositories as repo,
)


def _instant() -> datetime:
    return datetime(2026, 6, 1, tzinfo=timezone.utc)


def _seed(db_session):
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
    repo.upsert_channel(
        db_session,
        TelegramChannel(
            channel_id=7,
            handle="pilot",
            title="Pilot Signals",
            is_private=False,
            first_seen_at=_instant(),
        ),
    )
    messages = [
        RawTelegramMessage(
            channel_id=7,
            message_id=idx,
            text=("alpha" if idx <= 3 else "beta"),
            posted_at=datetime(2026, 6, idx, tzinfo=timezone.utc),
            captured_at=_instant(),
            has_media=False,
            raw_payload={},
        )
        for idx in range(1, 7)
    ]
    repo.insert_messages(db_session, messages)
    repo.insert_signal_events(
        db_session,
        [
            RawSignalEvent(
                channel_id=7,
                message_id=message.message_id,
                candidate_text=message.text,
                materialized_by=MaterializationPath.SEED_HEURISTIC,
            )
            for message in messages
        ],
    )
    repo.upsert_filter_rule(
        db_session,
        FilterRule(
            rule_id=f"{account.id}:7-filter-v1",
            user_id=account.id,
            channel_id=7,
            include_patterns=["alpha"],
        ),
    )
    user_channel_repository.subscribe(db_session, account.id, 7, _instant())
    db_session.commit()
    return account


def test_verification_samples_include_predictions(db_session):
    account = _seed(db_session)

    result = verification_samples(db_session, account.id, 7)

    assert result["attempt"] == 1
    assert [sample["predicted"] for sample in result["samples"]] == [
        "signal",
        "signal",
        "signal",
        "noise",
        "noise",
        "noise",
    ]


def test_apply_verdicts_records_wrong_feedback_and_passes_all_correct(db_session):
    account = _seed(db_session)

    passed, misclassified = apply_verdicts(
        db_session,
        account.id,
        7,
        [
            {"messageId": str(idx), "verdict": "wrong" if idx == 4 else "correct"}
            for idx in range(1, 7)
        ],
    )
    db_session.commit()
    followup_passed, followup_misclassified = apply_verdicts(
        db_session,
        account.id,
        7,
        [{"messageId": str(idx), "verdict": "correct"} for idx in range(1, 7)],
    )

    assert passed is False
    assert misclassified == ["4"]
    assert (
        user_channel_repository.read_subscription(
            db_session, account.id, 7
        ).verify_attempt
        == 2
    )
    assert len(repo.read_drift_warnings(db_session, 7, account.id)) == 1
    assert followup_passed is True
    assert followup_misclassified == []
    assert (
        user_channel_repository.read_subscription(db_session, account.id, 7).status
        == "verified"
    )


def test_apply_verdicts_rejects_too_few_verdicts(db_session):
    account = _seed(db_session)

    with pytest.raises(TooFewVerdictsError):
        apply_verdicts(
            db_session,
            account.id,
            7,
            [{"messageId": str(idx), "verdict": "correct"} for idx in range(1, 6)],
        )
