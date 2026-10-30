from pydantic import field_validator, model_validator

from verasig.features.accounts.name_validation import (
    validate_account_name,
    validate_account_name_pair,
)
from verasig.foundation.http.schemas import CamelModel


class RenameUserIn(CamelModel):
    first_name: str | None = None
    last_name: str | None = None

    @field_validator("first_name")
    @classmethod
    def _validate_first_name(cls, raw: str | None) -> str | None:
        if raw is None:
            return None
        return validate_account_name(raw, field_name="first_name")

    @field_validator("last_name")
    @classmethod
    def _validate_last_name(cls, raw: str | None) -> str | None:
        if raw is None:
            return None
        return validate_account_name(raw, field_name="last_name")

    @model_validator(mode="after")
    def _validate_distinct_names(self) -> "RenameUserIn":
        if self.first_name is None or self.last_name is None:
            return self
        validate_account_name_pair(self.first_name, self.last_name)
        return self


class EmailChangeIn(CamelModel):
    email: str


class EmailConfirmIn(CamelModel):
    token: str
