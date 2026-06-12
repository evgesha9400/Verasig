from verasig.api.schemas.common import CamelModel


class TelegramConnectIn(CamelModel):
    api_id: int
    api_hash: str
    phone: str


class TelegramVerifyIn(CamelModel):
    code: str


class TelegramStatusOut(CamelModel):
    connected: bool
    phone: str | None


class TelegramVerifyOut(CamelModel):
    connected: bool
