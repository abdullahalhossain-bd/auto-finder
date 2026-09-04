"""
subscriptions — one active subscription row per organization (Section 17).
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
import uuid

from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Organization


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_subscriptions_organization_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    plan_id: Mapped[str] = mapped_column(String(40), nullable=False, server_default="trial")
    # trialing | active | past_due | cancelled
    status: Mapped[str] = mapped_column(String(40), nullable=False, server_default="trialing")
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="subscription")
