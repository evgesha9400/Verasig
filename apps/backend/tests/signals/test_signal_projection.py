from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.label import GoldenLabel, LabelKind
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import EntryType, ExtractedSignal, Side
from verasig.features.accounts import repository as account_repository
from verasig.features.rules import repository as rule_repository
from verasig.features.signals import event_repository, outcome_repository
from verasig.features.signals.views import present_signals
from verasig.features.simulation import repository as backtest_repository
from verasig.features.sources import (
    channel_repository,
    message_repository,
)
from verasig.features.sources import subscription_repository as user_channel_repository

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
    assert signal["status"] == "tested"
    assert signal["outcome"] == "profit"
    assert signal["pnl"] == 1.5
    assert signal["mods"][0]["kind"] == "move_stop"
    assert signal["mods"][0]["via"] == "reply"
    assert signal["effective"]["stop"] == "100"
    assert orphan["id"] == "3"
    assert orphan["suggestId"] == str(_SIGNAL_ID)


def _seed(session) -> None:
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
    channel_repository.upsert_channel(
        session,
        TelegramChannel(
            channel_id=7,
            handle="pilot",
            title="Pilot",
            is_private=False,
            first_seen_at=_BASE,
        ),
    )
    message_repository.insert_messages(
        session,
        [
            _message(1, "BTC long entry", None),
            _message(2, "move SL to BE", 1),
            _message(3, "close BTC at 110", None),
        ],
    )
    event_repository.insert_signal_events(session, [_event()])
    outcome_repository.insert_extracted_signals(session, [_signal()], _USER_ID)
    rule_repository.upsert_labels(
        session,
        [
            GoldenLabel(
                user_id=_USER_ID, channel_id=7, message_id=3, label=LabelKind.MODIFIER
            )
        ],
    )
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
    user_channel_repository.subscribe(session, _USER_ID, 7, _BASE)
    user_channel_repository.set_status(session, _USER_ID, 7, "analyzed")
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


def _event() -> RawSignalEvent:
    return RawSignalEvent(
        id=_EVENT_ID,
        channel_id=7,
        message_id=1,
        candidate_text="BTC long entry",
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
