"""FINAL_SYSTEM_SPEC §4: followups, usage, audit_logs, soft-delete, lead unique, next_recrawl

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
Create Date: 2026-08-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "h8c9d0e1f2a3"
down_revision: Union[str, None] = "g7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Soft delete
    op.add_column("campaigns", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("leads", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("messages", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "website_audits",
        sa.Column("next_recrawl_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Lead uniqueness (dedupe within campaign)
    # Drop duplicates keep oldest if any
    op.execute(
        """
        DELETE FROM leads a
        USING leads b
        WHERE a.campaign_id = b.campaign_id
          AND a.business_id = b.business_id
          AND a.created_at > b.created_at
        """
    )
    op.create_unique_constraint(
        "uq_leads_campaign_business", "leads", ["campaign_id", "business_id"]
    )

    op.create_table(
        "followups",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="scheduled"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("message_id", name="uq_followups_message_id"),
    )
    op.create_index("ix_followups_organization_id", "followups", ["organization_id"])
    op.create_index("ix_followups_lead_id", "followups", ["lead_id"])
    op.create_index("ix_followups_message_id", "followups", ["message_id"])

    op.create_table(
        "usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("campaigns_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leads_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("messages_sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_calls_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", "period", name="uq_usage_org_period"),
    )
    op.create_index("ix_usage_organization_id", "usage", ["organization_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("resource_type", sa.String(40), nullable=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(300), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("usage")
    op.drop_table("followups")
    op.drop_constraint("uq_leads_campaign_business", "leads", type_="unique")
    op.drop_column("website_audits", "next_recrawl_at")
    op.drop_column("messages", "deleted_at")
    op.drop_column("leads", "deleted_at")
    op.drop_column("campaigns", "deleted_at")
