"""Mine-result cache endpoint end-to-end (resume source for Verify).

GET /feeds/{id}/mine/result returns the last mine's ``{groups, messages}``
snapshot the runner cached on completion — so reopening a verified feed hydrates
the Verify audit from it instead of re-running the scan. 404 before any mine (or
on a foreign feed), so the client falls back to a live mine.
"""

from conftest import (
    _auth,
    _backfill_to_done,
)
from conftest import (
    _register_token as _register,
)
from fakes import FakeSource
from fakes import channel as _channel
from fakes import messages as _messages


def _mine_to_done(client, token: str) -> None:
    assert client.post("/feeds/7/mine", headers=_auth(token)).status_code == 202
    with client.stream(
        "GET", "/feeds/7/mine/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())


def test_result_is_404_before_any_mine(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))

    assert client.get("/feeds/7/mine/result", headers=_auth(token)).status_code == 404


def test_result_returns_cached_snapshot_after_mine(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))
    _mine_to_done(client, token)

    response = client.get("/feeds/7/mine/result", headers=_auth(token))

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["groups"], list) and len(body["groups"]) >= 1
    assert isinstance(body["messages"], list) and len(body["messages"]) >= 1
    # Cached in the browser's camelCase wire shape, ready to hydrate directly.
    assert {"templateKey", "count", "suggestedAction"} <= set(body["groups"][0])


def test_result_on_foreign_feed_is_404(client, app):
    token = _register(client)
    assert client.get("/feeds/999/mine/result", headers=_auth(token)).status_code == 404
