"""outcome_repository persists the signal projection (ADR 0006, amends 0001).

Every persisted `signal` IS an extraction (there are no stored "misses" —
removed in migration 0021). Confirm reconciles a feed's whole signal set as one
atomic projection with `replace_signals_for_channel`; this covers it and
`insert_signals` in isolation from the mining pipeline (see
`tests/integration/test_mining_confirm.py` for the end-to-end reconfirm flow).
"""

from datetime import datetime, timezone
from uuid import UUID

from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import Side, Signal
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import (
    feed_repository,
    message_repository,
)
from verasig.features.signals import outcome_repository

_USER_ID = UUID("40000000-0000-0000-0000-000000000001")


def _instant() -> datetime:
    return datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc)


def _seed_feed(session_factory, message_id: int, text: str) -> None:
    with session_factory() as session:
        account_repository.insert_account(
            session,
            UserAccount(
                id=_USER_ID,
                email="projection@example.com",
                password_hash="hash",
                first_name="Ada",
                last_name="Lovelace",
                plan=Plan.OBSERVER,
                pending_email=None,
                cancel_at=None,
                created_at=_instant(),
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
                first_seen_at=_instant(),
            ),
            _instant(),
        )
        message_repository.insert_messages(
            session,
            _USER_ID,
            [
                RawTelegramMessage(
                    channel_id=7,
                    message_id=message_id,
                    text=text,
                    posted_at=_instant(),
                    captured_at=_instant(),
                    has_media=False,
                    raw_payload={},
                )
            ],
        )
        session.commit()


def _signal(message_id: int) -> Signal:
    return Signal(
        channel_id=7,
        message_id=message_id,
        candidate_text="BTC long entry 65000",
        symbol="BTCUSDT",
        side=Side.LONG,
    )


def _insert(session_factory, signals: list[Signal]) -> int:
    with session_factory() as session:
        count = outcome_repository.insert_signals(session, signals, _USER_ID)
        session.commit()
        return count


def test_insert_signals_persists_and_is_idempotent_per_message(session_factory):
    _seed_feed(session_factory, 1, "BTC long entry 65000")
    signal = _signal(1)

    inserted_first = _insert(session_factory, [signal])
    inserted_again = _insert(session_factory, [signal])

    with session_factory() as session:
        stored = outcome_repository.read_signals(session, 7, _USER_ID)
    assert inserted_first == 1
    assert inserted_again == 0  # on-conflict-do-nothing keyed on the message
    assert len(stored) == 1
    assert stored[0].symbol == "BTCUSDT"


def test_replace_signals_with_an_empty_set_clears_the_whole_projection(
    session_factory,
):
    _seed_feed(session_factory, 1, "BTC long entry 65000")
    _insert(session_factory, [_signal(1)])

    with session_factory() as session:
        stored = outcome_repository.replace_signals_for_channel(
            session, _USER_ID, 7, []
        )
        session.commit()

    with session_factory() as session:
        assert outcome_repository.read_signals(session, 7, _USER_ID) == []
    assert stored == 0


def test_replace_signals_keeps_the_id_and_rewrites_extraction_columns(
    session_factory,
):
    _seed_feed(session_factory, 1, "BTC long entry 65000")
    original = _signal(1)
    _insert(session_factory, [original])
    rewritten = _signal(1).model_copy(update={"symbol": "ETHUSDT", "rule_id": "tpl_b"})

    with session_factory() as session:
        stored = outcome_repository.replace_signals_for_channel(
            session, _USER_ID, 7, [rewritten]
        )
        session.commit()

    with session_factory() as session:
        [row] = outcome_repository.read_signals(session, 7, _USER_ID)
    assert stored == 1
    assert row.id == original.id  # a fresh Signal.id never replaces a stored one
    assert row.symbol == "ETHUSDT"
    assert row.rule_id == "tpl_b"


def test_read_signal_channel_resolves_a_signals_own_feed(session_factory):
    _seed_feed(session_factory, 1, "BTC long entry 65000")
    signal = _signal(1)
    _insert(session_factory, [signal])

    with session_factory() as session:
        channel_id = outcome_repository.read_signal_channel(
            session, _USER_ID, signal.id
        )
    assert channel_id == 7


def test_replace_signals_upserts_in_chunks(session_factory, monkeypatch):
    _seed_feed(session_factory, 1, "BTC long entry 65000")
    with session_factory() as session:
        message_repository.insert_messages(
            session,
            _USER_ID,
            [
                RawTelegramMessage(
                    channel_id=7,
                    message_id=2,
                    text="ETH long entry 3000",
                    posted_at=_instant(),
                    captured_at=_instant(),
                    has_media=False,
                    raw_payload={},
                )
            ],
        )
        session.commit()
    monkeypatch.setattr(outcome_repository, "_UPSERT_CHUNK", 1)

    with session_factory() as session:
        stored = outcome_repository.replace_signals_for_channel(
            session, _USER_ID, 7, [_signal(1), _signal(2)]
        )
        session.commit()

    with session_factory() as session:
        assert len(outcome_repository.read_signals(session, 7, _USER_ID)) == 2
    assert stored == 2
