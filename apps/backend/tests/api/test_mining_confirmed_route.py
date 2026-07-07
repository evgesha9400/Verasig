"""Mining Confirmed read endpoint end-to-end (resume source for Verify).

GET /feeds/{id}/mining/confirmed lists the accepted template keys recovered from
persisted Signals (``rule_id`` == ``template_key``) — no re-mine, no migration.
Only signal-bearing families ever appear. Mirrors the confirm-route harness so
the two endpoints share exactly one setup path.
"""

from conftest import (
    _auth,
    _backfill_to_done,
    _mined_keys,
)
from conftest import (
    _register_token as _register,
)
from fakes import FakeSource
from fakes import channel as _channel
from fakes import messages as _messages


def test_confirmed_lists_accepted_keys_after_confirm(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))
    keys = _mined_keys(client, app, token)

    client.post(
        "/feeds/7/mining/confirm",
        headers=_auth(token),
        json={"acceptedTemplateKeys": keys},
    )
    response = client.get("/feeds/7/mining/confirmed", headers=_auth(token))

    assert response.status_code == 200
    confirmed = response.json()["acceptedTemplateKeys"]
    assert confirmed  # signal-bearing families persisted a rule_id to recover
    assert set(confirmed) <= set(keys)  # never a key we did not accept


def test_confirmed_is_empty_before_any_confirm(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))

    response = client.get("/feeds/7/mining/confirmed", headers=_auth(token))

    assert response.status_code == 200
    assert response.json()["acceptedTemplateKeys"] == []


def test_confirmed_is_empty_when_confirm_accepted_no_keys(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))

    client.post(
        "/feeds/7/mining/confirm",
        headers=_auth(token),
        json={"acceptedTemplateKeys": []},
    )
    response = client.get("/feeds/7/mining/confirmed", headers=_auth(token))

    assert response.status_code == 200
    assert response.json()["acceptedTemplateKeys"] == []


def test_confirmed_on_foreign_feed_is_404(client, app):
    token = _register(client)
    response = client.get("/feeds/999/mining/confirmed", headers=_auth(token))
    assert response.status_code == 404
