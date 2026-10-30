"""Mining Confirm persists accepted families' signals (ADR 0015, miner-based).

`confirm_review` consumes a revisioned review, keeps the accepted
template families, persists each audit-parsed candidate as one ``Signal`` — the
SAME rows the Signals view reads — by reconciling the feed's whole signal
projection (a retained message keeps its signal id), and marks the feed verified.
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, timezone
from decimal import Decimal
from threading import Event
from uuid import uuid4

import pytest
from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.message import RawTelegramMessage
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import feed_repository, message_repository
from verasig.features.feeds.backfill_job_coordinator import BackfillJobCoordinator
from verasig.features.feeds.backfill_job_run import BackfillMode
from verasig.features.mining import mining_review_repository
from verasig.features.mining.mining_confirm import (
    confirm_review,
)
from verasig.features.mining.mining_review import create_review, read_input
from verasig.features.mining.template_mining import mine_template_groups
from verasig.features.signals import lifecycle_link_repository, outcome_repository
from verasig.features.signals.views import present_signals
from verasig.features.simulation import repository as backtest_repository
from verasig.foundation.jobs.registry import JobRegistry


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
        plan=Plan.FREE,
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


def _create_review(session_factory, user_id):
    with session_factory() as session:
        review_input = read_input(session, user_id, 1)
        groups = mine_template_groups(review_input.messages, review_input.overlay)
        review = create_review(session, user_id, 1, review_input, groups)
        session.commit()
    return review


def test_confirm_persists_miner_signals_and_marks_verified(session_factory):
    user_id = _seed_backfilled_feed(session_factory)
    review = _create_review(session_factory, user_id)
    keys = [group.template_key for group in review.groups]

    result = confirm_review(session_factory, user_id, 1, review.review_id, keys)

    with session_factory() as session:
        extracted = outcome_repository.read_signals(session, 1, user_id)
        feed = feed_repository.read_feed(session, user_id, 1)
    assert result.feed_status == "verified"
    assert result.signals_extracted == 2  # the two LONG signals, not the chatter
    assert len(extracted) == 2
    assert feed.status == "verified"


def test_confirmed_signals_surface_through_the_signals_view(session_factory):
    user_id = _seed_backfilled_feed(session_factory)
    review = _create_review(session_factory, user_id)
    keys = [group.template_key for group in review.groups]

    confirm_review(session_factory, user_id, 1, review.review_id, keys)

    with session_factory() as session:
        result = present_signals(session, user_id, plan=Plan.TRADER)
    symbols = sorted(signal["symbol"] for signal in result["signals"])
    assert symbols == ["BTCUSDT", "ETHUSDT"]


def test_confirm_maps_structured_fields_onto_the_signal(session_factory):
    user_id = _seed_backfilled_feed(session_factory)
    review = _create_review(session_factory, user_id)
    keys = [group.template_key for group in review.groups]

    confirm_review(session_factory, user_id, 1, review.review_id, keys)

    with session_factory() as session:
        extracted = outcome_repository.read_signals(session, 1, user_id)
    btc = next(signal for signal in extracted if signal.symbol == "BTCUSDT")
    assert btc.side.value == "LONG"
    assert btc.entry_low == Decimal("100")
    assert btc.stop_loss == Decimal("95")
    assert btc.take_profits == [Decimal("110")]
    assert btc.confidence is not None  # miner confidence carried onto the signal
    assert btc.rule_id in keys  # provenance: which template family produced it


def test_confirm_with_empty_keys_persists_nothing_but_verifies(session_factory):
    user_id = _seed_backfilled_feed(session_factory)
    review = _create_review(session_factory, user_id)

    result = confirm_review(session_factory, user_id, 1, review.review_id, [])

    with session_factory() as session:
        extracted = outcome_repository.read_signals(session, 1, user_id)
        feed = feed_repository.read_feed(session, user_id, 1)
    assert result.signals_extracted == 0
    assert extracted == []
    assert feed.status == "verified"


def test_reconfirm_is_idempotent(session_factory):
    user_id = _seed_backfilled_feed(session_factory)
    review = _create_review(session_factory, user_id)
    keys = [group.template_key for group in review.groups]

    confirm_review(session_factory, user_id, 1, review.review_id, keys)
    confirm_review(session_factory, user_id, 1, review.review_id, keys)

    with session_factory() as session:
        extracted = outcome_repository.read_signals(session, 1, user_id)
    assert len(extracted) == 2  # not doubled


def test_reconfirm_with_a_smaller_accepted_set_removes_deselected_signals(
    session_factory,
):
    """Confirm reconciles the feed's whole signal projection: confirming a
    SMALLER accepted set must not leave the de-selected family's signal
    orphaned in storage (it would resurrect when the feed is reopened)."""
    user_id = _seed_backfilled_feed_with_two_families(session_factory)
    review = _create_review(session_factory, user_id)
    keys = [group.template_key for group in review.groups]
    assert len(keys) == 2  # two distinct template families

    confirm_review(session_factory, user_id, 1, review.review_id, keys)
    with session_factory() as session:
        before = outcome_repository.read_signals(session, 1, user_id)
    assert {signal.symbol for signal in before} == {"BTCUSDT", "EURUSD"}

    smaller = keys[:1]
    result = confirm_review(session_factory, user_id, 1, review.review_id, smaller)

    with session_factory() as session:
        after = outcome_repository.read_signals(session, 1, user_id)
    assert result.signals_extracted == 1
    assert len(after) == 1  # the de-selected family's signal is actually gone
    assert {signal.rule_id for signal in after} == set(smaller)


def test_reconfirm_drops_backtests_of_the_previous_signal_set(session_factory):
    user_id = _seed_backfilled_feed(session_factory)
    review = _create_review(session_factory, user_id)
    keys = [group.template_key for group in review.groups]
    confirm_review(session_factory, user_id, 1, review.review_id, keys)
    with session_factory() as session:
        backtest_repository.insert_result(
            session, user_id, 1, 70, Decimal("50"), Decimal("1"), [], _instant()
        )
        feed_repository.set_status(session, user_id, 1, "analyzed")
        session.commit()

    result = confirm_review(session_factory, user_id, 1, review.review_id, keys[:1])

    with session_factory() as session:
        results = backtest_repository.read_latest_results(session, user_id)
        feed = feed_repository.read_feed(session, user_id, 1)
    assert result.feed_status == "verified"
    assert 1 not in results
    assert feed.status == "verified"


def test_reconfirm_keeps_retained_signal_ids_and_their_lifecycle_links(
    session_factory,
):
    user_id = _seed_backfilled_feed_with_two_families(session_factory)
    review = _create_review(session_factory, user_id)
    keys = [group.template_key for group in review.groups]
    confirm_review(session_factory, user_id, 1, review.review_id, keys)
    with session_factory() as session:
        before = outcome_repository.read_signals(session, 1, user_id)
        btc = next(signal for signal in before if signal.symbol == "BTCUSDT")
        lifecycle_link_repository.insert_link(
            session, user_id, 1, 2, btc.id, _instant()
        )
        session.commit()

    confirm_review(session_factory, user_id, 1, review.review_id, [btc.rule_id])

    with session_factory() as session:
        after = outcome_repository.read_signals(session, 1, user_id)
        links = lifecycle_link_repository.read_links(session, user_id, 1)
    assert [signal.id for signal in after] == [btc.id]  # EURUSD gone, BTC id kept
    assert [link.root_signal_id for link in links] == [btc.id]


def test_confirm_failure_rolls_back_projection_status_and_review_evidence(
    session_factory, monkeypatch
):
    user_id = _seed_backfilled_feed(session_factory)
    review = _create_review(session_factory, user_id)
    keys = [group.template_key for group in review.groups]
    confirm_review(session_factory, user_id, 1, review.review_id, keys)
    with session_factory() as session:
        feed_repository.set_status(session, user_id, 1, "analyzed")
        before = outcome_repository.read_signals(session, 1, user_id)
        session.commit()

    def fail_after_projection(*_args, **_kwargs):
        raise RuntimeError("injected confirm failure")

    monkeypatch.setattr(
        mining_review_repository, "mark_review_confirmed", fail_after_projection
    )

    with pytest.raises(RuntimeError, match="injected confirm failure"):
        confirm_review(session_factory, user_id, 1, review.review_id, [])

    with session_factory() as session:
        after = outcome_repository.read_signals(session, 1, user_id)
        feed = feed_repository.read_feed(session, user_id, 1)
        review_row = mining_review_repository.read_review_row(
            session, user_id, 1, review.review_id
        )
    assert [signal.id for signal in after] == [signal.id for signal in before]
    assert feed.status == "analyzed"
    assert review_row.accepted_template_keys == keys


def test_confirm_and_backfill_serialize_on_the_feed_row(session_factory, monkeypatch):
    user_id = _seed_backfilled_feed(session_factory)
    review = _create_review(session_factory, user_id)
    keys = [group.template_key for group in review.groups]
    projection_started = Event()
    release_confirm = Event()
    original_replace = outcome_repository.replace_signals_for_channel

    def block_after_lock(session, owner_id, external_id, signals):
        stored = original_replace(session, owner_id, external_id, signals)
        projection_started.set()
        assert release_confirm.wait(timeout=5)
        return stored

    monkeypatch.setattr(
        outcome_repository, "replace_signals_for_channel", block_after_lock
    )
    coordinator = BackfillJobCoordinator(session_factory, JobRegistry(), batch_size=200)

    with ThreadPoolExecutor(max_workers=2) as executor:
        confirm_future = executor.submit(
            confirm_review,
            session_factory,
            user_id,
            1,
            review.review_id,
            keys,
        )
        assert projection_started.wait(timeout=5)
        backfill_future = executor.submit(
            coordinator._create_run, user_id, 1, BackfillMode.REFRESH
        )
        with pytest.raises(TimeoutError):
            backfill_future.result(timeout=0.2)
        release_confirm.set()
        confirmed = confirm_future.result(timeout=5)
        _run, previous_status = backfill_future.result(timeout=5)

    with session_factory() as session:
        feed = feed_repository.read_feed(session, user_id, 1)
        signals = outcome_repository.read_signals(session, 1, user_id)
    assert confirmed.feed_status == "verified"
    assert previous_status == "verified"
    assert feed.status == "backfilling"
    assert len(signals) == 2
