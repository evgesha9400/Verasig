import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
import stripe
from conftest import (
    SITE_URL,
    STRIPE_PRICE_TRADER_MONTHLY,
    STRIPE_PRICE_TRADER_YEARLY,
    STRIPE_WEBHOOK_SECRET,
    _auth,
)
from conftest import _register_user as _register
from stripe import WebhookSignature

from verasig.features.accounts import repository as account_repository

_PERIOD_END = 1_798_761_600  # 2027-01-01T00:00:00Z


# --- Stripe payload builders ---------------------------------------------


def _event(event_type: str, obj: dict) -> str:
    return json.dumps(
        {
            "id": f"evt_{event_type}",
            "object": "event",
            "type": event_type,
            "data": {"object": obj},
        }
    )


def _checkout_session(
    user_id,
    subscription_id: str = "sub_1",
    customer_id: str = "cus_1",
    payment_status: str = "no_payment_required",
    plan: str | None = "trader",
) -> dict:
    return {
        "id": "cs_test_1",
        "object": "checkout.session",
        "mode": "subscription",
        "client_reference_id": str(user_id),
        "customer": customer_id,
        "subscription": subscription_id,
        "payment_status": payment_status,
        "status": "complete",
        "metadata": {"user_id": str(user_id), "plan": plan} if plan else {},
    }


def _subscription(
    subscription_id: str = "sub_1",
    status: str = "active",
    price_id: str = STRIPE_PRICE_TRADER_MONTHLY,
    cancel_at_period_end: bool = False,
    cancel_at: int | None = None,
) -> dict:
    return {
        "id": subscription_id,
        "object": "subscription",
        "customer": "cus_1",
        "status": status,
        "cancel_at_period_end": cancel_at_period_end,
        "cancel_at": cancel_at,
        "items": {
            "object": "list",
            "data": [
                {
                    "id": "si_1",
                    "object": "subscription_item",
                    "price": {"id": price_id, "object": "price"},
                    "current_period_end": _PERIOD_END,
                }
            ],
        },
    }


def _invoice(subscription_id: str = "sub_1") -> dict:
    return {
        "id": "in_1",
        "object": "invoice",
        "customer": "cus_1",
        "parent": {
            "type": "subscription_details",
            "subscription_details": {"subscription": subscription_id},
        },
    }


def _post_event(client, payload: str, secret: str = STRIPE_WEBHOOK_SECRET):
    header = WebhookSignature.generate_signature_header(payload, secret)
    return client.post(
        "/billing/webhook",
        content=payload,
        headers={"stripe-signature": header, "content-type": "application/json"},
    )


def _me(client, token: str) -> dict:
    return client.get("/auth/me", headers=_auth(token)).json()


def _account(app, user_id):
    with app.state.session_factory() as session:
        return account_repository.find_by_id(session, user_id)


def _subscribe(client, user_id, subscription_id: str = "sub_1") -> None:
    payload = _event(
        "checkout.session.completed",
        _checkout_session(user_id, subscription_id=subscription_id),
    )
    assert _post_event(client, payload).status_code == 200


# --- Webhook signature -----------------------------------------------------


def test_webhook_rejects_a_missing_signature(client):
    response = client.post("/billing/webhook", content=_event("ping", {}))

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BILLING_WEBHOOK_SIGNATURE"


def test_webhook_rejects_a_bad_signature(client):
    token, user_id = _register(client)
    payload = _event("checkout.session.completed", _checkout_session(user_id))

    response = _post_event(client, payload, secret="whsec_wrong")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BILLING_WEBHOOK_SIGNATURE"
    assert _me(client, token)["plan"] == "free"


def test_webhook_fails_loudly_without_a_webhook_secret(client, app):
    app.state.settings = app.state.settings.model_copy(
        update={"stripe_webhook_secret": ""}
    )

    response = _post_event(client, _event("ping", {}))

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "BILLING_NOT_CONFIGURED"
    assert "VERASIG_STRIPE_WEBHOOK_SECRET" in response.json()["error"]["message"]


def test_webhook_acknowledges_an_unhandled_event_type(client):
    response = _post_event(client, _event("customer.created", {"id": "cus_1"}))

    assert response.status_code == 200


# --- checkout.session.completed --------------------------------------------


def test_completed_checkout_starts_the_trader_trial(client, app):
    token, user_id = _register(client)

    _subscribe(client, user_id)

    me = _me(client, token)
    account = _account(app, user_id)
    assert me["plan"] == "trader"
    assert me["subscriptionStatus"] == "trialing"
    assert account.stripe_customer_id == "cus_1"
    assert account.stripe_subscription_id == "sub_1"


