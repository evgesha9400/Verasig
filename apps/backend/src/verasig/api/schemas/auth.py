from pydantic import Field

from verasig.api.schemas.common import CamelModel
from verasig.api.schemas.user import UserOut


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
