from pydantic import Field

from verasig.features.accounts.user_schemas import UserOut
from verasig.foundation.http.schemas import CamelModel


class RegisterIn(CamelModel):
    first_name: str
    last_name: str
    email: str
    password: str = Field(min_length=10)


class LoginIn(CamelModel):
    email: str
    password: str


class AuthOut(CamelModel):
    token: str
    user: UserOut
