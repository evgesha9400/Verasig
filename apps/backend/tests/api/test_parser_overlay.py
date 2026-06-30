def _register(client, email="ada@example.com"):
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


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_overlay_defaults_empty_then_round_trips(client):
    token = _register(client)

    initial = client.get("/parser-overlay", headers=_auth(token))
    assert initial.status_code == 200
    assert initial.json()["overlay"] == {
        "instrumentAliases": {},
        "directionTokens": {},
        "rejectPhrases": [],
        "templateThresholds": {},
    }

    saved = client.put(
        "/parser-overlay",
        headers=_auth(token),
        json={"overlay": {"instrumentAliases": {"АПТ": "APTUSDT"}}},
    )
    assert saved.status_code == 200
    assert saved.json()["overlay"]["instrumentAliases"] == {"АПТ": "APTUSDT"}

    reread = client.get("/parser-overlay", headers=_auth(token))
    assert reread.json()["overlay"]["instrumentAliases"] == {"АПТ": "APTUSDT"}


def test_overlay_is_per_account(client):
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")
    client.put(
        "/parser-overlay",
        headers=_auth(owner),
        json={"overlay": {"rejectPhrases": ["closed"]}},
    )

    assert client.get("/parser-overlay", headers=_auth(other)).json()["overlay"][
        "rejectPhrases"
    ] == []


def test_overlay_requires_auth(client):
    assert client.get("/parser-overlay").status_code == 401