def test_completed_checkout_paid_upfront_is_active(client):
    token, user_id = _register(client)
    payload = _event(
        "checkout.session.completed",
        _checkout_session(user_id, payment_status="paid"),
    )

    _post_event(client, payload)

    assert _me(client, token)["subscriptionStatus"] == "active"


def test_redelivered_checkout_keeps_the_newer_subscription_status(client):
    token, user_id = _register(client)
    _subscribe(client, user_id)
    _post_event(
        client, _event("customer.subscription.updated", _subscription(status="active"))
    )

    response = _post_event(
        client, _event("checkout.session.completed", _checkout_session(user_id))
    )

    assert response.status_code == 200
    assert _me(client, token)["subscriptionStatus"] == "active"


def test_checkout_without_verasig_plan_metadata_grants_nothing(client):
    token, user_id = _register(client)
    payload = _event(
        "checkout.session.completed", _checkout_session(user_id, plan=None)
    )

    response = _post_event(client, payload)

    assert response.status_code == 200
    assert _me(client, token)["plan"] == "free"


def test_checkout_for_an_unknown_user_is_ignored(client):
    payload = _event(
        "checkout.session.completed",
        _checkout_session("00000000-0000-0000-0000-000000000000"),
    )

    assert _post_event(client, payload).status_code == 200


def test_replayed_checkout_of_an_ended_subscription_stays_free(client):
    token, user_id = _register(client)
    _subscribe(client, user_id)
    _post_event(
        client,
        _event("customer.subscription.deleted", _subscription(status="canceled")),
    )

    _subscribe(client, user_id)

    assert _me(client, token)["plan"] == "free"


def test_checkout_of_a_new_subscription_after_the_old_one_ended(client, app):
    token, user_id = _register(client)
    _subscribe(client, user_id)
    _post_event(
        client,
        _event("customer.subscription.deleted", _subscription(status="canceled")),
    )

    _subscribe(client, user_id, subscription_id="sub_2")

    assert _me(client, token)["plan"] == "trader"
    assert _account(app, user_id).stripe_subscription_id == "sub_2"


def test_checkout_of_a_second_subscription_while_paying_is_ignored(client, app):
    _token, user_id = _register(client)
    _subscribe(client, user_id)

    _subscribe(client, user_id, subscription_id="sub_2")

    assert _account(app, user_id).stripe_subscription_id == "sub_1"


# --- customer.subscription.updated / deleted -------------------------------


def test_cancel_at_period_end_sets_cancel_at_and_resume_clears_it(client):
    token, user_id = _register(client)
    _subscribe(client, user_id)

    _post_event(
        client,
        _event(
            "customer.subscription.updated",
            _subscription(status="trialing", cancel_at_period_end=True),
        ),
    )
    cancelling = _me(client, token)
    _post_event(
        client,
        _event("customer.subscription.updated", _subscription(status="trialing")),
    )
    resumed = _me(client, token)

    assert datetime.fromisoformat(cancelling["cancelAt"]) == datetime.fromtimestamp(
        _PERIOD_END, tz=UTC
    )
    assert cancelling["plan"] == "trader"
    assert resumed["cancelAt"] is None


def test_scheduled_cancel_at_is_mirrored(client):
    token, user_id = _register(client)
    _subscribe(client, user_id)

    _post_event(
        client,
        _event(
            "customer.subscription.updated",
            _subscription(cancel_at=_PERIOD_END - 86_400),
        ),
    )

    assert datetime.fromisoformat(
        _me(client, token)["cancelAt"]
    ) == datetime.fromtimestamp(_PERIOD_END - 86_400, tz=UTC)


def test_past_due_subscription_falls_back_to_free_limits(client):
    token, user_id = _register(client)
    _subscribe(client, user_id)

    _post_event(
        client,
        _event("customer.subscription.updated", _subscription(status="past_due")),
    )

    me = _me(client, token)
    assert me["plan"] == "free"
    assert me["subscriptionStatus"] == "past_due"


def test_yearly_price_maps_to_trader(client, app):
    token, user_id = _register(client)
    _subscribe(client, user_id)

    _post_event(
        client,
        _event(
            "customer.subscription.updated",
            _subscription(price_id=STRIPE_PRICE_TRADER_YEARLY),
        ),
    )

    assert _me(client, token)["plan"] == "trader"


