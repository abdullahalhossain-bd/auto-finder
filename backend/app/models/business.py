from typing import Optional, Any, TYPE_CHECKING
from sqlalchemy import String, Float, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.lead import Lead
    from app.models.website_audit import WebsiteAudit
    from app.models.contact import Contact


class Business(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "businesses"
    __table_args__ = (
        UniqueConstraint("organization_id", "dedupe_key", name="uq_businesses_org_dedupe"),
    )

    # Tenant isolation — discovery is per-org (FINAL_SYSTEM_SPEC)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    review_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)  # osm | google_places | merged
    dedupe_key: Mapped[str] = mapped_column(String(400), nullable=False, index=True)
    source_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    leads: Mapped[list["Lead"]] = relationship(back_populates="business")
    website_audits: Mapped[list["WebsiteAudit"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
