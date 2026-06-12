from fastapi import APIRouter, Depends, Request, Response, status

from verasig.api.deps import require_user_channel
from verasig.api.schemas.message import LabelIn
from verasig.services.labeling.service import (
    label_counts,
    labeling_sample,
    record_label,
)

router = APIRouter(prefix="/chats/{chat_id}")


@router.get("/messages")
def messages(
    request: Request,
    chat_id: str,
    limit: int = 40,
    subscription=Depends(require_user_channel),
) -> dict:
    with request.app.state.session_factory() as session:
        return {
            "messages": labeling_sample(
                session, subscription.user_id, int(chat_id), limit
            )
        }


@router.post("/messages/{msg_id}/label", status_code=status.HTTP_204_NO_CONTENT)
def label_message(
    request: Request,
    chat_id: str,
    msg_id: str,
    payload: LabelIn,
    subscription=Depends(require_user_channel),
) -> Response:
    with request.app.state.session_factory() as session:
        record_label(
            session, subscription.user_id, int(chat_id), int(msg_id), payload.label
        )
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/labels")
def labels(
    request: Request,
    chat_id: str,
    subscription=Depends(require_user_channel),
) -> dict:
    with request.app.state.session_factory() as session:
        return label_counts(session, subscription.user_id, int(chat_id))
