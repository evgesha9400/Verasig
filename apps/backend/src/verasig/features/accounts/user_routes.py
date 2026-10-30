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
)
from verasig.features.accounts.tokens import (
    TokenInvalidError,
    issue_email_change_token,
    read_email_change_token,
)
from verasig.features.accounts.user_schemas import UserOut, user_out
from verasig.features.accounts.workflow import (
    EmailTakenError,
    PendingEmailMismatchError,
    cancel_email_change,
    confirm_email_change,
    rename_account,
    request_email_change,
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
        try:
            updated = rename_account(
                session, user, payload.first_name, payload.last_name
            )
        except ValueError as error:
            raise ApiError(422, "INVALID_ACCOUNT_NAME", str(error)) from error
        session.commit()
    return user_out(updated)


@router.post("/email")
def request_email(
    request: Request,
    payload: EmailChangeIn,
    user: UserAccount = Depends(get_current_user),
) -> UserOut:
    with request.app.state.session_factory() as session:
        try:
            updated = request_email_change(session, user, payload.email)
        except EmailTakenError as error:
            raise ApiError(
                409, "AUTH_EMAIL_TAKEN", "Email is already registered"
            ) from error
        token = issue_email_change_token(
            user.id,
            updated.pending_email,
            request.app.state.jwt_secret,
            access_token_ttl(request),
        )
        send_email_confirm(updated.pending_email, token)
        session.commit()
    return user_out(updated)


@router.delete("/email")
@router.post("/email/cancel")
def cancel_email(
    request: Request, user: UserAccount = Depends(get_current_user)
) -> UserOut:
    with request.app.state.session_factory() as session:
        updated = cancel_email_change(session, user)
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
        except EmailTakenError as error:
            raise ApiError(
                409, "AUTH_EMAIL_TAKEN", "Email is already registered"
            ) from error
        session.commit()
    return user_out(updated)


@router.post("/password/reset-request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(user: UserAccount = Depends(get_current_user)) -> Response:
    send_password_reset_requested(user.email)
    return Response(status_code=status.HTTP_202_ACCEPTED)
