from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from seed import insert_source

from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.label import GoldenLabel, LabelKind
from verasig.domain.message import RawTelegramMessage
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import EntryType, ExtractedSignal, Side, UnrecognizedSignal
from verasig.features.accounts.tokens import read_user_id
from verasig.features.feeds import (
    feed_repository,
    message_repository,
)
from verasig.features.rules import repository as rule_repository
from verasig.features.signals import event_repository, outcome_repository
from verasig.features.simulation import repository as backtest_repository

SECRET = "s" * 32
_BASE = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)
_EVENT_ID = UUID("70000000-0000-0000-0000-000000000001")
_SIGNAL_ID = UUID("70000000-0000-0000-0000-000000000002")


def _register(client, email: str = "ada@example.com") -> tuple[str, UUID]:
    response = client.post(
        "/auth/register",
        json={
            "firstName": "Ada",
            "lastName": "Lovelace",
            "email": email,
            "password": "correct horse battery staple",
        },
    )
    body = response.json()
    return body["token"], read_user_id(body["token"], SECRET)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_signal_routes_list_detail_filter_and_link_mod(client, app):
    token, user_id = _register(client)
    _seed(app, user_id)

    listed = client.get("/signals?feedId=7&status=tested", headers=_auth(token))
    detail = client.get(f"/signals/{_SIGNAL_ID}", headers=_auth(token))
    linked = client.post(
        f"/signals/{_SIGNAL_ID}/link-mod",
        headers=_auth(token),
        json={"modId": 3},
    )

    assert listed.status_code == 200
    assert listed.json()["signals"][0]["id"] == str(_SIGNAL_ID)
    assert listed.json()["orphanMods"][0]["id"] == "3"
    assert detail.status_code == 200
    assert linked.status_code == 200
    assert linked.json()["mods"][-1]["id"] == "3"
    assert linked.json()["mods"][-1]["via"] == "inferred"


def test_signal_routes_mask_foreign_user(client, app):
    owner, owner_id = _register(client, "owner@example.com")
    other, _other_id = _register(client, "other@example.com")
    _seed(app, owner_id)

    detail = client.get(f"/signals/{_SIGNAL_ID}", headers=_auth(other))
    linked = client.post(
        f"/signals/{_SIGNAL_ID}/link-mod",
        headers=_auth(other),
        json={"modId": 3},
    )

    assert owner
    assert detail.status_code == 404
    assert linked.status_code == 404
    assert detail.json()["error"]["code"] == "SIGNAL_NOT_FOUND"
    assert linked.json()["error"]["code"] == "SIGNAL_NOT_FOUND"


def test_signal_routes_materialize_verified_feed_signals(client, app):
    token, user_id = _register(client)
    _seed_verified_parser_only(app, user_id)

    listed = client.get("/signals", headers=_auth(token))

    with app.state.session_factory() as session:
        signals = outcome_repository.read_extracted_signals(session, 7, user_id)

    assert listed.status_code == 200
    assert listed.json()["signals"][0]["status"] == "untested"
    assert listed.json()["signals"][0]["symbol"] == "BTCUSDT"
    assert len(signals) == 1


def test_signal_routes_reprocess_unrecognized_after_parser_rules_exist(client, app):
    token, user_id = _register(client)
    _seed_verified_unrecognized_then_parser(app, user_id)

    listed = client.get("/signals", headers=_auth(token))

    with app.state.session_factory() as session:
        signals = outcome_repository.read_extracted_signals(session, 7, user_id)
        unrecognized = outcome_repository.read_unrecognized_signals(session, 7, user_id)

    assert listed.status_code == 200
    assert listed.json()["signals"][0]["symbol"] == "BTCUSDT"
    assert len(signals) == 1
    assert unrecognized == []


def _seed(app, user_id: UUID) -> None:
    with app.state.session_factory() as session:
        insert_source(session, user_id)
        feed_repository.create_feed(
            session,
            user_id,
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
            user_id,
            [
                _message(1, "BTC long entry", None),
                _message(2, "move SL to BE", 1),
                _message(3, "close BTC at 110", None),
            ],
        )
        event_repository.insert_signal_events(session, user_id, [_event()])
        outcome_repository.insert_extracted_signals(session, [_signal()], user_id)
        rule_repository.upsert_labels(
            session,
            [
                GoldenLabel(
                    user_id=user_id,
                    channel_id=7,
                    message_id=3,
                    label=LabelKind.MODIFIER,
                )
            ],
        )
        backtest_repository.insert_result(
            session,
            user_id,
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
        feed_repository.set_status(session, user_id, 7, "analyzed")
        session.commit()


def _seed_verified_parser_only(app, user_id: UUID) -> None:
    with app.state.session_factory() as session:
        insert_source(session, user_id)
        feed_repository.create_feed(
            session,
            user_id,
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
            user_id,
            [_message(1, "BTC long entry 100 sl 95 tp 110", None)],
        )
        event_repository.insert_signal_events(
            session,
            user_id,
            [
                RawSignalEvent(
                    id=_EVENT_ID,
                    channel_id=7,
                    message_id=1,
                    candidate_text="BTC long entry 100 sl 95 tp 110",
                    materialized_by=MaterializationPath.SEED_HEURISTIC,
                    created_at=_BASE,
                )
            ],
        )
        rule_repository.upsert_parser_rules(session, [_parser_rule(user_id)])
        feed_repository.set_status(session, user_id, 7, "verified")
        session.commit()


def _seed_verified_unrecognized_then_parser(app, user_id: UUID) -> None:
    with app.state.session_factory() as session:
        insert_source(session, user_id)
        feed_repository.create_feed(
            session,
            user_id,
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
            user_id,
            [_message(1, "BTC long entry 100 sl 95 tp 110", None)],
        )
        event_repository.insert_signal_events(
            session,
            user_id,
            [
                RawSignalEvent(
                    id=_EVENT_ID,
                    channel_id=7,
                    message_id=1,
                    candidate_text="BTC long entry 100 sl 95 tp 110",
                    materialized_by=MaterializationPath.SEED_HEURISTIC,
                    created_at=_BASE,
                )
            ],
        )
        outcome_repository.insert_unrecognized_signals(
            session,
            [UnrecognizedSignal(event_id=_EVENT_ID, reason="no_match")],
            user_id,
        )
        rule_repository.upsert_parser_rules(session, [_parser_rule(user_id)])
        feed_repository.set_status(session, user_id, 7, "verified")
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


def _parser_rule(user_id: UUID) -> ParserRule:
    return ParserRule(
        rule_id=f"{user_id}:7-parser-v1",
        user_id=user_id,
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
