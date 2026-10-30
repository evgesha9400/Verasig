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
from verasig.features.accounts.plans import PAYING_STATUSES
from verasig.features.billing import repository

logger = logging.getLogger(__name__)

TRIAL_DAYS = 7
_FOR_SALE = frozenset({Plan.TRADER})
# Provisional status from a completed Checkout. Stripe reports a trial Checkout
# as "paid" too (its first invoice is zero), so the exact status (trialing) comes
# from customer.subscription.created, which may arrive before or after.
_CHECKOUT_STATUS_BY_PAYMENT = {"paid": "active", "no_payment_required": "active"}
# Terminal Stripe statuses: such a subscription never changes again.
_ENDED_STATUSES = frozenset({"canceled", "incomplete_expired"})
# Payload shapes change only between named Stripe releases ("endive"); the
# handlers read the shape of the release the stripe SDK is pinned to.
_API_RELEASE = stripe.api_version.rpartition(".")[2]

_Handler = Callable[[Session, Settings, dict, datetime], None]


class PlanNotForSaleError(Exception):
    """Raised when Checkout is asked for a plan that cannot be bought."""


class AlreadySubscribedError(Exception):
    """Raised when a user with a live subscription starts another Checkout."""


class NoBillingCustomerError(Exception):
    """Raised when the portal is opened before the user has a Stripe customer."""


class WebhookSignatureError(Exception):
    """Raised when a webhook body is not signed with our webhook secret."""


class WebhookApiVersionError(Exception):
    """Raised when a webhook event comes from another Stripe API release."""


def start_checkout(
    session: Session, settings: Settings, user: UserAccount, plan: Plan, interval: str
) -> tuple[str, str]:
    """Create a Stripe Checkout Session; returns its (url, id)."""
    if plan not in _FOR_SALE:
        raise PlanNotForSaleError(plan)
    price_id = settings.stripe_trader_price_spec(interval)
    api_key = settings.stripe_secret_key_spec()
    site_url = settings.site_url_spec()
    # Locked so two clicks cannot both pass the checks below.
    account = repository.lock_by_id(session, user.id)
    # A past-due subscription is still live: it is fixed in the portal, not
    # replaced by a second one.
    if account.subscription_status not in {None, *_ENDED_STATUSES}:
        raise AlreadySubscribedError(account.id)
    # Only one Checkout may be open, so a second tab cannot start a second
    # subscription. A completed or expired session cannot be expired again.
    if account.stripe_checkout_session_id:
        try:
            stripe.checkout.Session.expire(
                account.stripe_checkout_session_id, api_key=api_key
            )
        except stripe.InvalidRequestError:
            pass
    metadata = {"user_id": str(account.id), "plan": plan.value}
    subscription_data: dict = {"metadata": metadata}
    # One trial per customer: a Stripe customer exists once a Checkout completed.
    if account.stripe_customer_id is None:
        subscription_data["trial_period_days"] = TRIAL_DAYS
    customer = (
        {"customer": account.stripe_customer_id}
        if account.stripe_customer_id
        else {"customer_email": account.email}
    )
    checkout = stripe.checkout.Session.create(
        api_key=api_key,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        payment_method_collection="always",
        subscription_data=subscription_data,
        client_reference_id=str(account.id),
        metadata=metadata,
        success_url=(
            f"{site_url}/app?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
        ),
        cancel_url=f"{site_url}/app?checkout=cancelled",
        **customer,
    )
    repository.set_checkout_session(session, account.id, checkout.id)
    return checkout.url, checkout.id


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
    api_version = event.get("api_version") or ""
    if api_version.rpartition(".")[2] != _API_RELEASE:
        raise WebhookApiVersionError(
            f"Stripe event API version {api_version or 'unknown'} is not from the "
            f"{_API_RELEASE} release; set the webhook endpoint to an "
            f"{_API_RELEASE} version"
        )
    handler = _HANDLERS.get(event["type"])
    logger.info(
        "billing webhook %s %s handled=%s", event["type"], event["id"], bool(handler)
    )
    if handler is not None:
        event_at = datetime.fromtimestamp(event["created"], tz=UTC)
        handler(session, settings, event["data"]["object"], event_at)


# --- event handlers ---------------------------------------------------------
#
# Stripe delivers events out of order and retries them for days. Every handler
# skips an event older than the last one applied to the account (same-second
# events all apply: Stripe stamps a Checkout's events with one second).


def _checkout_completed(
    session: Session, _settings: Settings, checkout: dict, event_at: datetime
) -> None:
    plan = _plan_from_metadata(checkout.get("metadata") or {})
    subscription_id = checkout.get("subscription")
    user_id = _parse_uuid(checkout.get("client_reference_id"))
    if plan is None or not subscription_id or user_id is None:
        logger.warning("billing checkout %s is not a Verasig plan", checkout.get("id"))
        return
    account = repository.lock_by_id(session, user_id)
    if account is None or _is_stale(account, event_at):
        return
    if not _accepts_subscription(account, subscription_id):
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
        event_at=event_at,
    )


