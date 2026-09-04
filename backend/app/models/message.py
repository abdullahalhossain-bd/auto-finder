from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.lead import Lead
    from app.models.contact import Contact


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True
    )
    # Target contact (email). Optional until send time resolves it from business contacts.
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    # draft | pending_approval | approved | rejected | sent | bounced | replied
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True
    )
    # ESP tracking
    esp_message_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    esp_provider: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    to_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    unsubscribe_token: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    last_send_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generation_provider: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    lead: Mapped["Lead"] = relationship(back_populates="messages")
    contact: Mapped[Optional["Contact"]] = relationship()
