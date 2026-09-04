"""Org-owned encrypted API keys (Google Places, Groq, etc.)."""
from typing import Optional
import uuid

from sqlalchemy import String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin


class ApiCredential(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "api_credentials"
    __table_args__ = (
        UniqueConstraint("organization_id", "provider", name="uq_api_credentials_org_provider"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    # google_places | groq | resend | smtp
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    last4: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
