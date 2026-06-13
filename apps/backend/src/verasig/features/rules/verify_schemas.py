from enum import StrEnum

from verasig.foundation.http.schemas import CamelModel


class VerifyVerdict(StrEnum):
    CORRECT = "correct"
    WRONG = "wrong"


class VerifyVerdictIn(CamelModel):
    message_id: str
    verdict: VerifyVerdict


class VerifyIn(CamelModel):
    verdicts: list[VerifyVerdictIn]
