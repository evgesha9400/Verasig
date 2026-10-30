from pydantic import EmailStr, Field, field_validator, model_validator

from verasig.features.accounts.name_validation import (
    validate_account_name,
    validate_account_name_pair,
)
from verasig.features.accounts.user_schemas import UserOut
from verasig.foundation.http.schemas import CamelModel

# bcrypt only hashes the first 72 BYTES and raises on longer input. The limit is
# on UTF-8 bytes, not characters: 72 non-ASCII characters can exceed it.
BCRYPT_MAX_PASSWORD_BYTES = 72


def _require_bcrypt_length(password: str) -> str:
    if len(password.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(
            f"password must be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes in UTF-8"
        )
    return password


class RegisterIn(CamelModel):
    first_name: str
    last_name: str
    email: EmailStr
    # reject over-length here so it 422s at the edge instead of 500ing in the hasher.
    password: str = Field(min_length=8, max_length=BCRYPT_MAX_PASSWORD_BYTES)

    @field_validator("password")
    @classmethod
    def _validate_password_bytes(cls, raw: str) -> str:
        return _require_bcrypt_length(raw)

    @field_validator("first_name")
    @classmethod
    def _validate_first_name(cls, raw: str) -> str:
        return validate_account_name(raw, field_name="first_name")

    @field_validator("last_name")
    @classmethod
    def _validate_last_name(cls, raw: str) -> str:
        return validate_account_name(raw, field_name="last_name")

    @model_validator(mode="after")
    def _validate_distinct_names(self) -> "RegisterIn":
        validate_account_name_pair(self.first_name, self.last_name)
        return self


class LoginIn(CamelModel):
    email: EmailStr
    # match register: never pass an over-length password to bcrypt (it raises).
    password: str = Field(max_length=BCRYPT_MAX_PASSWORD_BYTES)

    @field_validator("password")
    @classmethod
    def _validate_password_bytes(cls, raw: str) -> str:
        return _require_bcrypt_length(raw)


class AuthOut(CamelModel):
    token: str
    user: UserOut
