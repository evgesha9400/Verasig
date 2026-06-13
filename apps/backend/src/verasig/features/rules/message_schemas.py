from verasig.domain.label import LabelKind
from verasig.foundation.http.schemas import CamelModel


class LabelIn(CamelModel):
    label: LabelKind
