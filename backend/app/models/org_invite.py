"""Organization member invites."""
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin


class OrgInvite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "org_invites"
    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_org_invites_org_email"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="member")
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    invited_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    # pending | accepted | revoked | expired
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
