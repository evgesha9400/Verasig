from pydantic import Field

from verasig.foundation.http.schemas import CamelModel


class ExchangeConnectIn(CamelModel):
    api_key: str = Field(min_length=1)
    api_secret: str = Field(min_length=1)
