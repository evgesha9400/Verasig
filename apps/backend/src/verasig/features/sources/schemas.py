from verasig.features.sources.backfill_job_run import BackfillMode
from verasig.foundation.http.schemas import CamelModel


class ChatCreateIn(CamelModel):
    tag: str


class BackfillStartIn(CamelModel):
    mode: BackfillMode = BackfillMode.RESUME
