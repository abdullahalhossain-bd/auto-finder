"""
POST /auth/register, POST /auth/login, POST /auth/refresh.

Route handlers stay thin: validate input via Pydantic, call AuthService,
translate service exceptions to the API's standard error envelope. All
actual logic lives in app.services.auth_service.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import (
    LoginRequestSchema,
    LoginResponseSchema,
    RefreshRequestSchema,
    RefreshResponseSchema,
    RegisterRequestSchema,
    RegisterResponseSchema,
    ForgotPasswordRequestSchema,
    ResetPasswordRequestSchema,
)
from app.services.auth_service import (
    AuthService,
    EmailTakenError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequestSchema, session: AsyncSession = Depends(get_db)
) -> RegisterResponseSchema:
    service = AuthService(session)
    try:
        user, organization_id, access_token, refresh_token = await service.register(
            email=body.email, password=body.password, organization_name=body.organization_name, tos_accepted=body.tos_accepted, referral_code=getattr(body, "referral_code", None)
        )
    except ValueError as exc:
        if str(exc) == "TOS_REQUIRED":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": {"code": "TOS_REQUIRED", "message": "Terms of Service must be accepted"}},
            ) from exc
        raise
    except EmailTakenError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "EMAIL_TAKEN", "message": "This email is already registered"}},
        ) from exc

    return RegisterResponseSchema(
        user_id=user.id,
        organization_id=organization_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=LoginResponseSchema, status_code=status.HTTP_200_OK)
async def login(
    body: LoginRequestSchema, session: AsyncSession = Depends(get_db)
) -> LoginResponseSchema:
    service = AuthService(session)
    try:
        access_token, refresh_token = await service.login(email=body.email, password=body.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password"}},
        ) from exc

    return LoginResponseSchema(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=RefreshResponseSchema, status_code=status.HTTP_200_OK)
async def refresh(
    body: RefreshRequestSchema, session: AsyncSession = Depends(get_db)
) -> RefreshResponseSchema:
    service = AuthService(session)
    try:
        access_token = await service.refresh(refresh_token=body.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token is invalid or expired"}},
        ) from exc

    return RefreshResponseSchema(access_token=access_token)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    body: ForgotPasswordRequestSchema, session: AsyncSession = Depends(get_db)
) -> dict:
    """Always returns ok — does not reveal whether email exists. Token logged if user exists (console)."""
    service = AuthService(session)
    await service.request_password_reset(email=body.email)
    return {
        "ok": True,
        "message": "If that email is registered, a reset token has been issued. Check server logs when ESP_PROVIDER=console.",
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    body: ResetPasswordRequestSchema, session: AsyncSession = Depends(get_db)
) -> dict:
    service = AuthService(session)
    try:
        await service.reset_password(token=body.token, new_password=body.new_password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "PASSWORD_TOO_SHORT", "message": "Password must be at least 8 characters"}},
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Reset token is invalid or expired"}},
        )
    return {"ok": True, "message": "Password updated. You can log in."}
