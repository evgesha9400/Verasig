import base64
import os

import pytest

from verasig.foundation.security import (
    SecretCipher,
    SecretDecryptError,
    check_password,
    hash_password,
)


def _key() -> str:
    return base64.b64encode(os.urandom(32)).decode()


def test_password_hash_round_trips_and_rejects_wrong_password():
    hashed = hash_password("correct horse battery staple")

    assert check_password("correct horse battery staple", hashed) is True
    assert check_password("wrong horse battery staple", hashed) is False


def test_secret_cipher_encrypts_decrypts_and_stamps_primary_key():
    cipher = SecretCipher.from_spec(f"2026-06:{_key()},2026-01:{_key()}")

    envelope = cipher.encrypt("telegram-session", "user-id:telegram_link")

    assert envelope.startswith("v1:2026-06:")
    assert cipher.decrypt(envelope, "user-id:telegram_link") == "telegram-session"


def test_secret_cipher_rejects_wrong_aad():
    cipher = SecretCipher.from_spec(f"2026-06:{_key()}")
    envelope = cipher.encrypt("telegram-session", "user-id:telegram_link")

    with pytest.raises(SecretDecryptError):
        cipher.decrypt(envelope, "other-user:telegram_link")


def test_secret_cipher_rotates_by_key_id_lookup():
    old_key = _key()
    old_cipher = SecretCipher.from_spec(f"2026-01:{old_key}")
    envelope = old_cipher.encrypt("api-secret", "user-id:exchange:bybit")
    rotated = SecretCipher.from_spec(f"2026-06:{_key()},2026-01:{old_key}")

    assert rotated.decrypt(envelope, "user-id:exchange:bybit") == "api-secret"


@pytest.mark.parametrize(
    "envelope",
    [
        "bad-envelope",
        f"v1:missing:{_key()}:{_key()}",
        f"v2:2026-06:{_key()}:{_key()}",
    ],
)
def test_secret_cipher_rejects_malformed_unknown_or_bad_version(envelope):
    cipher = SecretCipher.from_spec(f"2026-06:{_key()}")

    with pytest.raises(SecretDecryptError):
        cipher.decrypt(envelope, "aad")


def test_secret_cipher_rejects_tampered_ciphertext():
    cipher = SecretCipher.from_spec(f"2026-06:{_key()}")
    envelope = cipher.encrypt("api-secret", "aad")
    version, key_id, nonce, _sealed = envelope.split(":")
    tampered = f"{version}:{key_id}:{nonce}:{_key()}"

    with pytest.raises(SecretDecryptError):
        cipher.decrypt(tampered, "aad")
