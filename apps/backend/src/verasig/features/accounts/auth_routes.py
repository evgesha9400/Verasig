from fastapi import APIRouter, Depends, Request, Response, status

from verasig.domain.account import UserAccount
from verasig.features.accounts.auth_schemas import AuthOut, LoginIn, RegisterIn
from verasig.features.accounts.tokens import issue_token
from verasig.features.accounts.user_schemas import UserOut, user_out
from verasig.features.accounts.workflow import (
    EmailTakenError,
    InvalidCredentialsError,
    authenticate,
    register_account,
)
from verasig.foundation.http.auth_dependencies import access_token_ttl, get_current_user
from verasig.foundation.http.errors import ApiError

router = APIRouter(prefix="/auth")


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
