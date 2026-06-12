from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request

from verasig.api.deps import require_user_channel
from verasig.api.schemas.risk import RiskConfigBody, to_body, to_config
from verasig.domain.risk_config import RiskConfig
from verasig.storage.risk_repository import read_risk_config, upsert_risk_config

router = APIRouter(prefix="/chats/{chat_id}")


@router.get("/risk")
def get_risk(
    request: Request,
    chat_id: str,
    subscription=Depends(require_user_channel),
) -> RiskConfigBody:
    with request.app.state.session_factory() as session:
        config = read_risk_config(session, subscription.user_id, int(chat_id))
    return to_body(config or RiskConfig())


@router.put("/risk")
def put_risk(
    request: Request,
    chat_id: str,
    payload: RiskConfigBody,
    subscription=Depends(require_user_channel),
) -> RiskConfigBody:
    with request.app.state.session_factory() as session:
        config = upsert_risk_config(
            session,
            subscription.user_id,
            int(chat_id),
            to_config(payload),
            datetime.now(tz=UTC),
        )
        session.commit()
    return to_body(config)
