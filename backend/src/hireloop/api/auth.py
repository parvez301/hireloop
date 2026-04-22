"""Auth HTTP endpoints — both the existing `/me` and the in-house flow.

Endpoints under `/auth/*` that don't need an authenticated user are:
- POST /signup
- POST /login
- POST /verify-email
- POST /resend-code
- POST /forgot
- POST /reset
- POST /refresh
- POST /logout

`/me` keeps returning the authed user (used by the portal).
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from hireloop.api.deps import CurrentDbUser, DbSession
from hireloop.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
    ResendCodeRequest,
    ResetPasswordRequest,
    SessionResponse,
    SignupRequest,
    SignupResponse,
    VerifyEmailRequest,
)
from hireloop.schemas.common import Envelope
from hireloop.schemas.user import UserResponse
from hireloop.services.auth import (
    forgot_password,
    login,
    logout,
    refresh,
    resend_code,
    reset_password,
    signup,
    verify_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    user_agent = request.headers.get("user-agent")
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = (forwarded.split(",")[0].strip() if forwarded else None) or (
        request.client.host if request.client else None
    )
    return user_agent, ip


@router.get("/me", response_model=Envelope[UserResponse])
async def me(user: CurrentDbUser, db: DbSession) -> Envelope[UserResponse]:
    _ = db
    return Envelope(data=UserResponse.model_validate(user))


@router.post(
    "/signup",
    response_model=Envelope[SignupResponse],
    status_code=status.HTTP_201_CREATED,
)
async def signup_endpoint(
    body: SignupRequest, db: DbSession
) -> Envelope[SignupResponse]:
    user_id = await signup(
        db,
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        password=body.password,
    )
    return Envelope(data=SignupResponse(userId=str(user_id)))


@router.post("/login", response_model=Envelope[SessionResponse])
async def login_endpoint(
    body: LoginRequest, request: Request, db: DbSession
) -> Envelope[SessionResponse]:
    ua, ip = _client_meta(request)
    session = await login(
        db,
        email=body.email,
        password=body.password,
        user_agent=ua,
        ip=ip,
    )
    return Envelope(
        data=SessionResponse(
            idToken=session.id_token,
            refreshToken=session.refresh_token,
            expiresIn=session.expires_in,
        )
    )


@router.post("/verify-email", response_model=Envelope[SessionResponse])
async def verify_email_endpoint(
    body: VerifyEmailRequest, request: Request, db: DbSession
) -> Envelope[SessionResponse]:
    ua, ip = _client_meta(request)
    session = await verify_email(
        db, email=body.email, code=body.code, user_agent=ua, ip=ip
    )
    return Envelope(
        data=SessionResponse(
            idToken=session.id_token,
            refreshToken=session.refresh_token,
            expiresIn=session.expires_in,
        )
    )


@router.post("/resend-code", status_code=status.HTTP_204_NO_CONTENT)
async def resend_code_endpoint(body: ResendCodeRequest, db: DbSession) -> Response:
    await resend_code(db, email=body.email)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/forgot", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password_endpoint(
    body: ForgotPasswordRequest, db: DbSession
) -> Response:
    await forgot_password(db, email=body.email)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reset", response_model=Envelope[SessionResponse])
async def reset_password_endpoint(
    body: ResetPasswordRequest, request: Request, db: DbSession
) -> Envelope[SessionResponse]:
    ua, ip = _client_meta(request)
    session = await reset_password(
        db, token=body.token, password=body.password, user_agent=ua, ip=ip
    )
    return Envelope(
        data=SessionResponse(
            idToken=session.id_token,
            refreshToken=session.refresh_token,
            expiresIn=session.expires_in,
        )
    )


@router.post("/refresh", response_model=Envelope[RefreshResponse])
async def refresh_endpoint(
    body: RefreshRequest, db: DbSession
) -> Envelope[RefreshResponse]:
    refreshed = await refresh(db, refresh_token=body.refresh_token)
    return Envelope(
        data=RefreshResponse(
            idToken=refreshed.id_token, expiresIn=refreshed.expires_in
        )
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_endpoint(body: LogoutRequest, db: DbSession) -> Response:
    await logout(db, refresh_token=body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
