def _register_payload(email: str = "Ada@Example.com") -> dict:
    return {
        "firstName": "Ada",
        "lastName": "Lovelace",
        "email": email,
        "password": "correct horse battery staple",
    }


def _register(client, email: str = "Ada@Example.com") -> dict:
    response = client.post("/auth/register", json=_register_payload(email))
    assert response.status_code == 201
    return response.json()


def test_register_returns_token_and_user(client):
    body = _register(client)

    assert body["token"]
    assert body["user"] == {
        "firstName": "Ada",
        "lastName": "Lovelace",
        "email": "ada@example.com",
        "plan": "observer",
        "pendingEmail": None,
        "cancelAt": None,
    }


def test_register_rejects_duplicate_email(client):
    _register(client)

    response = client.post("/auth/register", json=_register_payload("ada@example.com"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "AUTH_EMAIL_TAKEN"


def test_register_accepts_eight_character_password(client):
    payload = _register_payload()
    payload["password"] = "12345678"

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 201


def test_register_rejects_password_shorter_than_eight_characters(client):
    payload = _register_payload()
    payload["password"] = "short"

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 422


def test_register_rejects_blank_first_name(client):
    payload = _register_payload()
    payload["firstName"] = "   "

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 422


def test_register_rejects_blank_last_name(client):
    payload = _register_payload()
    payload["lastName"] = " "

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 422


def test_register_rejects_one_word_full_name_fallback(client):
    payload = _register_payload()
    payload["firstName"] = "Ada"
    payload["lastName"] = "Ada"

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 422


def test_register_rejects_digits_in_name(client):
    payload = _register_payload()
    payload["firstName"] = "Ada123"

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 422


def test_register_rejects_symbols_in_name(client):
    payload = _register_payload()
    payload["lastName"] = "Lovelace!"

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 422


def test_register_accepts_name_with_punctuation_and_multi_word_surname(client):
    payload = _register_payload()
    payload["firstName"] = "Jean-Luc"
    payload["lastName"] = "de la Cruz"

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 201
    assert response.json()["user"]["firstName"] == "Jean-Luc"
    assert response.json()["user"]["lastName"] == "de la Cruz"


def test_register_normalizes_and_stores_full_name_whitespace(client):
    payload = _register_payload()
    payload["firstName"] = "  Ada   Marie  "
    payload["lastName"] = "  Lovelace   "

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 201
    assert response.json()["user"]["firstName"] == "Ada Marie"
    assert response.json()["user"]["lastName"] == "Lovelace"


def test_login_returns_token_for_valid_credentials(client):
    _register(client)

    response = client.post(
        "/auth/login",
        json={"email": "ADA@example.com", "password": "correct horse battery staple"},
    )

    assert response.status_code == 200
    assert response.json()["token"]
    assert response.json()["user"]["email"] == "ada@example.com"


def test_login_rejects_bad_password(client):
    _register(client)

    response = client.post(
        "/auth/login",
        json={"email": "ada@example.com", "password": "wrong horse battery staple"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


def test_me_returns_current_user_with_token(client):
    registered = _register(client)

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {registered['token']}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "ada@example.com"


def test_me_requires_token(client):
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_logout_is_stateless_no_content(client):
    response = client.post("/auth/logout")

    assert response.status_code == 204
    assert response.content == b""
