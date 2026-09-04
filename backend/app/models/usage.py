"""Per-org monthly usage counters (optional materialization of /usage)."""
from typing import Optional
import uuid

from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin


class Usage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "usage"
    __table_args__ = (
        UniqueConstraint("organization_id", "period", name="uq_usage_org_period"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    # YYYY-MM
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    campaigns_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    leads_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    messages_sent_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    llm_calls_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
