from uuid import UUID

from verasig.domain.account import Plan
from verasig.services.accounts.tokens import read_user_id
from verasig.storage import account_repository, exchange_repository

SECRET = "s" * 32


class FakeVerifier:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.reject = False

    async def __call__(self, api_key: str, api_secret: str) -> None:
        self.calls.append((api_key, api_secret))
        if self.reject:
            from verasig.foundation.bybit_account import KeyVerificationError

            raise KeyVerificationError


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


def _set_plan(app, user_id: UUID, plan: Plan) -> None:
    with app.state.session_factory() as session:
        account_repository.set_plan(session, user_id, plan)
        session.commit()


def test_exchanges_catalog_starts_disconnected(client):
    token, _user_id = _register(client)

    response = client.get("/exchanges", headers=_auth(token))

    bybit = response.json()["exchanges"][0]
    assert response.status_code == 200
    assert bybit["id"] == "bybit"
    assert bybit["kind"] == "Derivatives · Spot"
    assert bybit["connected"] is False
    assert bybit["account"] is None


def test_observer_cannot_connect_exchange(client):
    token, _user_id = _register(client)

    response = client.post(
        "/exchanges/bybit/connect",
        headers=_auth(token),
        json={"apiKey": "J7n2Kp9XvR4mQ1wL", "apiSecret": "x9Tt3FqLm2Vb8RkD"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PLAN_LIMIT_EXCHANGES"


def test_operator_connects_and_disconnects_bybit(client, app):
    verifier = FakeVerifier()
    app.state.exchange_verifier = verifier
    token, user_id = _register(client)
    _set_plan(app, user_id, Plan.OPERATOR)

    connected = client.post(
        "/exchanges/bybit/connect",
        headers=_auth(token),
        json={"apiKey": "J7n2Kp9XvR4mQ1wL", "apiSecret": "x9Tt3FqLm2Vb8RkD"},
    )
    catalog = client.get("/exchanges", headers=_auth(token))
    disconnected = client.post("/exchanges/bybit/disconnect", headers=_auth(token))
    after = client.get("/exchanges", headers=_auth(token))

    row = _read_connection(app, user_id)
    assert connected.status_code == 200
    assert connected.json()["connected"] is True
    assert connected.json()["account"] == "J7n2…wL · trade-only"
    assert "apiSecret" not in connected.json()
    assert catalog.json()["exchanges"][0]["account"] == "J7n2…wL · trade-only"
    assert row.api_key_encrypted.startswith("v1:")
    assert row.api_secret_encrypted.startswith("v1:")
    assert "J7n2Kp9XvR4mQ1wL" not in row.api_key_encrypted
    assert "x9Tt3FqLm2Vb8RkD" not in row.api_secret_encrypted
    assert verifier.calls == [("J7n2Kp9XvR4mQ1wL", "x9Tt3FqLm2Vb8RkD")]
    assert disconnected.status_code == 200
    assert disconnected.json()["connected"] is False
    assert after.json()["exchanges"][0]["connected"] is False


def test_connect_rejects_bad_exchange_keys(client, app):
    verifier = FakeVerifier()
    verifier.reject = True
    app.state.exchange_verifier = verifier
    token, user_id = _register(client)
    _set_plan(app, user_id, Plan.OPERATOR)

    response = client.post(
        "/exchanges/bybit/connect",
        headers=_auth(token),
        json={"apiKey": "bad-key-value", "apiSecret": "bad-secret-value"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EXCHANGE_KEYS_INVALID"


def _read_connection(app, user_id: UUID):
    with app.state.session_factory() as session:
        row = exchange_repository.read_connections(session, user_id)[0]
        session.expunge(row)
        return row
