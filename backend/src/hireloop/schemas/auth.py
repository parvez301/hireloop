"""Pydantic request/response schemas for the custom auth endpoints."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100, alias="firstName")
    last_name: str = Field(..., min_length=1, max_length=100, alias="lastName")
    email: EmailStr
    password: str = Field(..., min_length=10, max_length=256)

    model_config = {"populate_by_name": True}


class SignupResponse(BaseModel):
    user_id: str = Field(..., alias="userId")
    model_config = {"populate_by_name": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=256)
    remember: bool = False


class SessionResponse(BaseModel):
    id_token: str = Field(..., alias="idToken")
    refresh_token: str = Field(..., alias="refreshToken")
    expires_in: int = Field(..., alias="expiresIn")
    model_config = {"populate_by_name": True}


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResendCodeRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=256)
    password: str = Field(..., min_length=10, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., alias="refreshToken", min_length=16)
    model_config = {"populate_by_name": True}


class RefreshResponse(BaseModel):
    id_token: str = Field(..., alias="idToken")
    expires_in: int = Field(..., alias="expiresIn")
    model_config = {"populate_by_name": True}


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., alias="refreshToken", min_length=16)
    model_config = {"populate_by_name": True}
