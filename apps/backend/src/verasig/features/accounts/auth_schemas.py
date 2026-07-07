from pydantic import Field, field_validator, model_validator

from verasig.features.accounts.name_validation import (
    validate_account_name,
    validate_account_name_pair,
)
from verasig.features.accounts.user_schemas import UserOut
from verasig.foundation.http.schemas import CamelModel


class RegisterIn(CamelModel):
    first_name: str
    last_name: str
    email: str
    # bcrypt only hashes the first 72 bytes and raises on longer input; reject
    # over-length here so it 422s at the edge instead of 500ing in the hasher.
    password: str = Field(min_length=8, max_length=72)

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
    email: str
    # match register: never pass an over-length password to bcrypt (it raises).
    password: str = Field(max_length=72)


class AuthOut(CamelModel):
    token: str
    user: UserOut
