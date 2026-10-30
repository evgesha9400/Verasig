from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from conftest import _auth
from conftest import _register_user as _register
from seed import insert_source

from verasig.domain.channel import TelegramChannel
from verasig.domain.risk_config import EntryMode, ExitSource, RiskConfig, Weighting
from verasig.features.feeds import feed_repository
from verasig.features.risk import repository as risk_repository
from verasig.features.simulation import repository as backtest_repository


def _seed_subscription(app, user_id: UUID) -> None:
    with app.state.session_factory() as session:
        insert_source(session, user_id)
        feed_repository.create_feed(
            session,
            user_id,
            TelegramChannel(
                channel_id=7,
                handle="pilot",
                title="Pilot Signals",
                is_private=False,
                first_seen_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            ),
            datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        session.commit()


def test_risk_get_returns_default_config(client, app):
    token, user_id = _register(client)
    _seed_subscription(app, user_id)

    response = client.get("/feeds/7/risk", headers=_auth(token))

    assert response.status_code == 200
    assert response.json() == _risk_json(RiskConfig())


def test_risk_put_persists_and_echoes_config(client, app):
    token, user_id = _register(client)
    _seed_subscription(app, user_id)
    payload = {
        "entryMode": "ladder",
        "levels": 5,
        "weighting": "martingale",
        "exitSource": "custom",
        "stopPct": "3.0",
        "tpPct": "9.5",
        "riskPct": "1.5",
        "leverage": 8,
    }

    response = client.put("/feeds/7/risk", headers=_auth(token), json=payload)

    assert response.status_code == 200
    assert response.json() == payload
    assert _read_config(app, user_id) == RiskConfig(
        entry_mode=EntryMode.LADDER,
        levels=5,
        weighting=Weighting.MARTINGALE,
        exit_source=ExitSource.CUSTOM,
        stop_pct=Decimal("3.0"),
        tp_pct=Decimal("9.5"),
        risk_pct=Decimal("1.5"),
        leverage=8,
    )


def test_risk_rejects_invalid_levels_and_unknown_enums(client, app):
    token, user_id = _register(client)
    _seed_subscription(app, user_id)
    valid = _risk_json(RiskConfig())

    low_level = client.put(
        "/feeds/7/risk", headers=_auth(token), json={**valid, "levels": 1}
    )
    unknown_mode = client.put(
        "/feeds/7/risk", headers=_auth(token), json={**valid, "entryMode": "last"}
    )

    assert low_level.status_code == 422
    assert unknown_mode.status_code == 422


def test_risk_rejects_invalid_risk_values(client, app):
    token, user_id = _register(client)
    _seed_subscription(app, user_id)

    base = _risk_json(RiskConfig())

    invalid_stop = client.put(
        "/feeds/7/risk",
        headers=_auth(token),
        json={**base, "stopPct": "0"},
    )
    invalid_tp = client.put(
        "/feeds/7/risk",
        headers=_auth(token),
        json={**base, "tpPct": "0"},
    )
    invalid_risk = client.put(
        "/feeds/7/risk",
        headers=_auth(token),
        json={**base, "riskPct": "-1"},
    )
    invalid_leverage = client.put(
        "/feeds/7/risk",
        headers=_auth(token),
        json={**base, "leverage": 0},
    )

    assert invalid_stop.status_code == 422
    assert invalid_tp.status_code == 422
    assert invalid_risk.status_code == 422
    assert invalid_leverage.status_code == 422


def _seed_analyzed_backtest(app, user_id: UUID) -> None:
    with app.state.session_factory() as session:
        backtest_repository.insert_result(
            session,
            user_id,
            7,
            80,
            Decimal("50"),
            Decimal("1"),
            [],
            datetime(2026, 6, 2, tzinfo=timezone.utc),
        )
        feed_repository.set_status(session, user_id, 7, "analyzed")
        session.commit()


def _backtest_state(app, user_id: UUID) -> tuple[bool, str]:
    with app.state.session_factory() as session:
        results = backtest_repository.read_latest_results(session, user_id)
        feed = feed_repository.read_feed(session, user_id, 7)
        return 7 in results, feed.status


def test_risk_change_invalidates_the_backtest(client, app):
    token, user_id = _register(client)
    _seed_subscription(app, user_id)
    _seed_analyzed_backtest(app, user_id)
    payload = _risk_json(RiskConfig(entry_mode=EntryMode.FIRST))

    response = client.put("/feeds/7/risk", headers=_auth(token), json=payload)

    assert response.status_code == 200
    assert _backtest_state(app, user_id) == (False, "verified")


def test_unchanged_risk_config_keeps_the_backtest(client, app):
    token, user_id = _register(client)
    _seed_subscription(app, user_id)
    _seed_analyzed_backtest(app, user_id)

    response = client.put(
        "/feeds/7/risk", headers=_auth(token), json=_risk_json(RiskConfig())
    )

    assert response.status_code == 200
    assert _backtest_state(app, user_id) == (True, "analyzed")


def test_risk_routes_mask_foreign_user(client, app):
    owner, owner_id = _register(client, "owner@example.com")
    other, _other_id = _register(client, "other@example.com")
    _seed_subscription(app, owner_id)

    responses = [
        client.get("/feeds/7/risk", headers=_auth(other)),
        client.put(
            "/feeds/7/risk", headers=_auth(other), json=_risk_json(RiskConfig())
        ),
    ]

    assert owner
    assert [response.status_code for response in responses] == [404, 404]
    assert {response.json()["error"]["code"] for response in responses} == {
        "FEED_NOT_FOUND"
    }


def _risk_json(config: RiskConfig) -> dict:
    return {
        "entryMode": config.entry_mode.value,
        "levels": config.levels,
        "weighting": config.weighting.value,
        "exitSource": config.exit_source.value,
        "stopPct": str(config.stop_pct),
        "tpPct": str(config.tp_pct),
        "riskPct": str(config.risk_pct),
        "leverage": config.leverage,
    }


def _read_config(app, user_id: UUID) -> RiskConfig | None:
    with app.state.session_factory() as session:
        return risk_repository.read_risk_config(session, user_id, 7)
