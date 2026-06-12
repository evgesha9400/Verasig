from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from verasig.domain.risk_config import EntryMode, ExitSource, RiskConfig, Weighting
from verasig.storage.models import ChatRiskConfigRow


def _to_config(row: ChatRiskConfigRow) -> RiskConfig:
    return RiskConfig(
        entry_mode=EntryMode(row.entry_mode),
        levels=row.levels,
        weighting=Weighting(row.weighting),
        exit_source=ExitSource(row.exit_source),
        stop_pct=row.stop_pct,
        tp_pct=row.tp_pct,
        risk_pct=row.risk_pct,
        leverage=row.leverage,
    )


def upsert_risk_config(
    session: Session,
    user_id: UUID,
    channel_id: int,
    config: RiskConfig,
    updated_at: datetime,
) -> RiskConfig:
    row = session.get(ChatRiskConfigRow, (user_id, channel_id))
    if row is None:
        row = ChatRiskConfigRow(user_id=user_id, channel_id=channel_id)
        session.add(row)
    row.entry_mode = config.entry_mode.value
    row.levels = config.levels
    row.weighting = config.weighting.value
    row.exit_source = config.exit_source.value
    row.stop_pct = config.stop_pct
    row.tp_pct = config.tp_pct
    row.risk_pct = config.risk_pct
    row.leverage = config.leverage
    row.updated_at = updated_at
    session.flush()
    return _to_config(row)


def read_risk_config(
    session: Session, user_id: UUID, channel_id: int
) -> RiskConfig | None:
    row = session.get(ChatRiskConfigRow, (user_id, channel_id))
    return _to_config(row) if row else None
