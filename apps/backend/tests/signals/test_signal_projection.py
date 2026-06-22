from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.label import GoldenLabel, LabelKind
from verasig.domain.message import RawTelegramMessage
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import EntryType, ExtractedSignal, Side
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import (
    deletion_repository,
    feed_repository,
    message_repository,
)
from verasig.features.rules import repository as rule_repository
from verasig.features.signals import event_repository, outcome_repository
from verasig.features.signals.views import present_signals
from verasig.features.simulation import repository as backtest_repository

_BASE = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)
_USER_ID = UUID("60000000-0000-0000-0000-000000000001")
_EVENT_ID = UUID("60000000-0000-0000-0000-000000000002")
_SIGNAL_ID = UUID("60000000-0000-0000-0000-000000000003")


def test_present_signals_projects_lifecycle_outcomes_and_orphan_mods(db_session):
    _seed(db_session)

    result = present_signals(db_session, _USER_ID, plan=Plan.OPERATOR)

    signal = result["signals"][0]
    orphan = result["orphanMods"][0]
    assert result["limitReached"] is False
    assert signal["id"] == str(_SIGNAL_ID)
    assert signal["feedId"] == "7"
    assert signal["feedName"] == "Pilot"
    assert signal["feedTag"] == "@pilot"
    assert signal["feedInitials"] == "P"
    assert signal["feedTint"].startswith("var(--viz-")
    assert signal["text"] == "BTC long entry"
    assert signal["status"] == "tested"
    assert signal["outcome"] == "profit"
    assert signal["pnl"] == 1.5
    assert signal["tp"] == ["110"]
    assert signal["tpText"] == "110"
    assert signal["mods"][0]["kind"] == "move_stop"
    assert signal["mods"][0]["via"] == "reply"
    assert signal["mods"][0]["effect"] == "Stop -> 100"
    assert signal["effective"]["stop"] == "100"
    assert orphan["id"] == "3"
    assert orphan["suggestId"] == str(_SIGNAL_ID)


def test_present_signals_includes_verified_feed_without_backtest(db_session):
    _seed(db_session, status="verified", with_backtest=False)

    result = present_signals(db_session, _USER_ID, plan=Plan.OPERATOR)

    assert result["signals"][0]["status"] == "untested"
    assert result["signals"][0]["text"] == "BTC long entry"


def test_present_signals_materializes_verified_feed_signals(db_session):
    _seed(
        db_session,
        status="verified",
        with_backtest=False,
        with_extracted=False,
        message_text="BTC long entry 100 sl 95 tp 110",
    )

    result = present_signals(db_session, _USER_ID, plan=Plan.OPERATOR)

    signal = result["signals"][0]
    assert signal["status"] == "untested"
    assert signal["symbol"] == "BTCUSDT"
    assert signal["entry"] == "100"
    assert signal["stop"] == "95"
    assert signal["tp"] == ["110"]
    assert signal["text"] == "BTC long entry 100 sl 95 tp 110"


def test_present_signals_filters_confirmed_deleted_evidence(db_session):
    _seed(db_session, deleted=True)

    result = present_signals(db_session, _USER_ID, status="deleted", plan=Plan.OPERATOR)

    assert len(result["signals"]) == 1
    assert result["signals"][0]["status"] == "deleted"
    assert result["signals"][0]["deleted"] is True


def test_present_signals_ignores_unlabelled_candidate_deletion(db_session):
    _seed(db_session, deleted=True, label_deleted_signal=False)

    result = present_signals(db_session, _USER_ID, status="deleted", plan=Plan.OPERATOR)

    assert result["signals"] == []


