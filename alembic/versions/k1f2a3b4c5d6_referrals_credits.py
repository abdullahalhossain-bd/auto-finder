"""referrals and organization credits

Revision ID: k1f2a3b4c5d6
Revises: j0e1f2a3b4c5
Create Date: 2026-08-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "k1f2a3b4c5d6"
down_revision: Union[str, None] = "j0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "referral_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("successful_referrals", sa.Integer(), server_default="0", nullable=False),
        sa.Column("signup_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("code", name="uq_referral_codes_code"),
        sa.UniqueConstraint("organization_id", name="uq_referral_codes_org"),
    )
    op.create_index("ix_referral_codes_code", "referral_codes", ["code"])
    op.create_index("ix_referral_codes_organization_id", "referral_codes", ["organization_id"])

    op.create_table(
        "referral_redemptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("referral_code_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("referral_codes.id"), nullable=False),
        sa.Column("referrer_organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("referred_organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("referred_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(20), server_default="signup", nullable=False),
        sa.Column("inviter_reward_leads", sa.Integer(), server_default="0", nullable=False),
        sa.Column("invitee_reward_leads", sa.Integer(), server_default="0", nullable=False),
        sa.Column("paid_reward_granted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("referred_organization_id", name="uq_referral_redemptions_referred_org"),
    )
    op.create_index("ix_referral_redemptions_referral_code_id", "referral_redemptions", ["referral_code_id"])

    op.create_table(
        "organization_credits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("bonus_leads", sa.Integer(), server_default="0", nullable=False),
        sa.Column("bonus_campaigns", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", name="uq_organization_credits_org"),
    )


def downgrade() -> None:
    op.drop_table("organization_credits")
    op.drop_table("referral_redemptions")
    op.drop_table("referral_codes")
