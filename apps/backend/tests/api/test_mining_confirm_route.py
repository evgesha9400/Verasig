"""Mining Confirm endpoint end-to-end (ADR 0015, miner-based).

POST /feeds/{id}/mining/confirm re-mines the feed's stored messages, persists the
accepted template families' signals into the SAME rows the Signals view reads,
marks the feed verified server-side, and thereby unlocks Check gaps.
"""

from conftest import (
    _auth,
    _backfill_to_done,
    _connect_and_subscribe,
    _mined_keys,
)
from conftest import (
    _register_token as _register,
)
from fakes import FakeSource
from fakes import channel as _channel
from fakes import messages as _messages


def _set_feed_status(app, token: str, status: str) -> None:
    from verasig.features.accounts.tokens import read_user_id
    from verasig.features.feeds import feed_repository

    user_id = read_user_id(token, app.state.jwt_secret)
    with app.state.session_factory() as session:
        feed_repository.set_status(session, user_id, 7, status)
        session.commit()


def test_confirm_persists_signals_and_marks_verified(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))
    keys = _mined_keys(client, app, token)

    response = client.post(
        "/feeds/7/mining/confirm",
        headers=_auth(token),
        json={"acceptedTemplateKeys": keys},
    )
    listed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]

    assert response.status_code == 200
    body = response.json()
    assert body["feedStatus"] == "verified"
    assert body["templatesAccepted"] == len(keys)
    assert body["signalsExtracted"] == 2  # the two LONG signals, not the chatter
    assert listed["status"] == "verified"


def test_confirmed_signals_are_readable_via_the_signals_view(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))
    keys = _mined_keys(client, app, token)

    client.post(
        "/feeds/7/mining/confirm",
        headers=_auth(token),
        json={"acceptedTemplateKeys": keys},
    )
    signals = client.get("/signals?feedId=7", headers=_auth(token)).json()["signals"]

    symbols = sorted(signal["symbol"] for signal in signals)
    assert symbols == ["BTCUSDT", "ETHUSDT"]
    assert all(signal["side"] == "LONG" for signal in signals)


def test_confirm_with_no_accepted_keys_persists_nothing(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))

    response = client.post(
        "/feeds/7/mining/confirm",
        headers=_auth(token),
        json={"acceptedTemplateKeys": []},
    )
    signals = client.get("/signals?feedId=7", headers=_auth(token)).json()["signals"]

    assert response.status_code == 200
    assert response.json()["signalsExtracted"] == 0
    assert response.json()["feedStatus"] == "verified"  # still verified
    assert signals == []


def test_confirm_with_unknown_keys_persists_nothing(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))

    response = client.post(
        "/feeds/7/mining/confirm",
        headers=_auth(token),
        json={"acceptedTemplateKeys": ["tpl_does_not_exist"]},
    )

    assert response.status_code == 200
    assert response.json()["templatesAccepted"] == 0
    assert response.json()["signalsExtracted"] == 0


def test_reconfirm_same_keys_is_idempotent(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))
    keys = _mined_keys(client, app, token)

    client.post(
        "/feeds/7/mining/confirm",
        headers=_auth(token),
        json={"acceptedTemplateKeys": keys},
    )
    client.post(
        "/feeds/7/mining/confirm",
        headers=_auth(token),
        json={"acceptedTemplateKeys": keys},
    )
    signals = client.get("/signals?feedId=7", headers=_auth(token)).json()["signals"]

    assert len(signals) == 2  # not doubled


def test_confirm_conflicts_while_backfilling(client, app):
    token = _register(client)
    _connect_and_subscribe(client, app, token, FakeSource(_channel(), _messages()))
    _set_feed_status(app, token, "backfilling")

    response = client.post(
        "/feeds/7/mining/confirm",
        headers=_auth(token),
        json={"acceptedTemplateKeys": []},
    )

    assert response.status_code == 409


def test_confirm_unlocks_check_gaps(client, app):
    token = _register(client)
    _backfill_to_done(
        client, app, token, FakeSource(_channel(), _messages(), live_ids={1, 2, 3})
    )

    before = client.post("/feeds/7/deletion-rescan", headers=_auth(token))
    client.post(
        "/feeds/7/mining/confirm",
        headers=_auth(token),
        json={"acceptedTemplateKeys": []},
    )
    after = client.post("/feeds/7/deletion-rescan", headers=_auth(token))

    assert before.status_code == 409  # DELETION_RESCAN_NOT_READY before confirm
    assert after.status_code == 202  # confirm marked verified -> unlocked


def test_confirm_on_foreign_feed_is_404(client, app):
    token = _register(client)
    response = client.post(
        "/feeds/999/mining/confirm",
        headers=_auth(token),
        json={"acceptedTemplateKeys": []},
    )
    assert response.status_code == 404
