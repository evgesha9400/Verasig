import logging

import stripe
from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from verasig.config import SettingsError
from verasig.domain.account import UserAccount
from verasig.features.billing.schemas import CheckoutIn, CheckoutOut, PortalOut
from verasig.features.billing.workflow import (
    AlreadySubscribedError,
    NoBillingCustomerError,
    PlanNotForSaleError,
    WebhookApiVersionError,
    WebhookSignatureError,
    handle_webhook,
    open_portal,
    start_checkout,
)
from verasig.foundation.http.auth_dependencies import get_current_user
from verasig.foundation.http.errors import ApiError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing")


@router.post("/checkout")
def checkout(
    request: Request,
    payload: CheckoutIn,
    user: UserAccount = Depends(get_current_user),
) -> CheckoutOut:
    try:
        with request.app.state.session_factory() as session:
            url, session_id = start_checkout(
                session,
                request.app.state.settings,
                user,
                payload.plan,
                payload.interval,
            )
            session.commit()
    except PlanNotForSaleError as error:
        raise ApiError(
            400, "BILLING_PLAN_NOT_FOR_SALE", "This plan cannot be bought"
        ) from error
    except AlreadySubscribedError as error:
        raise ApiError(
            409, "BILLING_ALREADY_SUBSCRIBED", "You already have a subscription"
        ) from error
    except SettingsError as error:
        raise _not_configured(error) from error
    except stripe.StripeError as error:
        raise _provider_error(error) from error
    return CheckoutOut(url=url, id=session_id)


@router.post("/portal")
def portal(
    request: Request, user: UserAccount = Depends(get_current_user)
) -> PortalOut:
    try:
        url = open_portal(request.app.state.settings, user)
    except NoBillingCustomerError as error:
        raise ApiError(
            409, "BILLING_NO_CUSTOMER", "There is no billing account to manage yet"
        ) from error
    except SettingsError as error:
        raise _not_configured(error) from error
    except stripe.StripeError as error:
        raise _provider_error(error) from error
    return PortalOut(url=url)


# Stripe calls this; it is authenticated by the stripe-signature header only.
@router.post("/webhook")
async def webhook(request: Request) -> dict:
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    try:
        await run_in_threadpool(_process_webhook, request, payload, signature)
    except WebhookSignatureError as error:
        raise ApiError(
            400, "BILLING_WEBHOOK_SIGNATURE", "Invalid Stripe signature"
        ) from error
    except WebhookApiVersionError as error:
        logger.error("billing webhook rejected: %s", error)
        raise ApiError(400, "BILLING_WEBHOOK_API_VERSION", str(error)) from error
    except SettingsError as error:
        raise _not_configured(error) from error
    return {"received": True}


def _process_webhook(request: Request, payload: bytes, signature: str | None) -> None:
    with request.app.state.session_factory() as session:
        handle_webhook(session, request.app.state.settings, payload, signature)
        session.commit()


def _not_configured(error: SettingsError) -> ApiError:
    return ApiError(503, "BILLING_NOT_CONFIGURED", str(error))


def _provider_error(error: stripe.StripeError) -> ApiError:
    logger.error("billing stripe request failed: %s", error)
    return ApiError(502, "BILLING_PROVIDER_ERROR", "Stripe could not be reached")
