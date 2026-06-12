from datetime import timedelta
from uuid import uuid4

import pytest

from verasig.services.accounts.tokens import (
    TokenInvalidError,
    issue_email_change_token,
    issue_token,
    read_email_change_token,
    read_user_id,
)

SECRET = "s" * 32


def test_access_token_round_trips_user_id():
    user_id = uuid4()
    token = issue_token(user_id, SECRET, timedelta(minutes=5))

    assert read_user_id(token, SECRET) == user_id


def test_access_token_rejects_expired_or_garbage_token():
    expired = issue_token(uuid4(), SECRET, timedelta(seconds=-1))

    with pytest.raises(TokenInvalidError):
        read_user_id(expired, SECRET)
    with pytest.raises(TokenInvalidError):
        read_user_id("not-a-token", SECRET)


def test_email_change_token_round_trips_user_id_and_new_email():
    user_id = uuid4()
    token = issue_email_change_token(
        user_id, "next@example.com", SECRET, timedelta(minutes=5)
    )

    assert read_email_change_token(token, SECRET) == (user_id, "next@example.com")


def test_token_purpose_mismatch_is_rejected():
    user_id = uuid4()
    access = issue_token(user_id, SECRET, timedelta(minutes=5))
    email_change = issue_email_change_token(
        user_id, "next@example.com", SECRET, timedelta(minutes=5)
    )

    with pytest.raises(TokenInvalidError):
        read_email_change_token(access, SECRET)
    with pytest.raises(TokenInvalidError):
        read_user_id(email_change, SECRET)
