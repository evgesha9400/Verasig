import base64
import os
from binascii import Error as Base64Error

import bcrypt
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def check_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        # bcrypt raises on input over 72 bytes (or a malformed hash): such a
        # password can never have been hashed, so it simply does not match.
        return False


class SecretDecryptError(Exception):
    """Raised when a secret envelope cannot be trusted or decrypted."""


class SecretCipher:
    """AES-GCM envelope encryption over a keyring."""

    ENVELOPE_VERSION = "v1"
    AES_KEY_BYTE_LENGTHS = frozenset((16, 24, 32))

    def __init__(self, keyring: dict[str, bytes], primary_id: str) -> None:
        self._keyring = keyring
        self._primary_id = primary_id

    @classmethod
    def from_spec(cls, spec: str) -> "SecretCipher":
        entries = [entry.strip() for entry in spec.split(",") if entry.strip()]
        pairs: list[tuple[str, str]] = []
        key_ids: set[str] = set()
        for entry in entries:
            if ":" not in entry:
                raise SecretDecryptError("malformed keyring")
            key_id, key = [part.strip() for part in entry.split(":", 1)]
            if not key_id or not key:
                raise SecretDecryptError("malformed keyring")
            if key_id in key_ids:
                raise SecretDecryptError("malformed keyring")
            key_ids.add(key_id)
            pairs.append((key_id, key))
        if not pairs:
            raise SecretDecryptError("empty keyring")
        try:
            keyring = {
                key_id: base64.b64decode(key, validate=True) for key_id, key in pairs
            }
        except (Base64Error, ValueError) as error:
            raise SecretDecryptError("malformed keyring") from error
        if any(len(key) not in cls.AES_KEY_BYTE_LENGTHS for key in keyring.values()):
            raise SecretDecryptError("malformed keyring")
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
            nonce_bytes = base64.b64decode(nonce, validate=True)
            sealed_bytes = base64.b64decode(sealed, validate=True)
            return AESGCM(key).decrypt(nonce_bytes, sealed_bytes, aad.encode()).decode()
        except (Base64Error, InvalidTag, UnicodeDecodeError, ValueError) as error:
            raise SecretDecryptError("aad mismatch or tampered ciphertext") from error
