"""Add organization_id, dedupe_key, source on businesses + unique constraint

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("businesses", sa.Column("dedupe_key", sa.String(400), nullable=True))
    op.add_column("businesses", sa.Column("source", sa.String(40), nullable=True))

    # Backfill organization_id from any linked lead → campaign
    op.execute(
        """
        UPDATE businesses b
        SET organization_id = sub.organization_id
        FROM (
            SELECT DISTINCT ON (l.business_id)
                l.business_id,
                c.organization_id
            FROM leads l
            JOIN campaigns c ON c.id = l.campaign_id
            ORDER BY l.business_id, l.created_at
        ) sub
        WHERE b.id = sub.business_id
          AND b.organization_id IS NULL
        """
    )
    # Orphans: attach to first organization if any, else leave null then delete orphans
    op.execute(
        """
        UPDATE businesses
        SET organization_id = (SELECT id FROM organizations ORDER BY created_at LIMIT 1)
        WHERE organization_id IS NULL
          AND EXISTS (SELECT 1 FROM organizations)
        """
    )
    op.execute(
        """
        UPDATE businesses
        SET dedupe_key = 'legacy:' || id::text
        WHERE dedupe_key IS NULL
        """
    )

    op.alter_column("businesses", "organization_id", nullable=False)
    op.alter_column("businesses", "dedupe_key", nullable=False)
    op.create_index("ix_businesses_organization_id", "businesses", ["organization_id"])
    op.create_index("ix_businesses_dedupe_key", "businesses", ["dedupe_key"])
    op.create_foreign_key(
        "fk_businesses_organization_id",
        "businesses",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_businesses_org_dedupe",
        "businesses",
        ["organization_id", "dedupe_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_businesses_org_dedupe", "businesses", type_="unique")
    op.drop_constraint("fk_businesses_organization_id", "businesses", type_="foreignkey")
    op.drop_index("ix_businesses_dedupe_key", table_name="businesses")
    op.drop_index("ix_businesses_organization_id", table_name="businesses")
    op.drop_column("businesses", "source")
    op.drop_column("businesses", "dedupe_key")
    op.drop_column("businesses", "organization_id")
