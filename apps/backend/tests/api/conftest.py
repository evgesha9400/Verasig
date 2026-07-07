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


@pytest.fixture
def app(session_factory, pg_url):
    settings = Settings(
        _env_file=None,
        database_url_override=pg_url,
        jwt_secret=JWT_SECRET,
        secret_keys=f"test:{base64.b64encode(os.urandom(32)).decode()}",
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


def _mined_keys(client, app, token: str) -> list[str]:
    """The template_keys the miner yields for the stored feed — what the client
    reviews and accepts before POSTing confirm. Re-mining the SAME stored messages
    (byte-identical port) yields the SAME keys the browser saw, so the match is
    exact and the test never hardcodes a hash."""
    from verasig.features.feeds import message_repository
    from verasig.features.mining.mining_confirm import _to_chat_message
    from verasig.features.mining.template_mining import mine_template_groups
    from verasig.features.parser_overlay.repository import read_overlay

    user_id = read_user_id(token, app.state.jwt_secret)
    with app.state.session_factory() as session:
        messages = message_repository.read_messages(session, user_id, 7)
        overlay = read_overlay(session, user_id)
    groups = mine_template_groups([_to_chat_message(m) for m in messages], overlay)
    return [group.template_key for group in groups]