def _seed(
    session,
    *,
    status: str = "analyzed",
    with_backtest: bool = True,
    with_extracted: bool = True,
    message_text: str = "BTC long entry",
    deleted: bool = False,
    label_deleted_signal: bool = True,
) -> None:
    account_repository.insert_account(
        session,
        UserAccount(
            id=_USER_ID,
            email="user@example.com",
            password_hash="hash",
            first_name="Ada",
            last_name="Lovelace",
            plan=Plan.OPERATOR,
            pending_email=None,
            cancel_at=None,
            created_at=_BASE,
        ),
    )
    insert_source(session, _USER_ID)
    feed_repository.create_feed(
        session,
        _USER_ID,
        TelegramChannel(
            channel_id=7,
            handle="pilot",
            title="Pilot",
            is_private=False,
            first_seen_at=_BASE,
        ),
        _BASE,
    )
    message_repository.insert_messages(
        session,
        _USER_ID,
        [
            _message(1, message_text, None),
            _message(2, "move SL to BE", 1),
            _message(3, "close BTC at 110", None),
        ],
    )
    event_repository.insert_signal_events(session, _USER_ID, [_event(message_text)])
    if with_extracted:
        outcome_repository.insert_extracted_signals(session, [_signal()], _USER_ID)
    else:
        rule_repository.upsert_parser_rules(session, [_parser_rule()])
    labels = [
        GoldenLabel(
            user_id=_USER_ID, channel_id=7, message_id=3, label=LabelKind.MODIFIER
        )
    ]
    if deleted and label_deleted_signal:
        labels.append(
            GoldenLabel(
                user_id=_USER_ID,
                channel_id=7,
                message_id=1,
                label=LabelKind.SIGNAL,
            )
        )
    rule_repository.upsert_labels(session, labels)
    if with_backtest:
        backtest_repository.insert_result(
            session,
            _USER_ID,
            7,
            90,
            Decimal("100.0"),
            Decimal("1.5"),
            [
                {
                    "rootSignalId": str(_SIGNAL_ID),
                    "kind": "R_MULTIPLE",
                    "rMultiple": 2.0,
                    "pctReturn": 1.5,
                    "exitReason": "tp",
                }
            ],
            _BASE,
        )
    if deleted:
        deletion_repository.upsert_deletion_evidence(
            session,
            _USER_ID,
            [
                DeletedSignalEvidence(
                    channel_id=7,
                    message_id=1,
                    confidence=DeletionConfidence.CONFIRMED,
                    method=DeletionMethod.SNAPSHOT_DIFF,
                    original_text="BTC long entry",
                    first_seen_at=_BASE,
                    detected_at=_BASE,
                    was_signal_candidate=True,
                )
            ],
        )
    feed_repository.set_status(session, _USER_ID, 7, status)
    session.commit()


def _message(message_id: int, text: str, reply_to: int | None) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=7,
        message_id=message_id,
        text=text,
        posted_at=_BASE,
        captured_at=_BASE,
        reply_to_message_id=reply_to,
        has_media=False,
        raw_payload={},
    )


def _event(candidate_text: str = "BTC long entry") -> RawSignalEvent:
    return RawSignalEvent(
        id=_EVENT_ID,
        channel_id=7,
        message_id=1,
        candidate_text=candidate_text,
        materialized_by=MaterializationPath.SEED_HEURISTIC,
        created_at=_BASE,
    )


def _signal() -> ExtractedSignal:
    return ExtractedSignal(
        id=_SIGNAL_ID,
        event_id=_EVENT_ID,
        channel_id=7,
        symbol="BTCUSDT",
        side=Side.LONG,
        entry_type=EntryType.LIMIT_SINGLE,
        entry_low=Decimal("100"),
        entry_high=Decimal("100"),
        stop_loss=Decimal("95"),
        take_profits=[Decimal("110")],
        extracted_at=_BASE,
    )


def _parser_rule() -> ParserRule:
    return ParserRule(
        rule_id=f"{_USER_ID}:7-parser-v1",
        user_id=_USER_ID,
        channel_id=7,
        patterns=[
            r"(?P<symbol>[A-Z]{2,10})\s+(?P<side>long|short)"
            r".*?entry\s+(?P<entry>[\d.]+).*?sl\s+(?P<sl>[\d.]+)"
            r".*?tp\s+(?P<tp>[\d.]+)"
        ],
        field_map={
            "symbol": "symbol",
            "side": "side",
            "entry": "entry",
            "sl": "stop_loss",
            "tp": "take_profit",
        },
        side_aliases={"long": "LONG", "short": "SHORT"},
    )
