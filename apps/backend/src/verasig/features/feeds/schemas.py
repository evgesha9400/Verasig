from verasig.features.feeds.backfill_job_run import BackfillMode
from verasig.foundation.http.schemas import CamelModel


class FeedCreateIn(CamelModel):
    tag: str


class BackfillStartIn(CamelModel):
    mode: BackfillMode = BackfillMode.RESUME
