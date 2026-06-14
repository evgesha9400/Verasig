from fakes import FakeTelegramAuth


def _register(client) -> str:
    response = client.post(
        "/auth/register",
        json={
            "firstName": "Ada",
            "lastName": "Lovelace",
            "email": "ada@example.com",
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201
    return response.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_telegram_status_without_link(client):
    token = _register(client)

    response = client.get("/telegram/status", headers=_auth(token))

    assert response.status_code == 200
    assert response.json() == {"connected": False, "phone": None}


def test_telegram_connect_verify_and_status(client, app):
    app.state.telegram_auth = FakeTelegramAuth(final_session="final-session")
    token = _register(client)

    connected = client.post(
        "/telegram/connect",
        headers=_auth(token),
        json={"apiId": 123, "apiHash": "api-secret", "phone": "+441234568821"},
    )
    verified = client.post(
        "/telegram/verify",
        headers=_auth(token),
        json={"code": "12345"},
    )
    status = client.get("/telegram/status", headers=_auth(token))

    assert connected.status_code == 202
    assert verified.status_code == 200
    assert verified.json() == {"connected": True}
    assert status.json() == {"connected": True, "phone": "+44 •••• 8821"}


def test_telegram_verify_rejects_bad_code(client, app):
    app.state.telegram_auth = FakeTelegramAuth(valid_code="12345")
    token = _register(client)
    client.post(
        "/telegram/connect",
        headers=_auth(token),
        json={"apiId": 123, "apiHash": "api-secret", "phone": "+441234568821"},
    )

    response = client.post(
        "/telegram/verify",
        headers=_auth(token),
        json={"code": "00000"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "TELEGRAM_CODE_INVALID"


def test_telegram_verify_collects_two_factor_password_when_required(client, app):
    app.state.telegram_auth = FakeTelegramAuth(
        valid_code="12345", requires_password=True, valid_password="two-factor-password"
    )
    token = _register(client)
    client.post(
        "/telegram/connect",
        headers=_auth(token),
        json={"apiId": 123, "apiHash": "api-secret", "phone": "+441234568821"},
    )

    requires_password = client.post(
        "/telegram/verify",
        headers=_auth(token),
        json={"code": "12345"},
    )
    invalid_password = client.post(
        "/telegram/verify",
        headers=_auth(token),
        json={"code": "12345", "password": "bad-password"},
    )
    verified = client.post(
        "/telegram/verify",
        headers=_auth(token),
        json={"code": "12345", "password": "two-factor-password"},
    )

    assert requires_password.status_code == 400
    assert requires_password.json()["error"]["code"] == "TELEGRAM_TWO_FACTOR_REQUIRED"
    assert invalid_password.status_code == 400
    assert invalid_password.json()["error"]["code"] == "TELEGRAM_PASSWORD_INVALID"
    assert verified.status_code == 200
    assert verified.json() == {"connected": True}
