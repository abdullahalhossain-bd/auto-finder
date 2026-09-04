"""
Request/response schemas for POST /auth/register, /auth/login, /auth/refresh.
"""
import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequestSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    organization_name: str = Field(min_length=1)
    tos_accepted: bool = Field(
        ...,
        description="Must be true — Acceptable Use / Terms acceptance (Section 19)",
    )
    referral_code: Optional[str] = Field(
        None, max_length=32, description="Optional referral/invite code"
    )

    @field_validator("tos_accepted")
    @classmethod
    def must_accept_tos(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("You must accept the Terms of Service and Acceptable Use Policy")
        return v


class RegisterResponseSchema(BaseModel):
    user_id: uuid.UUID
    organization_id: uuid.UUID
    access_token: str
    refresh_token: str


class LoginRequestSchema(BaseModel):
    email: EmailStr
    password: str


class LoginResponseSchema(BaseModel):
    access_token: str
    refresh_token: str


class RefreshRequestSchema(BaseModel):
    refresh_token: str


class RefreshResponseSchema(BaseModel):
    access_token: str


class ErrorDetailSchema(BaseModel):
    code: str
    message: str


class ErrorResponseSchema(BaseModel):
    error: ErrorDetailSchema


class ForgotPasswordRequestSchema(BaseModel):
    email: EmailStr


class ResetPasswordRequestSchema(BaseModel):
    token: str = Field(min_length=10)
    new_password: str = Field(min_length=8)
