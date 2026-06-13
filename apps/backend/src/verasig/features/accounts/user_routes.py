from fastapi import APIRouter, Depends, Request, Response, status

from verasig.domain.account import UserAccount
from verasig.features.accounts.mailer import (
    send_email_confirm,
    send_password_reset_requested,
)
from verasig.features.accounts.profile_schemas import (
    EmailChangeIn,
    EmailConfirmIn,
    RenameUserIn,
    SubscriptionChangeIn,
)
from verasig.features.accounts.tokens import (
    TokenInvalidError,
    issue_email_change_token,
    read_email_change_token,
)
from verasig.features.accounts.user_schemas import UserOut, user_out
from verasig.features.accounts.workflow import (
    PendingEmailMismatchError,
    cancel_subscription,
    change_plan,
    confirm_email_change,
    rename_account,
    request_email_change,
    resume_subscription,
)
from verasig.foundation.http.auth_dependencies import access_token_ttl, get_current_user
from verasig.foundation.http.errors import ApiError

router = APIRouter(prefix="/user")


@router.patch("")
def patch_user(
    request: Request,
    payload: RenameUserIn,
    user: UserAccount = Depends(get_current_user),
) -> UserOut:
    with request.app.state.session_factory() as session:
        updated = rename_account(session, user, payload.first_name, payload.last_name)
        session.commit()
    return user_out(updated)


@router.post("/email")
def request_email(
    request: Request,
    payload: EmailChangeIn,
    user: UserAccount = Depends(get_current_user),
) -> UserOut:
    with request.app.state.session_factory() as session:
        updated = request_email_change(session, user, payload.email)
        token = issue_email_change_token(
            user.id,
            updated.pending_email,
            request.app.state.jwt_secret,
            access_token_ttl(request),
        )
        send_email_confirm(updated.pending_email, token)
        session.commit()
    return user_out(updated)


@router.post("/email/confirm")
def confirm_email(
    request: Request,
    payload: EmailConfirmIn,
    user: UserAccount = Depends(get_current_user),
) -> UserOut:
    try:
        token_user_id, new_email = read_email_change_token(
            payload.token, request.app.state.jwt_secret
        )
    except TokenInvalidError as error:
        raise ApiError(400, "AUTH_INVALID_TOKEN", "Invalid token") from error
    if token_user_id != user.id:
        raise ApiError(400, "AUTH_INVALID_TOKEN", "Invalid token")
    with request.app.state.session_factory() as session:
        try:
            updated = confirm_email_change(session, user, new_email)
        except PendingEmailMismatchError as error:
            raise ApiError(
                400, "EMAIL_CONFIRM_MISMATCH", "Email does not match"
            ) from error
        session.commit()
    return user_out(updated)


@router.post("/password/reset-request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(user: UserAccount = Depends(get_current_user)) -> Response:
    send_password_reset_requested(user.email)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post("/subscription/change")
def change_subscription(
    request: Request,
    payload: SubscriptionChangeIn,
    user: UserAccount = Depends(get_current_user),
) -> UserOut:
    with request.app.state.session_factory() as session:
        updated = change_plan(session, user, payload.plan)
        session.commit()
    return user_out(updated)


@router.post("/subscription/cancel")
def cancel_user_subscription(
    request: Request, user: UserAccount = Depends(get_current_user)
) -> UserOut:
    with request.app.state.session_factory() as session:
        updated = cancel_subscription(session, user)
        session.commit()
    return user_out(updated)


@router.post("/subscription/resume")
def resume_user_subscription(
    request: Request, user: UserAccount = Depends(get_current_user)
) -> UserOut:
    with request.app.state.session_factory() as session:
        updated = resume_subscription(session, user)
        session.commit()
    return user_out(updated)
