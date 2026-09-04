"""Phase 5.5: tos_accepted_at, sending_identities, org soft-delete

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("tos_accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "sending_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("from_name", sa.String(120), nullable=False, server_default="Outreach"),
        sa.Column("from_address", sa.String(255), nullable=False),
        sa.Column("verified_domain", sa.String(255), nullable=False),
        sa.Column("spf_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("dkim_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sending_paused", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("pause_reason", sa.Text(), nullable=True),
        sa.Column("bounce_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("complaint_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sending_identities_organization_id", "sending_identities", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_sending_identities_organization_id", table_name="sending_identities")
    op.drop_table("sending_identities")
    op.drop_column("organizations", "deleted_at")
    op.drop_column("users", "tos_accepted_at")
