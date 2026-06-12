from datetime import UTC, datetime, timedelta

from verasig.services.accounts.tokens import issue_email_change_token, read_user_id

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


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


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


def test_password_reset_request_is_accepted(client):
    registered = _register(client)

    response = client.post(
        "/user/password/reset-request",
        headers=_auth(registered["token"]),
    )

    assert response.status_code == 202


def test_subscription_change_cancel_and_resume(client):
    registered = _register(client)

    changed = client.post(
        "/user/subscription/change",
        headers=_auth(registered["token"]),
        json={"plan": "operator"},
    )
    cancelled = client.post(
        "/user/subscription/cancel",
        headers=_auth(registered["token"]),
    )
    resumed = client.post(
        "/user/subscription/resume",
        headers=_auth(registered["token"]),
    )
    cancel_at = datetime.fromisoformat(cancelled.json()["cancelAt"])

    assert changed.status_code == 200
    assert changed.json()["plan"] == "operator"
    assert cancelled.status_code == 200
    assert cancel_at > datetime.now(tz=UTC) + timedelta(days=29)
    assert resumed.status_code == 200
    assert resumed.json()["cancelAt"] is None


def test_subscription_change_rejects_invalid_plan(client):
    registered = _register(client)

    response = client.post(
        "/user/subscription/change",
        headers=_auth(registered["token"]),
        json={"plan": "invalid"},
    )

    assert response.status_code == 422
