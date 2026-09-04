"""
Auth service — registration, login, token refresh.

Business logic lives here, not in the route handler, per CODING_STANDARDS.md
("no business logic inside route handlers").
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.membership_repository import MembershipRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.services.billing_service import ensure_trial_subscription


class EmailTakenError(Exception):
    """Raised when registering with an email that already exists."""


class InvalidCredentialsError(Exception):
    """Raised on login with a wrong email/password combination."""


class InvalidRefreshTokenError(Exception):
    """Raised when POST /auth/refresh is given an expired/malformed/unknown refresh token."""


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._organizations = OrganizationRepository(session)
        self._memberships = MembershipRepository(session)

    async def register(
        self, *, email: str, password: str, organization_name: str, tos_accepted: bool = False, referral_code: str | None = None
    ) -> tuple[User, uuid.UUID, str, str]:
        """
        Creates a user + a new organization + an `owner` membership linking
        them, in one transaction. Returns (user, organization_id,
        access_token, refresh_token).
        """
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise EmailTakenError(email)

        if not tos_accepted:
            raise ValueError("TOS_REQUIRED")
        from datetime import datetime, timezone
        user = await self._users.create(email=email, password_hash=hash_password(password))
        user.tos_accepted_at = datetime.now(timezone.utc)
        await self._session.flush()
        organization = await self._organizations.create(name=organization_name)
        await self._memberships.create(organization.id, user_id=user.id, role="owner")

        await ensure_trial_subscription(self._session, organization.id)

        referral_meta = None
        if referral_code:
            from app.services.referral_service import apply_referral_on_register
            referral_meta = await apply_referral_on_register(
                self._session,
                referral_code=referral_code,
                new_organization_id=organization.id,
                new_user_id=user.id,
            )

        # Auto-create referral code for new org (viral loop)
        from app.services.referral_service import get_or_create_referral_code
        await get_or_create_referral_code(
            self._session, organization_id=organization.id, user_id=user.id
        )

        from app.services.audit_service import write_audit
        await write_audit(
            self._session,
            action="auth.register",
            user_id=user.id,
            organization_id=organization.id,
            meta={"email": email, "referral": referral_meta},
        )
        await self._session.commit()

        access_token = create_access_token(user_id=user.id, organization_id=organization.id)
        refresh_token = create_refresh_token(user_id=user.id)
        return user, organization.id, access_token, refresh_token

    async def login(self, *, email: str, password: str) -> tuple[str, str]:
        """Returns (access_token, refresh_token)."""
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            try:
                from app.services.audit_service import write_audit
                await write_audit(
                    self._session,
                    action="auth.login_failed",
                    detail=(email or "")[:120],
                    meta={"reason": "invalid_credentials"},
                )
                await self._session.commit()
            except Exception:
                await self._session.rollback()
            raise InvalidCredentialsError()

        memberships = await self._memberships.list_for_user(user_id=user.id)
        if not memberships:
            # Should be unreachable in practice (registration always creates
            # one), but a user with zero orgs has nothing to scope a token
            # to — treat like invalid credentials rather than issuing a
            # token with no usable org context.
            raise InvalidCredentialsError()

        default_org_id = memberships[0].organization_id
        access_token = create_access_token(user_id=user.id, organization_id=default_org_id)
        refresh_token = create_refresh_token(user_id=user.id)
        try:
            from app.services.audit_service import write_audit
            await write_audit(
                self._session,
                action="auth.login_success",
                user_id=user.id,
                organization_id=default_org_id,
            )
            await self._session.commit()
        except Exception:
            await self._session.rollback()
        return access_token, refresh_token

    async def refresh(self, *, refresh_token: str) -> str:
        """Returns a new access_token."""
        try:
            payload = decode_token(refresh_token, expected_type=TokenType.REFRESH)
        except InvalidTokenError as exc:
            raise InvalidRefreshTokenError() from exc

        user_id = uuid.UUID(payload["sub"])
        memberships = await self._memberships.list_for_user(user_id=user_id)
        if not memberships:
            raise InvalidRefreshTokenError()

        default_org_id = memberships[0].organization_id
        return create_access_token(user_id=user_id, organization_id=default_org_id)

    async def request_password_reset(self, *, email: str) -> str | None:
        """
        Always succeeds from API POV (no email enumeration).
        Returns plaintext token only for console/dev logging — never in HTTP response.
        Free path: log token when ESP is console.
        """
        import hashlib
        import secrets
        from datetime import datetime, timedelta, timezone

        from app.services.audit_service import write_audit

        user = await self._users.get_by_email(email)
        if user is None:
            return None
        token = secrets.token_urlsafe(32)
        user.password_reset_token_hash = hashlib.sha256(token.encode()).hexdigest()
        user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await write_audit(
            self._session,
            action="auth.password_reset_requested",
            user_id=user.id,
            meta={"email": email},
        )
        await self._session.commit()
        # Console-friendly: log reset link (no paid email required)
        import logging
        logging.getLogger(__name__).info(
            "password_reset token for %s (dev/console): %s", email, token
        )
        return token

    async def reset_password(self, *, token: str, new_password: str) -> None:
        import hashlib
        from datetime import datetime, timezone

        from app.services.audit_service import write_audit
        from sqlalchemy import select
        from app.models.user import User

        if len(new_password) < 8:
            raise ValueError("PASSWORD_TOO_SHORT")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        result = await self._session.execute(
            select(User).where(User.password_reset_token_hash == token_hash)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise InvalidCredentialsError()
        exp = user.password_reset_expires_at
        if exp is None or (exp.replace(tzinfo=timezone.utc) if exp.tzinfo is None else exp) < datetime.now(timezone.utc):
            raise InvalidCredentialsError()
        user.password_hash = hash_password(new_password)
        user.password_reset_token_hash = None
        user.password_reset_expires_at = None
        await write_audit(
            self._session,
            action="auth.password_reset_completed",
            user_id=user.id,
        )
        await self._session.commit()
