from pydantic import Field

from verasig.foundation.http.schemas import CamelModel


class ParserOverlayData(CamelModel):
    instrument_aliases: dict[str, str] = Field(default_factory=dict)
    direction_tokens: dict[str, str] = Field(default_factory=dict)
    reject_phrases: list[str] = Field(default_factory=list)
    template_thresholds: dict[str, float] = Field(default_factory=dict)


class ParserOverlayBody(CamelModel):
    overlay: ParserOverlayData
