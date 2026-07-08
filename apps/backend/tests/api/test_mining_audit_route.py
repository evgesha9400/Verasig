"""Mining Audit endpoint end-to-end (server-side Verify audit).

POST /feeds/{id}/mining/audit re-mines the feed's stored messages, keeps the
accepted template families, and runs them over every message — the SAME
camelCase audit shape the browser used to compute client-side via
applyAcceptedRules. A pure read: unlike confirm, it never touches feed status
or persisted signals.
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


def test_audit_returns_the_browsers_camel_case_shape(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))
    keys = _mined_keys(client, app, token)

    response = client.post(
        "/feeds/7/mining/audit",
        headers=_auth(token),
        json={"acceptedTemplateKeys": keys},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "parsedSignals",
        "ambiguousCandidates",
        "rejectedCandidates",
        "rareTemplates",
        "potentialMisses",
    }
    # The two LONG signals accepted by the mined keys, same count confirm persists.
    assert len(body["parsedSignals"]) == 2
    signal = body["parsedSignals"][0]
    assert {
        "sourceMessageIds",
        "instrument",
        "direction",
        "orderType",
        "entry",
        "stopLoss",
        "takeProfits",
        "confidence",
        "parserRuleId",
        "match",
        "intent",
    } <= set(signal)


def test_audit_with_no_accepted_keys_parses_nothing(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))

    response = client.post(
        "/feeds/7/mining/audit",
        headers=_auth(token),
        json={"acceptedTemplateKeys": []},
    )

    assert response.status_code == 200
    assert response.json()["parsedSignals"] == []


def test_audit_does_not_persist_or_change_feed_status(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))
    keys = _mined_keys(client, app, token)

    client.post(
        "/feeds/7/mining/audit",
        headers=_auth(token),
        json={"acceptedTemplateKeys": keys},
    )

    listed = client.get("/feeds", headers=_auth(token)).json()["feeds"][0]
    signals = client.get("/signals?feedId=7", headers=_auth(token)).json()["signals"]
    assert listed["status"] == "backfilled"  # unchanged — audit never confirms
    assert signals == []  # unchanged — audit never persists


def test_audit_on_foreign_feed_is_404(client, app):
    token = _register(client)
    response = client.post(
        "/feeds/999/mining/audit",
        headers=_auth(token),
        json={"acceptedTemplateKeys": []},
    )
    assert response.status_code == 404
