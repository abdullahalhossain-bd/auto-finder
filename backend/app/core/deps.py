"""FastAPI dependencies shared across route modules."""
import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.logging_config import bind_context
from app.core.security import InvalidTokenError, TokenType, decode_token

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user_id: uuid.UUID
    organization_id: uuid.UUID


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "UNAUTHORIZED", "message": "Missing or invalid access token"}},
    )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise _unauthorized()

    try:
        payload = decode_token(credentials.credentials, expected_type=TokenType.ACCESS)
    except InvalidTokenError as exc:
        raise _unauthorized() from exc

    user = CurrentUser(
        user_id=uuid.UUID(payload["sub"]),
        organization_id=uuid.UUID(payload["org_id"]),
    )
    # Structured logs for the rest of this request include org + user
    bind_context(
        organization_id=str(user.organization_id),
        user_id=str(user.user_id),
    )
    request.state.organization_id = user.organization_id
    request.state.user_id = user.user_id
    return user


def _admin_emails() -> set[str]:
    from app.core.config import get_settings
    raw = (getattr(get_settings(), "PLATFORM_ADMIN_EMAILS", None) or "").strip()
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


async def require_platform_admin(
    current: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Platform super-admin only (not org owner).
    Configure PLATFORM_ADMIN_EMAILS=admin@example.com,ops@example.com
    """
    from sqlalchemy import select
    from app.core.database import get_db
    from app.models.user import User

    # get_db is async generator — use session from a one-shot
    from app.core.database import async_session_factory

    emails = _admin_emails()
    if not emails:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "ADMIN_NOT_CONFIGURED",
                    "message": "PLATFORM_ADMIN_EMAILS is not set on this deployment",
                }
            },
        )

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.id == current.user_id))
        user = result.scalar_one_or_none()
        if user is None or (user.email or "").lower() not in emails:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "Platform admin access required",
                    }
                },
            )
    return current


async def is_platform_admin_user(user_id: uuid.UUID, email: str | None = None) -> bool:
    emails = _admin_emails()
    if not emails:
        return False
    if email and email.lower() in emails:
        return True
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.user import User

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return bool(user and (user.email or "").lower() in emails)
