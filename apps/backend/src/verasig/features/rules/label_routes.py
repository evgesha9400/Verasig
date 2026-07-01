from fastapi import APIRouter, Depends, Request, Response, status

from verasig.features.feeds.message_views import read_history
from verasig.features.rules.labeling import (
    label_counts,
    labeling_sample,
    record_label,
)
from verasig.features.rules.message_schemas import LabelIn
from verasig.foundation.http.auth_dependencies import require_feed

router = APIRouter(prefix="/feeds/{external_id}")


@router.get("/messages")
def messages(
    request: Request,
    external_id: str,
    limit: int = 40,
    subscription=Depends(require_feed),
) -> dict:
    with request.app.state.session_factory() as session:
        return {
            "messages": labeling_sample(
                session, subscription.user_id, int(external_id), limit
            )
        }


# The full backfilled history (every message, unfiltered) for the parser-first
# miner, which classifies messages itself rather than reading the labeling deck.
@router.get("/messages/history")
def message_history(
    request: Request,
    subscription=Depends(require_feed),
) -> dict:
    with request.app.state.session_factory() as session:
        return {"messages": read_history(session, subscription)}


@router.post("/messages/{msg_id}/label", status_code=status.HTTP_204_NO_CONTENT)
def label_message(
    request: Request,
    external_id: str,
    msg_id: str,
    payload: LabelIn,
    subscription=Depends(require_feed),
) -> Response:
    with request.app.state.session_factory() as session:
        record_label(
            session, subscription.user_id, int(external_id), int(msg_id), payload.label
        )
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/labels")
def labels(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
) -> dict:
    with request.app.state.session_factory() as session:
        return label_counts(session, subscription.user_id, int(external_id))
