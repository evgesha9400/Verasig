"""Mining Confirm persists accepted families' signals (ADR 0015, miner-based).

`confirm_mined_signals` re-mines the feed's stored messages, keeps the accepted
template families, persists each candidate as one ``Signal`` — the SAME rows the
Signals view reads — by replacing the feed's whole signal projection (delete +
insert), and marks the feed verified.
"""

from datetime import datetime, timezone
from uuid import uuid4

from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.message import RawTelegramMessage
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import feed_repository, message_repository
from verasig.features.mining.mining_confirm import (
    _to_chat_message,
    confirm_mined_signals,
)
from verasig.features.mining.template_mining import mine_template_groups
from verasig.features.parser_overlay.repository import read_overlay
from verasig.features.signals import outcome_repository
from verasig.features.signals.views import present_signals


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
                _message(1, "BTC LONG entry 100 sl 95 tp 110"),
                _message(2, "gm everyone"),
                _message(3, "ETH LONG entry 200 sl 190 tp 210"),
            ],
        )
        session.commit()
        return account.id


def _seed_backfilled_feed_with_two_families(session_factory) -> object:
    """Two structurally distinct message templates, so mining yields two
    separate template families (unlike `_seed_backfilled_feed`, where BTC/ETH
    share one family)."""
    with session_factory() as session:
        account = account_repository.insert_account(session, _account())
        insert_source(session, account.id)
        feed_repository.create_feed(session, account.id, _channel(), _instant())
        feed_repository.set_status(session, account.id, 1, "backfilled")
        message_repository.insert_messages(
            session,
            account.id,
            [
                _message(1, "BTC LONG entry 100 sl 95 tp 110"),
                _message(2, "gm everyone"),
                _message(4, "SELL EURUSD @ 1.0860\nSL 1.0900\nTP 1.0800"),
            ],
        )
        session.commit()
        return account.id


def _all_keys(session_factory, user_id) -> list[str]:
    with session_factory() as session:
        messages = message_repository.read_messages(session, user_id, 1)
        overlay = read_overlay(session, user_id)
    groups = mine_template_groups([_to_chat_message(m) for m in messages], overlay)
    return [group.template_key for group in groups]


def test_confirm_persists_miner_signals_and_marks_verified(session_factory):
    user_id = _seed_backfilled_feed(session_factory)
    keys = _all_keys(session_factory, user_id)

    result = confirm_mined_signals(session_factory, user_id, 1, keys)

    with session_factory() as session:
        extracted = outcome_repository.read_signals(session, 1, user_id)
        feed = feed_repository.read_feed(session, user_id, 1)
    assert result.feed_status == "verified"
    assert result.signals_extracted == 2  # the two LONG signals, not the chatter
    assert len(extracted) == 2
    assert feed.status == "verified"


def test_confirmed_signals_surface_through_the_signals_view(session_factory):
    user_id = _seed_backfilled_feed(session_factory)
    keys = _all_keys(session_factory, user_id)

    confirm_mined_signals(session_factory, user_id, 1, keys)

    with session_factory() as session:
        result = present_signals(session, user_id, plan=Plan.OPERATOR)
    symbols = sorted(signal["symbol"] for signal in result["signals"])
    assert symbols == ["BTCUSDT", "ETHUSDT"]


def test_confirm_maps_structured_fields_onto_the_signal(session_factory):
    user_id = _seed_backfilled_feed(session_factory)
    keys = _all_keys(session_factory, user_id)

    confirm_mined_signals(session_factory, user_id, 1, keys)

    with session_factory() as session:
        extracted = outcome_repository.read_signals(session, 1, user_id)
    btc = next(signal for signal in extracted if signal.symbol == "BTCUSDT")
    assert btc.side.value == "LONG"
    assert btc.confidence is not None  # miner confidence carried onto the signal
    assert btc.rule_id in keys  # provenance: which template family produced it


def test_confirm_with_empty_keys_persists_nothing_but_verifies(session_factory):
    user_id = _seed_backfilled_feed(session_factory)

    result = confirm_mined_signals(session_factory, user_id, 1, [])

    with session_factory() as session:
        extracted = outcome_repository.read_signals(session, 1, user_id)
        feed = feed_repository.read_feed(session, user_id, 1)
    assert result.signals_extracted == 0
    assert extracted == []
    assert feed.status == "verified"


def test_reconfirm_is_idempotent(session_factory):
    user_id = _seed_backfilled_feed(session_factory)
    keys = _all_keys(session_factory, user_id)

    confirm_mined_signals(session_factory, user_id, 1, keys)
    confirm_mined_signals(session_factory, user_id, 1, keys)

    with session_factory() as session:
        extracted = outcome_repository.read_signals(session, 1, user_id)
    assert len(extracted) == 2  # not doubled


def test_reconfirm_with_a_smaller_accepted_set_removes_deselected_signals(
    session_factory,
):
    """Confirm replaces the feed's whole signal projection. Before the fix,
    persistence only ever upserted, so confirming a SMALLER accepted set left
    the de-selected family's signal orphaned in storage — it resurrected the
    next time the feed was reopened. A replace (delete + insert) makes the
    stored set always exactly the accepted set."""
    user_id = _seed_backfilled_feed_with_two_families(session_factory)
    keys = _all_keys(session_factory, user_id)
    assert len(keys) == 2  # two distinct template families

    confirm_mined_signals(session_factory, user_id, 1, keys)
    with session_factory() as session:
        before = outcome_repository.read_signals(session, 1, user_id)
    assert {signal.symbol for signal in before} == {"BTCUSDT", "EURUSDUSDT"}

    smaller = keys[:1]
    result = confirm_mined_signals(session_factory, user_id, 1, smaller)

    with session_factory() as session:
        after = outcome_repository.read_signals(session, 1, user_id)
    assert result.signals_extracted == 1
    assert len(after) == 1  # the de-selected family's signal is actually gone
    assert {signal.rule_id for signal in after} == set(smaller)
