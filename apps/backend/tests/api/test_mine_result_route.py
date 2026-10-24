"""Revisioned mine-result endpoint end-to-end (resume source for Verify).

GET /feeds/{id}/mining/result returns the latest current MiningReview, so reopening
a verified feed hydrates Verify from the exact reviewed input. It returns 404
before any mine, after input changes, or for a foreign feed.
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

from verasig.features.mining import mining_review


def _mine_to_done(client, token: str) -> None:
    assert (
        client.post("/feeds/7/mining/preview", headers=_auth(token)).status_code == 202
    )
    with client.stream(
        "GET", "/feeds/7/mining/preview/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())


def test_result_is_404_before_any_mine(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))

    assert client.get("/feeds/7/mining/result", headers=_auth(token)).status_code == 404


def test_result_returns_cached_snapshot_after_mine(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))
    _mine_to_done(client, token)

    response = client.get("/feeds/7/mining/result", headers=_auth(token))

    assert response.status_code == 200
    body = response.json()
    assert body["reviewId"]
    assert body["inputRevision"]
    assert isinstance(body["groups"], list) and len(body["groups"]) >= 1
    assert isinstance(body["messages"], list) and len(body["messages"]) >= 1
    assert body["totalMessages"] == len(body["messages"])
    # Cached in the browser's camelCase wire shape, ready to hydrate directly.
    assert {"templateKey", "count", "suggestedAction"} <= set(body["groups"][0])


def _refresh_to_done(client, app, token: str, source: FakeSource, mode: str) -> None:
    app.state.telegram_source_factory = lambda _link: source
    assert (
        client.post(
            "/feeds/7/backfill",
            headers=_auth(token),
            json={"mode": mode},
        ).status_code
        == 202
    )
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())


def _assert_stale(response) -> None:
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "MINING_REVIEW_STALE"


def test_refresh_stales_the_cached_review(client, app):
    token = _register(client)
    original = _messages()
    _backfill_to_done(client, app, token, FakeSource(_channel(), original))
    _mine_to_done(client, token)

    refreshed = [*original, original[0].model_copy(update={"message_id": 99})]
    _refresh_to_done(
        client,
        app,
        token,
        FakeSource(_channel(), refreshed),
        "refresh",
    )

    _assert_stale(client.get("/feeds/7/mining/result", headers=_auth(token)))


def test_full_recapture_stales_review_even_when_corpus_is_identical(client, app):
    token = _register(client)
    original = _messages()
    _backfill_to_done(client, app, token, FakeSource(_channel(), original))
    _mine_to_done(client, token)

    _refresh_to_done(
        client,
        app,
        token,
        FakeSource(_channel(), original),
        "full",
    )

    _assert_stale(client.get("/feeds/7/mining/result", headers=_auth(token)))


def test_overlay_replacement_stales_the_cached_review(client, app):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))
    _mine_to_done(client, token)

    saved = client.put(
        "/parser-overlay",
        headers=_auth(token),
        json={"overlay": {"rejectPhrases": ["promo"]}},
    )

    assert saved.status_code == 200
    _assert_stale(client.get("/feeds/7/mining/result", headers=_auth(token)))


def test_result_on_foreign_feed_is_404(client, app):
    token = _register(client)
    assert (
        client.get("/feeds/999/mining/result", headers=_auth(token)).status_code == 404
    )


def test_a_miner_upgrade_stales_the_cached_review(client, app, monkeypatch):
    token = _register(client)
    _backfill_to_done(client, app, token, FakeSource(_channel(), _messages()))
    _mine_to_done(client, token)

    monkeypatch.setattr(mining_review, "MINER_VERSION", mining_review.MINER_VERSION + 1)

    _assert_stale(client.get("/feeds/7/mining/result", headers=_auth(token)))
