import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt


class TokenInvalidError(Exception):
    """Raised when a JWT is expired, malformed, or has the wrong purpose."""


def _issue(claims: dict, purpose: str, secret: str, ttl: timedelta) -> str:
    now = datetime.now(tz=UTC)
    return jwt.encode(
        {**claims, "purpose": purpose, "iat": now, "exp": now + ttl},
        secret,
        algorithm="HS256",
    )


def _read(token: str, purpose: str, secret: str) -> dict:
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.InvalidTokenError as error:
        raise TokenInvalidError() from error
    if claims.get("purpose") != purpose:
        raise TokenInvalidError()
    return claims


def issue_token(user_id: UUID, secret: str, ttl: timedelta) -> str:
    return _issue({"sub": str(user_id)}, "access", secret, ttl)


def read_user_id(token: str, secret: str) -> UUID:
    return UUID(_read(token, "access", secret)["sub"])


def issue_email_change_token(
    user_id: UUID, new_email: str, secret: str, ttl: timedelta
) -> str:
    return _issue(
        {"sub": str(user_id), "new_email": new_email},
        "email-change",
        secret,
        ttl,
    )


def read_email_change_token(token: str, secret: str) -> tuple[UUID, str]:
    claims = _read(token, "email-change", secret)
    return UUID(claims["sub"]), claims["new_email"]


def password_fingerprint(password_hash: str) -> str:
    # binds a reset token to the current password: any password change voids it.
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def issue_password_reset_token(
    user_id: UUID, password_hash: str, secret: str, ttl: timedelta
) -> str:
    return _issue(
        {"sub": str(user_id), "fp": password_fingerprint(password_hash)},
        "password-reset",
        secret,
        ttl,
    )


def read_password_reset_token(token: str, secret: str) -> tuple[UUID, str]:
    claims = _read(token, "password-reset", secret)
    return UUID(claims["sub"]), claims["fp"]
