import base64
import os
from binascii import Error as Base64Error

import bcrypt
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


class SecretDecryptError(Exception):
    """Raised when a secret envelope cannot be trusted or decrypted."""


class SecretCipher:
    """AES-GCM envelope encryption over a keyring."""

    ENVELOPE_VERSION = "v1"

    def __init__(self, keyring: dict[str, bytes], primary_id: str) -> None:
        self._keyring = keyring
        self._primary_id = primary_id

    @classmethod
    def from_spec(cls, spec: str) -> "SecretCipher":
        try:
            pairs = [
                (key_id.strip(), key.strip())
                for key_id, key in (
                    entry.split(":", 1) for entry in spec.split(",") if entry
                )
            ]
        except ValueError as error:
            raise SecretDecryptError("malformed keyring") from error
        if not pairs:
            raise SecretDecryptError("empty keyring")
        try:
            keyring = {key_id: base64.b64decode(key) for key_id, key in pairs}
        except (Base64Error, ValueError) as error:
            raise SecretDecryptError("malformed keyring") from error
        return cls(keyring, pairs[0][0])

    def encrypt(self, plain: str, aad: str) -> str:
        nonce = os.urandom(12)
        sealed = AESGCM(self._keyring[self._primary_id]).encrypt(
            nonce, plain.encode(), aad.encode()
        )
        return ":".join(
            (
                self.ENVELOPE_VERSION,
                self._primary_id,
                base64.b64encode(nonce).decode(),
                base64.b64encode(sealed).decode(),
            )
        )

    def decrypt(self, envelope: str, aad: str) -> str:
        try:
            version, key_id, nonce, sealed = envelope.split(":")
        except ValueError as error:
            raise SecretDecryptError("malformed envelope") from error
        key = self._keyring.get(key_id)
        if version != self.ENVELOPE_VERSION or key is None:
            raise SecretDecryptError(
                f"unreadable envelope (version={version}, key_id={key_id})"
            )
        try:
            return (
                AESGCM(key)
                .decrypt(
                    base64.b64decode(nonce),
                    base64.b64decode(sealed),
                    aad.encode(),
                )
                .decode()
            )
        except (Base64Error, InvalidTag, UnicodeDecodeError) as error:
            raise SecretDecryptError("aad mismatch or tampered ciphertext") from error
