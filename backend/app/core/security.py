"""
Password hashing (argon2id, per FINAL_SYSTEM_SPEC.md Section 11) and JWT
access/refresh token issuance + verification.

Access tokens: short-lived, carry `sub` (user_id) and `org_id` (the user's
primary/first organization — Stage 1 has no multi-org switching UI, a user's
membership row(s) determine which orgs they can act as, but the token's
`org_id` claim is a convenience default used by the auth dependency).

Refresh tokens: longer-lived, carry only `sub` and a `type: refresh` marker
so an access token can never be replayed as a refresh token or vice versa.
"""
import uuid
from datetime import datetime, timedelta, timezone
from enum import StrEnum

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from app.core.config import get_settings

_settings = get_settings()
_password_hasher = PasswordHasher()

JWT_ALGORITHM = "HS256"


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class InvalidTokenError(Exception):
    """Raised when a JWT is malformed, expired, or the wrong token type."""


# --- Password hashing ---

def hash_password(plain_password: str) -> str:
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# --- JWT issuance ---

def create_access_token(user_id: uuid.UUID, organization_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "org_id": str(organization_id),
        "type": TokenType.ACCESS.value,
        "iat": now,
        "exp": now + timedelta(minutes=_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, _settings.APP_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": TokenType.REFRESH.value,
        "iat": now,
        "exp": now + timedelta(days=_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, _settings.APP_SECRET_KEY, algorithm=JWT_ALGORITHM)


# --- JWT verification ---

def decode_token(token: str, expected_type: TokenType) -> dict:
    try:
        payload = jwt.decode(token, _settings.APP_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("Token is invalid") from exc

    if payload.get("type") != expected_type.value:
        raise InvalidTokenError(f"Expected a {expected_type.value} token")

    return payload
