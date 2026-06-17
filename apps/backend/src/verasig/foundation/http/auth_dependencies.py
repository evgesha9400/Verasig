from datetime import timedelta

from fastapi import Depends, Header, Query, Request

from verasig.domain.account import UserAccount
from verasig.features.accounts.repository import find_by_id
from verasig.features.accounts.tokens import TokenInvalidError, read_user_id
from verasig.features.sources import feed_repository
from verasig.foundation.http.errors import ApiError
from verasig.storage.models import FeedRow


def access_token_ttl(request: Request) -> timedelta:
    return timedelta(days=request.app.state.settings.jwt_ttl_days)


def _bearer(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def get_current_user(
    request: Request,
    authorization: str | None = Header(None),
    token: str | None = Query(None),
) -> UserAccount:
    raw = token or _bearer(authorization)
    if raw is None:
        raise ApiError(401, "AUTH_REQUIRED", "Missing token")
    try:
        user_id = read_user_id(raw, request.app.state.jwt_secret)
    except TokenInvalidError as error:
        raise ApiError(401, "AUTH_INVALID_TOKEN", "Invalid token") from error
    with request.app.state.session_factory() as session:
        account = find_by_id(session, user_id)
    if account is None:
        raise ApiError(401, "AUTH_UNKNOWN_USER", "Unknown user")
    return account


def require_user_channel(
    chat_id: str,
    request: Request,
    user: UserAccount = Depends(get_current_user),
) -> FeedRow:
    with request.app.state.session_factory() as session:
        subscription = feed_repository.read_feed(session, user.id, int(chat_id))
        if subscription is None:
            raise ApiError(404, "CHAT_NOT_FOUND", "Chat not found")
        session.expunge(subscription)
        return subscription
