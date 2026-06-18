from fastapi import APIRouter, Depends, Request

from verasig.features.rules.verification import (
    TooFewVerdictsError,
    apply_verdicts,
    verification_samples,
)
from verasig.features.rules.verify_schemas import VerifyIn
from verasig.foundation.http.auth_dependencies import require_feed
from verasig.foundation.http.errors import ApiError

router = APIRouter(prefix="/feeds/{external_id}")


@router.get("/verify/samples")
def samples(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
) -> dict:
    with request.app.state.session_factory() as session:
        return verification_samples(session, subscription.user_id, int(external_id))


@router.post("/verify")
def verify(
    request: Request,
    external_id: str,
    payload: VerifyIn,
    subscription=Depends(require_feed),
) -> dict:
    verdicts = [verdict.model_dump(by_alias=True) for verdict in payload.verdicts]
    try:
        with request.app.state.session_factory() as session:
            passed, misclassified = apply_verdicts(
                session, subscription.user_id, int(external_id), verdicts
            )
            session.commit()
    except TooFewVerdictsError as error:
        raise ApiError(
            400,
            "VERIFY_TOO_FEW_VERDICTS",
            "At least 6 verdicts are required",
        ) from error
    return {"passed": passed, "misclassified": misclassified}
