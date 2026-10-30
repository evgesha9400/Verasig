from typing import Literal

from verasig.domain.account import Plan
from verasig.foundation.http.schemas import CamelModel


class CheckoutIn(CamelModel):
    plan: Plan
    interval: Literal["month", "year"]


class CheckoutOut(CamelModel):
    url: str
    id: str


class PortalOut(CamelModel):
    url: str
