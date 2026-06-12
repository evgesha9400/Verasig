from pydantic import Field

from verasig.api.schemas.common import CamelModel


class ExchangeConnectIn(CamelModel):
    api_key: str = Field(min_length=1)
    api_secret: str = Field(min_length=1)
