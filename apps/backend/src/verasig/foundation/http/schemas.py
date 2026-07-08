from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class JobOut(CamelModel):
    """The 202 envelope every background-job start returns: ``{ jobId }``."""

    job_id: str
