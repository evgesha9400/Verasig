import logging
from datetime import timedelta
from email.message import EmailMessage

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status

from verasig.domain.account import UserAccount
from verasig.features.accounts.auth_schemas import (
    AuthOut,
    ForgotPasswordIn,
    LoginIn,
    RegisterIn,
    ResetPasswordIn,
)
from verasig.features.accounts.mailer import Mailer, build_password_reset_email
from verasig.features.accounts.tokens import (
    TokenInvalidError,
    issue_password_reset_token,
    issue_token,
    read_password_reset_token,
)
from verasig.features.accounts.user_schemas import UserOut, user_out
from verasig.features.accounts.workflow import (
    EmailTakenError,
    InvalidCredentialsError,
    ResetLinkInvalidError,
    authenticate,
    find_account,
    register_account,
    reset_password,
)
from verasig.foundation.http.auth_dependencies import access_token_ttl, get_current_user
from verasig.foundation.http.errors import ApiError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")

PASSWORD_RESET_TTL = timedelta(minutes=60)


def _auth_response(request: Request, account: UserAccount) -> AuthOut:
    token = issue_token(
        account.id,
        request.app.state.jwt_secret,
        access_token_ttl(request),
    )
    return AuthOut(token=token, user=user_out(account))


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: Request, payload: RegisterIn) -> AuthOut:
    with request.app.state.session_factory() as session:
        try:
            account = register_account(
                session,
                payload.first_name,
                payload.last_name,
                payload.email,
                payload.password,
            )
        except ValueError as error:
            raise ApiError(422, "INVALID_ACCOUNT_NAME", str(error)) from error
        except EmailTakenError as error:
            raise ApiError(
                409, "AUTH_EMAIL_TAKEN", "Email is already registered"
            ) from error
        session.commit()
    return _auth_response(request, account)


@router.post("/login")
def login(request: Request, payload: LoginIn) -> AuthOut:
    with request.app.state.session_factory() as session:
        try:
            account = authenticate(session, payload.email, payload.password)
        except InvalidCredentialsError as error:
            raise ApiError(
                401, "AUTH_INVALID_CREDENTIALS", "Invalid email or password"
            ) from error
    return _auth_response(request, account)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me")
def me(user: UserAccount = Depends(get_current_user)) -> UserOut:
    return user_out(user)


def _send_reset_email(mailer: Mailer, message: EmailMessage) -> None:
    try:
        mailer.send(message)
    except Exception as error:
        # never log the message or the error text: both may carry the reset link.
        logger.error(
            "password reset email failed",
            extra={"email": message["To"], "error_type": type(error).__name__},
        )


@router.post("/password/forgot", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    request: Request, payload: ForgotPasswordIn, background_tasks: BackgroundTasks
) -> Response:
    # same answer for known and unknown emails; mail goes out after the response.
    with request.app.state.session_factory() as session:
        account = find_account(session, payload.email)
    if account is not None:
        token = issue_password_reset_token(
            account.id,
            account.password_hash,
            request.app.state.jwt_secret,
            PASSWORD_RESET_TTL,
        )
        site_url = request.app.state.settings.site_url_spec()
        message = build_password_reset_email(
            account.email, f"{site_url}/reset-password?token={token}"
        )
        background_tasks.add_task(_send_reset_email, request.app.state.mailer, message)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_password_with_token(request: Request, payload: ResetPasswordIn) -> Response:
    try:
        user_id, fingerprint = read_password_reset_token(
            payload.token, request.app.state.jwt_secret
        )
        with request.app.state.session_factory() as session:
            reset_password(session, user_id, fingerprint, payload.password)
            session.commit()
    except (TokenInvalidError, ResetLinkInvalidError) as error:
        raise ApiError(400, "AUTH_INVALID_TOKEN", "Invalid or expired link") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
