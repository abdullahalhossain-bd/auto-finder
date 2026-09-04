"""
Shared column mixins.

Per FINAL_SYSTEM_SPEC.md Section 4: every table has
  id UUID PK default gen_random_uuid()
  created_at timestamptz default now()
  updated_at timestamptz (trigger-maintained)

Soft delete (deleted_at) applies ONLY to campaigns, leads, messages
(tables a user might "undo") — not to organizations/users/memberships,
so it is intentionally not part of this base mixin.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        onupdate=text("now()"),
        nullable=False,
    )
