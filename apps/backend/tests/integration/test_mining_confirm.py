"""Mining Confirm persists compiled rules and re-derives everything (ADR 0015).

`confirm_mining_rules` replaces the feed's rules at a bumped version, re-derives
candidates through the new filter, re-extracts every event with the new parser,
recomputes deletion-evidence candidacy from the rules, and marks the feed
verified — server-side, replacing the old frontend-only 'verified' patch.
"""

from datetime import datetime, timezone
from uuid import uuid4

from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.domain.message import RawTelegramMessage
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import (
    deletion_repository,
    feed_repository,
    message_repository,
)
from verasig.features.rules import repository as rule_repository
from verasig.features.rules.mining_confirm import confirm_mining_rules
from verasig.features.rules.mining_schemas import MiningRulesConfirmIn
from verasig.features.signals import outcome_repository
from verasig.foundation.market_data.static_exchange import StaticExchange


def _instant() -> datetime:
    return datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)


def _channel() -> TelegramChannel:
    return TelegramChannel(
        channel_id=1, title="Pilot", is_private=False, first_seen_at=_instant()
    )


def _message(message_id: int, text: str) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=1,
        message_id=message_id,
        text=text,
        posted_at=_instant(),
        captured_at=_instant(),
        has_media=False,
        raw_payload={"id": message_id},
    )


def _account() -> UserAccount:
    return UserAccount(
        id=uuid4(),
        email="user@example.com",
        password_hash="hash",
        first_name="Ada",
        last_name="Lovelace",
        plan=Plan.OBSERVER,
        pending_email=None,
        cancel_at=None,
        created_at=_instant(),
    )


def _seed_backfilled_feed(session_factory) -> object:
    with session_factory() as session:
        account = account_repository.insert_account(session, _account())
        insert_source(session, account.id)
        feed_repository.create_feed(session, account.id, _channel(), _instant())
        feed_repository.set_status(session, account.id, 1, "backfilled")
        message_repository.insert_messages(
            session,
            account.id,
            [
                _message(1, "BTC LONG entry 100"),
                _message(2, "gm everyone"),
                _message(3, "ETH LONG entry 200"),
            ],
        )
        session.commit()
        return account.id


_PAYLOAD = {
    "filterRule": {"includePatterns": ["LONG"]},
    "parserRules": [
        {
            "patterns": [r"(?P<symbol>\w+)\s+(?P<side>LONG|SHORT)"],
            "fieldMap": {"symbol": "symbol", "side": "side"},
            "sideAliases": {"long": "LONG", "short": "SHORT"},
        }
    ],
}


def _confirm(session_factory, user_id) -> object:
    payload = MiningRulesConfirmIn.model_validate(_PAYLOAD)
    return confirm_mining_rules(
        session_factory,
        user_id,
        1,
        payload.filter_rule,
        payload.parser_rules,
        StaticExchange(),
    )


def test_confirm_persists_rules_rederives_and_marks_verified(session_factory):
    user_id = _seed_backfilled_feed(session_factory)

    result = _confirm(session_factory, user_id)

    with session_factory() as session:
        assert rule_repository.read_filter_rules(session, 1, user_id)
        assert len(rule_repository.read_parser_rules(session, 1, user_id)) == 1
        extracted = outcome_repository.read_extracted_signals(session, 1, user_id)
        assert feed_repository.read_feed(session, user_id, 1).status == "verified"
    assert result.feed_status == "verified"
    assert result.signals_extracted == 2  # the two LONG messages, not the chatter
    assert len(extracted) == 2


def test_reconfirm_replaces_rules_at_a_bumped_version(session_factory):
    user_id = _seed_backfilled_feed(session_factory)

    _confirm(session_factory, user_id)
    _confirm(session_factory, user_id)

    with session_factory() as session:
        parser_rules = rule_repository.read_parser_rules(session, 1, user_id)
        filter_rules = rule_repository.read_filter_rules(session, 1, user_id)
    assert len(parser_rules) == 1  # replaced, not appended
    assert len(filter_rules) == 1
    assert parser_rules[0].version == 2
    assert "v2" in parser_rules[0].rule_id


def test_confirm_recomputes_deletion_evidence_candidacy_from_rules(session_factory):
    user_id = _seed_backfilled_feed(session_factory)
    # a CONFIRMED deleted message (no surviving raw row) the new rules recognize
    with session_factory() as session:
        deletion_repository.upsert_deletion_evidence(
            session,
            user_id,
            [
                DeletedSignalEvidence(
                    channel_id=1,
                    message_id=99,
                    confidence=DeletionConfidence.CONFIRMED,
                    method=DeletionMethod.SNAPSHOT_DIFF,
                    original_text="SOL LONG entry 5",
                    first_seen_at=_instant(),
                    detected_at=_instant(),
                    was_signal_candidate=False,
                )
            ],
        )
        session.commit()

    result = _confirm(session_factory, user_id)

    with session_factory() as session:
        evidence = deletion_repository.read_deletion_evidence(session, user_id, 1)
    deleted = next(item for item in evidence if item.message_id == 99)
    assert deleted.was_signal_candidate is True  # rules now recognize the text
    assert result.evidence_updated == 1