def test_unknown_price_keeps_the_stored_plan(client):
    token, user_id = _register(client)
    _subscribe(client, user_id)

    _post_event(
        client,
        _event("customer.subscription.updated", _subscription(price_id="price_other")),
    )

    assert _me(client, token)["plan"] == "trader"


def test_update_for_a_stale_subscription_is_ignored(client):
    token, user_id = _register(client)
    _subscribe(client, user_id)

    _post_event(
        client,
        _event(
            "customer.subscription.updated",
            _subscription(subscription_id="sub_old", status="past_due"),
        ),
    )

    assert _me(client, token)["subscriptionStatus"] == "trialing"


def test_deleted_subscription_returns_the_user_to_free(client, app):
    token, user_id = _register(client)
    _subscribe(client, user_id)

    response = _post_event(
        client,
        _event("customer.subscription.deleted", _subscription(status="canceled")),
    )

    me = _me(client, token)
    account = _account(app, user_id)
    assert response.status_code == 200
    assert me["plan"] == "free"
    assert me["subscriptionStatus"] == "canceled"
    assert me["cancelAt"] is None
    assert account.plan.value == "free"
    # the customer stays linked so a later checkout and the portal reuse it
    assert account.stripe_customer_id == "cus_1"


def test_late_update_after_deletion_is_ignored(client):
    token, user_id = _register(client)
    _subscribe(client, user_id)
    _post_event(
        client,
        _event("customer.subscription.deleted", _subscription(status="canceled")),
    )

    _post_event(
        client, _event("customer.subscription.updated", _subscription(status="active"))
    )

    me = _me(client, token)
    assert me["plan"] == "free"
    assert me["subscriptionStatus"] == "canceled"


def test_deleted_stale_subscription_is_ignored(client):
    token, user_id = _register(client)
    _subscribe(client, user_id)

    _post_event(
        client,
        _event(
            "customer.subscription.deleted",
            _subscription(subscription_id="sub_old", status="canceled"),
        ),
    )

    assert _me(client, token)["plan"] == "trader"


# --- invoice.paid / invoice.payment_failed ---------------------------------


def test_failed_then_paid_invoice_moves_the_status(client):
    token, user_id = _register(client)
    _subscribe(client, user_id)

    _post_event(client, _event("invoice.payment_failed", _invoice()))
    failed = _me(client, token)
    _post_event(client, _event("invoice.paid", _invoice()))
    paid = _me(client, token)

    assert failed["subscriptionStatus"] == "past_due"
    assert failed["plan"] == "free"
    assert paid["subscriptionStatus"] == "active"
    assert paid["plan"] == "trader"


def test_paid_trial_invoice_keeps_the_trial_status(client):
    token, user_id = _register(client)
    _subscribe(client, user_id)

    _post_event(client, _event("invoice.paid", _invoice()))

    assert _me(client, token)["subscriptionStatus"] == "trialing"


def test_invoice_for_another_subscription_is_ignored(client):
    token, user_id = _register(client)
    _subscribe(client, user_id)

    _post_event(client, _event("invoice.payment_failed", _invoice("sub_other")))

    assert _me(client, token)["subscriptionStatus"] == "trialing"


# --- POST /billing/checkout ------------------------------------------------


@pytest.fixture
def checkout_calls(monkeypatch) -> list[dict]:
    calls: list[dict] = []

    def create(**params):
        calls.append(params)
        return SimpleNamespace(
            id="cs_test_1", url="https://checkout.stripe.com/c/pay/cs_test_1"
        )

    monkeypatch.setattr(stripe.checkout.Session, "create", create)
    return calls


