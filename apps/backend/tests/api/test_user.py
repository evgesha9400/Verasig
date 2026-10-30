from datetime import timedelta

from conftest import _auth

from verasig.features.accounts.tokens import issue_email_change_token, read_user_id

SECRET = "s" * 32


def _register(client) -> dict:
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
    return response.json()


def test_patch_user_name_persists(client):
    registered = _register(client)

    response = client.patch(
        "/user",
        headers=_auth(registered["token"]),
        json={"firstName": "Grace", "lastName": "Hopper"},
    )

    assert response.status_code == 200
    assert response.json()["firstName"] == "Grace"
    assert response.json()["lastName"] == "Hopper"


def test_patch_user_name_accepts_partial_first_name(client):
    registered = _register(client)

    response = client.patch(
        "/user",
        headers=_auth(registered["token"]),
        json={"firstName": "Grace"},
    )

    assert response.status_code == 200
    assert response.json()["firstName"] == "Grace"
    assert response.json()["lastName"] == "Lovelace"


def test_patch_user_name_accepts_partial_last_name(client):
    registered = _register(client)

    response = client.patch(
        "/user",
        headers=_auth(registered["token"]),
        json={"lastName": "Hopper"},
    )

    assert response.status_code == 200
    assert response.json()["firstName"] == "Ada"
    assert response.json()["lastName"] == "Hopper"


def test_patch_user_name_rejects_invalid_first_name(client):
    registered = _register(client)

    response = client.patch(
        "/user",
        headers=_auth(registered["token"]),
        json={"firstName": "Ada123", "lastName": "Lovelace"},
    )

    assert response.status_code == 422


def test_patch_user_name_rejects_invalid_last_name(client):
    registered = _register(client)

    response = client.patch(
        "/user",
        headers=_auth(registered["token"]),
        json={"firstName": "Ada", "lastName": "Lovelace!"},
    )

    assert response.status_code == 422


def test_patch_user_name_rejects_equal_first_and_last_name(client):
    registered = _register(client)

    response = client.patch(
        "/user",
        headers=_auth(registered["token"]),
        json={"firstName": "Lovelace", "lastName": "Lovelace"},
    )

    assert response.status_code == 422


def test_patch_user_name_stores_normalized_values(client):
    registered = _register(client)

    response = client.patch(
        "/user",
        headers=_auth(registered["token"]),
        json={"firstName": "  Grace  ", "lastName": " Hopper   "},
    )

    assert response.status_code == 200
    assert response.json()["firstName"] == "Grace"
    assert response.json()["lastName"] == "Hopper"


def test_email_change_sets_pending_and_confirm_applies(client):
    registered = _register(client)

    requested = client.post(
        "/user/email",
        headers=_auth(registered["token"]),
        json={"email": "next@example.com"},
    )
    user_id = read_user_id(registered["token"], SECRET)
    confirm_token = issue_email_change_token(
        user_id, "next@example.com", SECRET, timedelta(minutes=15)
    )
    confirmed = client.post(
        "/user/email/confirm",
        headers=_auth(registered["token"]),
        json={"token": confirm_token},
    )

    assert requested.status_code == 200
    assert requested.json()["email"] == "ada@example.com"
    assert requested.json()["pendingEmail"] == "next@example.com"
    assert confirmed.status_code == 200
    assert confirmed.json()["email"] == "next@example.com"
    assert confirmed.json()["pendingEmail"] is None


def _cancel_pending_email(client, method: str, path: str) -> None:
    registered = _register(client)
    headers = _auth(registered["token"])
    client.post("/user/email", headers=headers, json={"email": "next@example.com"})

    cancelled = client.request(method, path, headers=headers)
    user_id = read_user_id(registered["token"], SECRET)
    stale_token = issue_email_change_token(
        user_id, "next@example.com", SECRET, timedelta(minutes=15)
    )
    confirmed = client.post(
        "/user/email/confirm", headers=headers, json={"token": stale_token}
    )

    assert cancelled.status_code == 200
    assert cancelled.json()["email"] == "ada@example.com"
    assert cancelled.json()["pendingEmail"] is None
    # a confirmation link minted before the cancel no longer applies
    assert confirmed.status_code == 400
    assert confirmed.json()["error"]["code"] == "EMAIL_CONFIRM_MISMATCH"


def test_delete_user_email_cancels_pending_change(client):
    _cancel_pending_email(client, "DELETE", "/user/email")


def test_post_user_email_cancel_cancels_pending_change(client):
    _cancel_pending_email(client, "POST", "/user/email/cancel")


def test_email_change_to_taken_email_returns_409(client):
    registered = _register(client)
    # a second account already owns the target address
    other = client.post(
        "/auth/register",
        json={
            "firstName": "Grace",
            "lastName": "Hopper",
            "email": "taken@example.com",
            "password": "correct horse battery staple",
        },
    )
    assert other.status_code == 201

    response = client.post(
        "/user/email",
        headers=_auth(registered["token"]),
        json={"email": "taken@example.com"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "AUTH_EMAIL_TAKEN"


def test_password_reset_request_is_accepted(client):
    registered = _register(client)

    response = client.post(
        "/user/password/reset-request",
        headers=_auth(registered["token"]),
    )

    assert response.status_code == 202


def test_fake_subscription_routes_are_gone(client):
    registered = _register(client)

    responses = [
        client.post(f"/user/subscription/{action}", headers=_auth(registered["token"]))
        for action in ("change", "cancel", "resume")
    ]

    assert [response.status_code for response in responses] == [404, 404, 404]
