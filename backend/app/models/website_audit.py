from datetime import datetime
from typing import Optional, Any, TYPE_CHECKING
from sqlalchemy import String, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.business import Business


class WebsiteAudit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "website_audits"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True
    )
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    has_ssl: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    has_viewport: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    booking_vendor_detected: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_findings: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_recrawl_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    business: Mapped["Business"] = relationship(back_populates="website_audits")
