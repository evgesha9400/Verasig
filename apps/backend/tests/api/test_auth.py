import logging
import re
from datetime import timedelta

from conftest import JWT_SECRET, SITE_URL

from verasig.features.accounts.repository import find_by_email
from verasig.features.accounts.tokens import issue_password_reset_token


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
        "plan": "free",
        "subscriptionStatus": None,
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


def test_register_rejects_malformed_email(client):
    payload = _register_payload()
    payload["email"] = "not-an-email"

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 422


def test_login_rejects_malformed_email(client):
    response = client.post(
        "/auth/login", json={"email": "not-an-email", "password": "whatever"}
    )

    assert response.status_code == 422


def test_register_rejects_password_longer_than_bcrypt_limit(client):
    # bcrypt raises on >72-byte input; reject at the schema edge with 422, not 500.
    payload = _register_payload()
    payload["password"] = "a" * 73

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 422


def test_login_rejects_password_longer_than_bcrypt_limit(client):
    _register(client)

    response = client.post(
        "/auth/login",
        json={"email": "ada@example.com", "password": "a" * 73},
    )

    assert response.status_code == 422


def test_register_rejects_multibyte_password_over_bcrypt_byte_limit(client):
    # 40 characters but 80 UTF-8 bytes: within max_length, over bcrypt's limit.
    payload = _register_payload()
    payload["password"] = "ж" * 40

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 422


def test_login_rejects_multibyte_password_over_bcrypt_byte_limit(client):
    _register(client)

    response = client.post(
        "/auth/login",
        json={"email": "ada@example.com", "password": "ж" * 40},
    )

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


# --- Password reset by email -----------------------------------------------

NEW_PASSWORD = "a brand new passphrase"


class RecordingMailer:
    def __init__(self, error: Exception | None = None):
        self.sent = []
        self._error = error

    def send(self, message) -> None:
        if self._error is not None:
            raise self._error
        self.sent.append(message)


def _mailed_token(mailer: RecordingMailer) -> str:
    text = mailer.sent[-1].get_body(("plain",)).get_content()
    match = re.search(re.escape(SITE_URL) + r"/reset-password\?token=(\S+)", text)
    assert match, text
    return match.group(1)


def _forgot(client, email: str = "ada@example.com"):
    return client.post("/auth/password/forgot", json={"email": email})


def _reset(client, token: str, password: str = NEW_PASSWORD):
    return client.post(
        "/auth/password/reset", json={"token": token, "password": password}
    )


def _login(client, password: str):
    return client.post(
        "/auth/login", json={"email": "ada@example.com", "password": password}
    )


def test_forgot_password_mails_a_reset_link_for_a_known_email(client, app):
    app.state.mailer = mailer = RecordingMailer()
    _register(client)

    response = _forgot(client, "  ADA@example.com ")

    assert response.status_code == 202
    assert response.content == b""
    (message,) = mailer.sent
    assert message["To"] == "ada@example.com"
    assert (
        f"{SITE_URL}/reset-password?token="
        in message.get_body(("plain",)).get_content()
    )


def test_forgot_password_answers_the_same_for_an_unknown_email(client, app):
    app.state.mailer = mailer = RecordingMailer()
    _register(client)

    known = _forgot(client, "ada@example.com")
    unknown = _forgot(client, "nobody@example.com")

    assert (unknown.status_code, unknown.content) == (known.status_code, known.content)
    assert len(mailer.sent) == 1


def test_forgot_password_still_accepts_when_mail_fails(client, app, caplog):
    app.state.mailer = RecordingMailer(error=OSError("smtp down"))
    _register(client)

    # verasig.* loggers do not propagate (configure_app_logging), so attach here
    routes_logger = logging.getLogger("verasig.features.accounts.auth_routes")
    routes_logger.addHandler(caplog.handler)
    try:
        response = _forgot(client)
    finally:
        routes_logger.removeHandler(caplog.handler)

    assert response.status_code == 202
    record = next(
        r for r in caplog.records if r.getMessage() == "password reset email failed"
    )
    assert record.email == "ada@example.com"
    assert "token" not in caplog.text
    assert "token" not in str(vars(record))


def test_reset_password_with_the_mailed_token_changes_the_password(client, app):
    app.state.mailer = mailer = RecordingMailer()
    _register(client)
    _forgot(client)

    response = _reset(client, _mailed_token(mailer))

    assert response.status_code == 204
    assert _login(client, NEW_PASSWORD).status_code == 200
    assert _login(client, "correct horse battery staple").status_code == 401


def test_reset_token_works_only_once(client, app):
    app.state.mailer = mailer = RecordingMailer()
    _register(client)
    _forgot(client)
    token = _mailed_token(mailer)

    assert _reset(client, token).status_code == 204
    response = _reset(client, token, "another new passphrase")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "AUTH_INVALID_TOKEN"
    assert _login(client, NEW_PASSWORD).status_code == 200


def test_reset_token_dies_when_the_password_changes_another_way(client, app):
    app.state.mailer = mailer = RecordingMailer()
    _register(client)
    _forgot(client)
    older = _mailed_token(mailer)
    _forgot(client)
    assert _reset(client, _mailed_token(mailer)).status_code == 204

    response = _reset(client, older, "another new passphrase")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "AUTH_INVALID_TOKEN"


def test_reset_rejects_an_expired_token(client, session_factory):
    _register(client)
    with session_factory() as session:
        account = find_by_email(session, "ada@example.com")
    expired = issue_password_reset_token(
        account.id, account.password_hash, JWT_SECRET, timedelta(seconds=-1)
    )

    response = _reset(client, expired)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "AUTH_INVALID_TOKEN"


def test_reset_rejects_an_access_token(client):
    registered = _register(client)

    response = _reset(client, registered["token"])

    assert response.status_code == 400


def test_reset_rejects_a_short_password(client, app):
    app.state.mailer = mailer = RecordingMailer()
    _register(client)
    _forgot(client)

    response = _reset(client, _mailed_token(mailer), "short")

    assert response.status_code == 422
