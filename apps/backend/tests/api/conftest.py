import base64
import os
from uuid import UUID

import pytest
from fakes import FakeTelegramAuth
from fastapi.testclient import TestClient

from verasig.config import Settings
from verasig.entrypoints.api import create_app
from verasig.features.accounts.tokens import read_user_id

# The app fixture below signs tokens with this secret; helpers that decode a
# freshly minted token (register_user) must use the same value.
JWT_SECRET = "s" * 32

# Stripe test settings: fake ids only, no request ever reaches Stripe.
STRIPE_WEBHOOK_SECRET = "whsec_test_secret"
STRIPE_PRICE_TRADER_MONTHLY = "price_trader_monthly"
STRIPE_PRICE_TRADER_YEARLY = "price_trader_yearly"
SITE_URL = "https://verasig.test"


@pytest.fixture
def app(session_factory, pg_url):
    settings = Settings(
        _env_file=None,
        database_url_override=pg_url,
        jwt_secret=JWT_SECRET,
        secret_keys=f"test:{base64.b64encode(os.urandom(32)).decode()}",
        stripe_secret_key="sk_test_fake",
        stripe_webhook_secret=STRIPE_WEBHOOK_SECRET,
        stripe_price_trader_monthly=STRIPE_PRICE_TRADER_MONTHLY,
        stripe_price_trader_yearly=STRIPE_PRICE_TRADER_YEARLY,
        site_url=SITE_URL,
    )
    return create_app(settings, session_factory=session_factory)


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


# --- Shared API-client helpers -------------------------------------------
# Centralized here (imported by tests/api/*.py) so the register/auth/backfill
# scaffolding stops drifting between files.


def _register_token(client, email: str = "ada@example.com") -> str:
    response = client.post(
        "/auth/register",
        json={
            "firstName": "Ada",
            "lastName": "Lovelace",
            "email": email,
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201
    return response.json()["token"]


def _register_user(client, email: str = "ada@example.com") -> tuple[str, UUID]:
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
    return body["token"], read_user_id(body["token"], JWT_SECRET)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _connect_and_subscribe(client, app, token: str, source) -> None:
    app.state.telegram_auth = FakeTelegramAuth()
    client.post(
        "/telegram/connect",
        headers=_auth(token),
        json={"apiId": 123, "apiHash": "api-secret", "phone": "+441234568821"},
    )
    client.post("/telegram/verify", headers=_auth(token), json={"code": "12345"})
    app.state.telegram_source_factory = lambda _link: source
    assert (
        client.post("/feeds", headers=_auth(token), json={"tag": "@pilot"}).status_code
        == 201
    )


def _backfill_to_done(client, app, token: str, source) -> None:
    _connect_and_subscribe(client, app, token, source)
    client.post("/feeds/7/backfill", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backfill/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())


def _mine_review(client, token: str) -> dict:
    assert (
        client.post("/feeds/7/mining/preview", headers=_auth(token)).status_code == 202
    )
    with client.stream(
        "GET", "/feeds/7/mining/preview/progress", headers=_auth(token)
    ) as response:
        "".join(response.iter_text())
    result = client.get("/feeds/7/mining/result", headers=_auth(token))
    assert result.status_code == 200
    return result.json()
