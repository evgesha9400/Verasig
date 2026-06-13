import base64
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fakes import FakeTelegramAuth

from verasig.domain.account import Plan, UserAccount
from verasig.domain.telegram_ports import CodeInvalidError
from verasig.features.accounts import repository as account_repository
from verasig.features.telegram_links import repository as telegram_link_repository
from verasig.features.telegram_links.workflow import connect, status, verify
from verasig.foundation.security.secrets import SecretCipher


def _cipher() -> SecretCipher:
    return SecretCipher.from_spec(f"test:{base64.b64encode(os.urandom(32)).decode()}")


def _account() -> UserAccount:
    return UserAccount(
        id=uuid4(),
        email="user@example.com",
        password_hash="hash",
        first_name="Ada",
        last_name="Lovelace",
        plan=Plan.OBSERVER,
        pending_email=None,
        cancel_at=None,
        created_at=datetime.now(tz=UTC),
    )


@pytest.mark.asyncio
async def test_connect_stores_encrypted_pending_link(db_session):
    account = account_repository.insert_account(db_session, _account())
    auth = FakeTelegramAuth(pending_session="pending-secret")
    cipher = _cipher()

    await connect(
        db_session,
        account.id,
        123,
        "api-secret",
        "+441234568821",
        auth,
        cipher,
    )
    db_session.commit()
    link = telegram_link_repository.read_link(db_session, account.id)

    assert link.status == "pending"
    assert link.api_hash_encrypted.startswith("v1:test:")
    assert link.session_string_encrypted.startswith("v1:test:")
    assert "api-secret" not in link.api_hash_encrypted
    assert "pending-secret" not in link.session_string_encrypted


@pytest.mark.asyncio
async def test_verify_flips_to_connected_and_stores_final_session(db_session):
    account = account_repository.insert_account(db_session, _account())
    auth = FakeTelegramAuth(final_session="final-secret")
    cipher = _cipher()
    await connect(
        db_session, account.id, 123, "api-secret", "+441234568821", auth, cipher
    )

    await verify(db_session, account.id, "12345", auth, cipher)
    db_session.commit()
    link = telegram_link_repository.read_link(db_session, account.id)

    assert link.status == "connected"
    assert (
        cipher.decrypt(link.session_string_encrypted, f"{account.id}:telegram_link")
        == "final-secret"
    )


@pytest.mark.asyncio
async def test_wrong_code_surfaces_error_and_stays_pending(db_session):
    account = account_repository.insert_account(db_session, _account())
    auth = FakeTelegramAuth(valid_code="12345")
    cipher = _cipher()
    await connect(
        db_session, account.id, 123, "api-secret", "+441234568821", auth, cipher
    )

    with pytest.raises(CodeInvalidError):
        await verify(db_session, account.id, "00000", auth, cipher)

    assert (
        telegram_link_repository.read_link(db_session, account.id).status == "pending"
    )


@pytest.mark.asyncio
async def test_status_masks_phone(db_session):
    account = account_repository.insert_account(db_session, _account())
    auth = FakeTelegramAuth()
    cipher = _cipher()
    await connect(
        db_session, account.id, 123, "api-secret", "+441234568821", auth, cipher
    )

    assert status(db_session, account.id) == {
        "connected": False,
        "phone": "+44 •••• 8821",
    }
