from fastapi import APIRouter, Depends, Request

from verasig.api.deps import require_user_channel
from verasig.api.errors import ApiError
from verasig.api.schemas.verify import VerifyIn
from verasig.services.verification.service import (
    TooFewVerdictsError,
    apply_verdicts,
    verification_samples,
)

router = APIRouter(prefix="/chats/{chat_id}")


@router.get("/verify/samples")
def samples(
    request: Request,
    chat_id: str,
    subscription=Depends(require_user_channel),
) -> dict:
    with request.app.state.session_factory() as session:
        return verification_samples(session, subscription.user_id, int(chat_id))


@router.post("/verify")
def verify(
    request: Request,
    chat_id: str,
    payload: VerifyIn,
    subscription=Depends(require_user_channel),
) -> dict:
    verdicts = [verdict.model_dump(by_alias=True) for verdict in payload.verdicts]
    try:
        with request.app.state.session_factory() as session:
            passed, misclassified = apply_verdicts(
                session, subscription.user_id, int(chat_id), verdicts
            )
            session.commit()
    except TooFewVerdictsError as error:
        raise ApiError(
            400,
            "VERIFY_TOO_FEW_VERDICTS",
            "At least 6 verdicts are required",
        ) from error
    return {"passed": passed, "misclassified": misclassified}
