"""Fernet encrypt/decrypt for api_credentials at rest."""
from __future__ import annotations

from app.core.config import get_settings


def _fernet():
    from cryptography.fernet import Fernet

    settings = get_settings()
    key = (settings.CREDENTIAL_ENCRYPTION_KEY or "").strip()
    if not key or key in ("changeme",):
        # Dev fallback: derive deterministic key from APP_SECRET_KEY (not for production)
        import base64
        import hashlib

        raw = hashlib.sha256((settings.APP_SECRET_KEY or "dev").encode()).digest()
        key = base64.urlsafe_b64encode(raw)
    return Fernet(key if isinstance(key, bytes) else key.encode() if not key.startswith("gAAAA") else key)


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
