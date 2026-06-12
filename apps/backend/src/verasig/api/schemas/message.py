from verasig.api.schemas.common import CamelModel
from verasig.domain.label import LabelKind


class LabelIn(CamelModel):
    label: LabelKind