def _subscription_created(
    session: Session, settings: Settings, subscription: dict, event_at: datetime
) -> None:
    account = _current_subscriber(session, subscription["id"])
    if account is None:
        # Not linked yet: Checkout put the user id in the subscription metadata.
        account = _metadata_subscriber(session, subscription)
    if account is not None and not _is_stale(account, event_at):
        _apply_subscription(session, settings, account, subscription, event_at)


def _subscription_updated(
    session: Session, settings: Settings, subscription: dict, event_at: datetime
) -> None:
    account = _current_subscriber(session, subscription["id"])
    if account is not None and not _is_stale(account, event_at):
        _apply_subscription(session, settings, account, subscription, event_at)


def _apply_subscription(
    session: Session,
    settings: Settings,
    account: UserAccount,
    subscription: dict,
    event_at: datetime,
) -> None:
    repository.save_subscription(
        session,
        account.id,
        plan=_plan_for_price(settings, subscription),
        status=subscription["status"],
        customer_id=subscription.get("customer") or account.stripe_customer_id,
        subscription_id=subscription["id"],
        cancel_at=_cancel_at(subscription),
        event_at=event_at,
    )


def _subscription_deleted(
    session: Session, _settings: Settings, subscription: dict, event_at: datetime
) -> None:
    account = _current_subscriber(session, subscription["id"])
    if account is None or _is_stale(account, event_at):
        return
    # The ended subscription id stays stored: a replayed Checkout event for it
    # is then recognised and ignored (see _accepts_subscription).
    repository.save_subscription(
        session,
        account.id,
        plan=Plan.FREE,
        status=subscription["status"],
        customer_id=account.stripe_customer_id,
        subscription_id=account.stripe_subscription_id,
        cancel_at=None,
        event_at=event_at,
    )


def _invoice_handler(status: str) -> _Handler:
    def handle(
        session: Session, _settings: Settings, invoice: dict, event_at: datetime
    ) -> None:
        details = (invoice.get("parent") or {}).get("subscription_details") or {}
        account = _current_subscriber(session, details.get("subscription"))
        if account is None or _is_stale(account, event_at):
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
            event_at=event_at,
        )

    return handle


_HANDLERS: dict[str, _Handler] = {
    "checkout.session.completed": _checkout_completed,
    "customer.subscription.created": _subscription_created,
    "customer.subscription.updated": _subscription_updated,
    "customer.subscription.deleted": _subscription_deleted,
    "invoice.paid": _invoice_handler("active"),
    "invoice.payment_failed": _invoice_handler("past_due"),
}


# --- helpers ----------------------------------------------------------------


def _is_stale(account: UserAccount, event_at: datetime) -> bool:
    return account.stripe_event_at is not None and event_at < account.stripe_event_at


def _current_subscriber(
    session: Session, subscription_id: str | None
) -> UserAccount | None:
    """The account whose live subscription this is; None for stale or ended ones."""
    if not subscription_id:
        return None
    account = repository.lock_by_subscription_id(session, subscription_id)
    if account is None or account.subscription_status in _ENDED_STATUSES:
        return None
    return account


def _metadata_subscriber(session: Session, subscription: dict) -> UserAccount | None:
    metadata = subscription.get("metadata") or {}
    user_id = _parse_uuid(metadata.get("user_id"))
    if _plan_from_metadata(metadata) is None or user_id is None:
        return None
    account = repository.lock_by_id(session, user_id)
    if account is None or not _accepts_subscription(account, subscription["id"]):
        return None
    return account


def _accepts_subscription(account: UserAccount, subscription_id: str) -> bool:
    """A redelivery of the paying subscription, or a new one replacing a lapsed one."""
    if not account.stripe_subscription_id:
        return True
    paying = account.subscription_status in PAYING_STATUSES
    if subscription_id == account.stripe_subscription_id:
        return paying
    if paying:
        # Stripe bills this one, but the account keeps its current subscription.
        logger.error(
            "billing subscription %s ignored: user %s already pays through %s",
            subscription_id,
            account.id,
            account.stripe_subscription_id,
        )
    return not paying


def _plan_from_metadata(metadata: dict) -> Plan | None:
    try:
        plan = Plan(metadata.get("plan"))
    except ValueError:
        return None
    return plan if plan in _FOR_SALE else None


def _plan_for_price(settings: Settings, subscription: dict) -> Plan:
    """The plan a subscription's price buys; an unknown price buys nothing."""
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
        logger.error(
            "billing subscription %s has unknown price %s", subscription["id"], price_id
        )
        return Plan.FREE
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