def test_checkout_creates_a_trader_trial_session(client, checkout_calls):
    token, user_id = _register(client)

    response = client.post(
        "/billing/checkout",
        headers=_auth(token),
        json={"plan": "trader", "interval": "month"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "url": "https://checkout.stripe.com/c/pay/cs_test_1",
        "id": "cs_test_1",
    }
    [params] = checkout_calls
    metadata = {"user_id": str(user_id), "plan": "trader"}
    assert params == {
        "api_key": "sk_test_fake",
        "mode": "subscription",
        "line_items": [{"price": STRIPE_PRICE_TRADER_MONTHLY, "quantity": 1}],
        "payment_method_collection": "always",
        "subscription_data": {"trial_period_days": 7, "metadata": metadata},
        "client_reference_id": str(user_id),
        "metadata": metadata,
        "customer_email": "ada@example.com",
        "success_url": (
            f"{SITE_URL}/app?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
        ),
        "cancel_url": f"{SITE_URL}/app?checkout=cancelled",
    }


def test_yearly_checkout_uses_the_yearly_price(client, checkout_calls):
    token, _user_id = _register(client)

    client.post(
        "/billing/checkout",
        headers=_auth(token),
        json={"plan": "trader", "interval": "year"},
    )

    assert checkout_calls[0]["line_items"] == [
        {"price": STRIPE_PRICE_TRADER_YEARLY, "quantity": 1}
    ]


def test_checkout_reuses_the_stored_stripe_customer(client, checkout_calls):
    token, user_id = _register(client)
    _subscribe(client, user_id)
    _post_event(
        client,
        _event("customer.subscription.deleted", _subscription(status="canceled")),
    )

    client.post(
        "/billing/checkout",
        headers=_auth(token),
        json={"plan": "trader", "interval": "month"},
    )

    assert checkout_calls[0]["customer"] == "cus_1"
    assert "customer_email" not in checkout_calls[0]


@pytest.mark.parametrize("plan", ["free", "desk"])
def test_checkout_rejects_plans_that_are_not_for_sale(client, checkout_calls, plan):
    token, _user_id = _register(client)

    response = client.post(
        "/billing/checkout",
        headers=_auth(token),
        json={"plan": plan, "interval": "month"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BILLING_PLAN_NOT_FOR_SALE"
    assert checkout_calls == []


def test_checkout_rejects_a_user_who_is_already_subscribed(client, checkout_calls):
    token, user_id = _register(client)
    _subscribe(client, user_id)

    response = client.post(
        "/billing/checkout",
        headers=_auth(token),
        json={"plan": "trader", "interval": "month"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BILLING_ALREADY_SUBSCRIBED"
    assert checkout_calls == []


def test_checkout_fails_loudly_without_a_price_id(client, app, checkout_calls):
    token, _user_id = _register(client)
    app.state.settings = app.state.settings.model_copy(
        update={"stripe_price_trader_monthly": ""}
    )

    response = client.post(
        "/billing/checkout",
        headers=_auth(token),
        json={"plan": "trader", "interval": "month"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "BILLING_NOT_CONFIGURED"
    assert "VERASIG_STRIPE_PRICE_TRADER_MONTHLY" in response.json()["error"]["message"]
    assert checkout_calls == []


def test_checkout_fails_loudly_without_a_secret_key(client, app, checkout_calls):
    token, _user_id = _register(client)
    app.state.settings = app.state.settings.model_copy(update={"stripe_secret_key": ""})

    response = client.post(
        "/billing/checkout",
        headers=_auth(token),
        json={"plan": "trader", "interval": "month"},
    )

    assert response.status_code == 503
    assert "VERASIG_STRIPE_SECRET_KEY" in response.json()["error"]["message"]
    assert checkout_calls == []


def test_checkout_reports_a_stripe_failure(client, monkeypatch):
    token, _user_id = _register(client)

    def fail(**_params):
        raise stripe.APIConnectionError("network down")

    monkeypatch.setattr(stripe.checkout.Session, "create", fail)

    response = client.post(
        "/billing/checkout",
        headers=_auth(token),
        json={"plan": "trader", "interval": "month"},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "BILLING_PROVIDER_ERROR"


def test_checkout_requires_a_signed_in_user(client):
    response = client.post(
        "/billing/checkout", json={"plan": "trader", "interval": "month"}
    )

    assert response.status_code == 401


# --- POST /billing/portal --------------------------------------------------


@pytest.fixture
def portal_calls(monkeypatch) -> list[dict]:
    calls: list[dict] = []

    def create(**params):
        calls.append(params)
        return SimpleNamespace(url="https://billing.stripe.com/p/session/test_1")

    monkeypatch.setattr(stripe.billing_portal.Session, "create", create)
    return calls


def test_portal_needs_a_stripe_customer(client, portal_calls):
    token, _user_id = _register(client)

    response = client.post("/billing/portal", headers=_auth(token))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BILLING_NO_CUSTOMER"
    assert portal_calls == []


def test_portal_opens_for_the_stored_customer(client, portal_calls):
    token, user_id = _register(client)
    _subscribe(client, user_id)

    response = client.post("/billing/portal", headers=_auth(token))

    assert response.status_code == 200
    assert response.json() == {"url": "https://billing.stripe.com/p/session/test_1"}
    assert portal_calls == [
        {
            "api_key": "sk_test_fake",
            "customer": "cus_1",
            "return_url": f"{SITE_URL}/app",
        }
    ]
