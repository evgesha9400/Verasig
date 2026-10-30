"""Stripe subscription billing: Checkout, the customer portal, and the webhook.

Stripe is the single source of truth for a user's paid plan. Checkout and the
portal are Stripe-hosted pages; the webhook is the only writer of the plan, the
subscription status and the Stripe ids on `user_account`.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

import stripe
from sqlalchemy.orm import Session

from verasig.config import Settings
from verasig.domain.account import Plan, UserAccount
from verasig.features.accounts.plans import PAYING_STATUSES, effective_plan
from verasig.features.billing import repository

logger = logging.getLogger(__name__)

TRIAL_DAYS = 7
_FOR_SALE = frozenset({Plan.TRADER})
# Provisional status from a completed Checkout. Stripe reports a trial Checkout
# as "paid" too (its first invoice is zero), so the exact status (trialing) comes
# from customer.subscription.created, which may arrive before or after.
_CHECKOUT_STATUS_BY_PAYMENT = {"paid": "active", "no_payment_required": "active"}
# Stripe never moves a canceled subscription to another status.
_ENDED_STATUS = "canceled"


class PlanNotForSaleError(Exception):
    """Raised when Checkout is asked for a plan that cannot be bought."""


class AlreadySubscribedError(Exception):
    """Raised when a user who already pays starts another Checkout."""


class NoBillingCustomerError(Exception):
    """Raised when the portal is opened before the user has a Stripe customer."""


class WebhookSignatureError(Exception):
    """Raised when a webhook body is not signed with our webhook secret."""


def start_checkout(
    settings: Settings, user: UserAccount, plan: Plan, interval: str
) -> tuple[str, str]:
    """Create a Stripe Checkout Session; returns its (url, id)."""
    if plan not in _FOR_SALE:
        raise PlanNotForSaleError(plan)
    if effective_plan(user) is not Plan.FREE:
        raise AlreadySubscribedError(user.id)
    price_id = settings.stripe_trader_price_spec(interval)
    api_key = settings.stripe_secret_key_spec()
    site_url = settings.site_url_spec()
    metadata = {"user_id": str(user.id), "plan": plan.value}
    customer = (
        {"customer": user.stripe_customer_id}
        if user.stripe_customer_id
        else {"customer_email": user.email}
    )
    session = stripe.checkout.Session.create(
        api_key=api_key,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        payment_method_collection="always",
        subscription_data={"trial_period_days": TRIAL_DAYS, "metadata": metadata},
        client_reference_id=str(user.id),
        metadata=metadata,
        success_url=(
            f"{site_url}/app?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
        ),
        cancel_url=f"{site_url}/app?checkout=cancelled",
        **customer,
    )
    return session.url, session.id


def open_portal(settings: Settings, user: UserAccount) -> str:
    """Create a Stripe customer portal session; returns its url."""
    if not user.stripe_customer_id:
        raise NoBillingCustomerError(user.id)
    portal = stripe.billing_portal.Session.create(
        api_key=settings.stripe_secret_key_spec(),
        customer=user.stripe_customer_id,
        return_url=f"{settings.site_url_spec()}/app",
    )
    return portal.url


def handle_webhook(
    session: Session, settings: Settings, payload: bytes, signature: str | None
) -> None:
    secret = settings.stripe_webhook_secret_spec()
    if not signature:
        raise WebhookSignatureError("missing stripe-signature header")
    try:
        event = stripe.Webhook.construct_event(payload, signature, secret).to_dict()
    except (stripe.SignatureVerificationError, ValueError) as error:
        raise WebhookSignatureError(str(error)) from error
    handler = _HANDLERS.get(event["type"])
    logger.info(
        "billing webhook %s %s handled=%s", event["type"], event["id"], bool(handler)
    )
    if handler is not None:
        handler(session, settings, event["data"]["object"])


# --- event handlers ---------------------------------------------------------


def _checkout_completed(session: Session, _settings: Settings, checkout: dict) -> None:
    plan = _plan_from_metadata(checkout.get("metadata") or {})
    subscription_id = checkout.get("subscription")
    user_id = _parse_uuid(checkout.get("client_reference_id"))
    if plan is None or not subscription_id or user_id is None:
        logger.warning("billing checkout %s is not a Verasig plan", checkout.get("id"))
        return
    account = repository.lock_by_id(session, user_id)
    if account is None or not _accepts_checkout(account, subscription_id):
        return
    redelivered = subscription_id == account.stripe_subscription_id
    repository.save_subscription(
        session,
        account.id,
        plan=plan,
        status=(
            account.subscription_status
            if redelivered
            else _CHECKOUT_STATUS_BY_PAYMENT.get(
                checkout.get("payment_status"), "incomplete"
            )
        ),
        customer_id=checkout.get("customer"),
        subscription_id=subscription_id,
        cancel_at=account.cancel_at if redelivered else None,
    )


def _subscription_created(
    session: Session, settings: Settings, subscription: dict
) -> None:
    account = _current_subscriber(session, subscription["id"])
    if account is None:
        # Not linked yet: Checkout put the user id in the subscription metadata.
        account = _metadata_subscriber(session, subscription)
    if account is not None:
        _apply_subscription(session, settings, account, subscription)


def _subscription_updated(
    session: Session, settings: Settings, subscription: dict
) -> None:
    account = _current_subscriber(session, subscription["id"])
    if account is not None:
        _apply_subscription(session, settings, account, subscription)


def _apply_subscription(
    session: Session, settings: Settings, account: UserAccount, subscription: dict
) -> None:
    repository.save_subscription(
        session,
        account.id,
        plan=_plan_for_price(settings, subscription)
        or _plan_from_metadata(subscription.get("metadata") or {})
        or account.plan,
        status=subscription["status"],
        customer_id=subscription.get("customer") or account.stripe_customer_id,
        subscription_id=subscription["id"],
        cancel_at=_cancel_at(subscription),
    )


def _subscription_deleted(
    session: Session, _settings: Settings, subscription: dict
) -> None:
    account = _current_subscriber(session, subscription["id"])
    if account is None:
        return
    # The ended subscription id stays stored: a replayed Checkout event for it
    # is then recognised and ignored (see _accepts_checkout).
    repository.save_subscription(
        session,
        account.id,
        plan=Plan.FREE,
        status=subscription["status"],
        customer_id=account.stripe_customer_id,
        subscription_id=account.stripe_subscription_id,
        cancel_at=None,
    )


def _invoice_handler(status: str) -> Callable[[Session, Settings, dict], None]:
    def handle(session: Session, _settings: Settings, invoice: dict) -> None:
        details = (invoice.get("parent") or {}).get("subscription_details") or {}
        subscription_id = details.get("subscription")
        account = _current_subscriber(session, subscription_id)
        if account is None:
            return
        # The trial starts with a paid zero invoice; it must not end the trial.
        if status == "active" and account.subscription_status == "trialing":
            return
        repository.save_subscription(
            session,
            account.id,
            plan=account.plan,
            status=status,
            customer_id=account.stripe_customer_id,
            subscription_id=account.stripe_subscription_id,
            cancel_at=account.cancel_at,
        )

    return handle


_HANDLERS: dict[str, Callable[[Session, Settings, dict], None]] = {
    "checkout.session.completed": _checkout_completed,
    "customer.subscription.created": _subscription_created,
    "customer.subscription.updated": _subscription_updated,
    "customer.subscription.deleted": _subscription_deleted,
    "invoice.paid": _invoice_handler("active"),
    "invoice.payment_failed": _invoice_handler("past_due"),
}


# --- helpers ----------------------------------------------------------------


def _current_subscriber(
    session: Session, subscription_id: str | None
) -> UserAccount | None:
    """The account whose live subscription this is; None for stale or ended ones."""
    if not subscription_id:
        return None
    account = repository.lock_by_subscription_id(session, subscription_id)
    if account is None or account.subscription_status == _ENDED_STATUS:
        return None
    return account


def _metadata_subscriber(session: Session, subscription: dict) -> UserAccount | None:
    metadata = subscription.get("metadata") or {}
    user_id = _parse_uuid(metadata.get("user_id"))
    if _plan_from_metadata(metadata) is None or user_id is None:
        return None
    account = repository.lock_by_id(session, user_id)
    if account is None or not _accepts_checkout(account, subscription["id"]):
        return None
    return account


def _accepts_checkout(account: UserAccount, subscription_id: str) -> bool:
    """A redelivery of the paying subscription, or a new one replacing a lapsed one."""
    if not account.stripe_subscription_id:
        return True
    paying = account.subscription_status in PAYING_STATUSES
    return paying if subscription_id == account.stripe_subscription_id else not paying


def _plan_from_metadata(metadata: dict) -> Plan | None:
    try:
        plan = Plan(metadata.get("plan"))
    except ValueError:
        return None
    return plan if plan in _FOR_SALE else None


def _plan_for_price(settings: Settings, subscription: dict) -> Plan | None:
    plans_by_price = {
        price_id: Plan.TRADER
        for price_id in (
            settings.stripe_price_trader_monthly,
            settings.stripe_price_trader_yearly,
        )
        if price_id
    }
    price_id = subscription["items"]["data"][0]["price"]["id"]
    plan = plans_by_price.get(price_id)
    if plan is None:
        logger.warning("billing subscription %s has unknown price", subscription["id"])
    return plan


def _cancel_at(subscription: dict) -> datetime | None:
    if subscription.get("cancel_at"):
        return datetime.fromtimestamp(subscription["cancel_at"], tz=UTC)
    if subscription.get("cancel_at_period_end"):
        period_end = subscription["items"]["data"][0]["current_period_end"]
        return datetime.fromtimestamp(period_end, tz=UTC)
    return None


def _parse_uuid(raw: str | None) -> UUID | None:
    try:
        return UUID(raw) if raw else None
    except ValueError:
        return None
