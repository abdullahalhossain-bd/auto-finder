"""Referral codes + redemptions + bonus lead credits."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import String, DateTime, ForeignKey, Integer, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin


class ReferralCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "referral_codes"
    __table_args__ = (
        UniqueConstraint("code", name="uq_referral_codes_code"),
        UniqueConstraint("organization_id", name="uq_referral_codes_org"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # successful paid conversions counted for leaderboard
    successful_referrals: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    # signup redemptions
    signup_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class ReferralRedemption(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "referral_redemptions"
    __table_args__ = (
        UniqueConstraint("referred_organization_id", name="uq_referral_redemptions_referred_org"),
    )

    referral_code_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("referral_codes.id"), nullable=False, index=True
    )
    referrer_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    referred_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    referred_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    # signup | paid
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="signup")
    inviter_reward_leads: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    invitee_reward_leads: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    paid_reward_granted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class OrganizationCredit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Bonus quotas stacked on top of plan caps (referral rewards, promos)."""
    __tablename__ = "organization_credits"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_organization_credits_org"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    bonus_leads: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    bonus_campaigns: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
