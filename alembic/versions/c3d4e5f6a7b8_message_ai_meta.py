"""Add AI generation metadata columns on messages

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("ai_rationale", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("generation_provider", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "generation_provider")
    op.drop_column("messages", "ai_rationale")
