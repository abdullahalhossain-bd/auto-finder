"""Per-org sending identity — SPF/DKIM must both be true before send (Section 18)."""
from typing import Optional, TYPE_CHECKING
import uuid

from sqlalchemy import String, Boolean, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Organization


class SendingIdentity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sending_identities"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    from_name: Mapped[str] = mapped_column(String(120), nullable=False, server_default="Outreach")
    from_address: Mapped[str] = mapped_column(String(255), nullable=False)
    verified_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    spf_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    dkim_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    sending_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    pause_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bounce_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    complaint_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    organization: Mapped["Organization"] = relationship(back_populates="sending_identities")
