"""Add ESP / outreach fields to messages

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id"), nullable=True),
    )
    op.create_index("ix_messages_contact_id", "messages", ["contact_id"])
    op.add_column("messages", sa.Column("subject", sa.String(300), nullable=True))
    op.add_column("messages", sa.Column("esp_message_id", sa.String(200), nullable=True))
    op.create_index("ix_messages_esp_message_id", "messages", ["esp_message_id"])
    op.add_column("messages", sa.Column("esp_provider", sa.String(30), nullable=True))
    op.add_column("messages", sa.Column("to_email", sa.String(255), nullable=True))
    op.add_column("messages", sa.Column("unsubscribe_token", sa.String(64), nullable=True))
    op.create_index("ix_messages_unsubscribe_token", "messages", ["unsubscribe_token"], unique=True)
    op.add_column("messages", sa.Column("last_send_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "last_send_error")
    op.drop_index("ix_messages_unsubscribe_token", table_name="messages")
    op.drop_column("messages", "unsubscribe_token")
    op.drop_column("messages", "to_email")
    op.drop_column("messages", "esp_provider")
    op.drop_index("ix_messages_esp_message_id", table_name="messages")
    op.drop_column("messages", "esp_message_id")
    op.drop_column("messages", "subject")
    op.drop_index("ix_messages_contact_id", table_name="messages")
    op.drop_column("messages", "contact_id")
