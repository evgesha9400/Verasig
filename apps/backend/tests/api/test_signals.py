from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from seed import insert_source

from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.label import GoldenLabel, LabelKind
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import EntryType, ExtractedSignal, Side
from verasig.features.accounts.tokens import read_user_id
from verasig.features.rules import repository as rule_repository
from verasig.features.signals import event_repository, outcome_repository
from verasig.features.simulation import repository as backtest_repository
from verasig.features.sources import (
    feed_repository,
    message_repository,
)

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
