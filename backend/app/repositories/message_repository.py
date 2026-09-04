from typing import Optional, Sequence
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.message import Message
from app.models.lead import Lead
from app.models.campaign import Campaign


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, message_id: UUID, organization_id: UUID) -> Optional[Message]:
        result = await self.session.execute(
            select(Message)
            .join(Lead, Message.lead_id == Lead.id)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .where(
                Message.id == message_id,
                Campaign.organization_id == organization_id,
                Message.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        lead_id: UUID,
        content: str,
        status: str = "pending_approval",
        contact_id: Optional[UUID] = None,
        subject: Optional[str] = None,
    ) -> Message:
        message = Message(
            lead_id=lead_id,
            content=content,
            status=status,
            contact_id=contact_id,
            subject=subject,
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def list_pending_approval(
        self, organization_id: UUID, limit: int = 50, offset: int = 0
    ) -> tuple[Sequence[Message], int]:
        base = (
            select(Message)
            .join(Lead, Message.lead_id == Lead.id)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .where(
                Campaign.organization_id == organization_id,
                Message.status == "pending_approval",
                Message.deleted_at.is_(None),
            )
        )
        total = (
            await self.session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        result = await self.session.execute(
            base.order_by(Message.created_at.asc()).limit(limit).offset(offset)
        )
        return result.scalars().all(), total

    async def approve(self, message: Message, approved_by: UUID) -> Message:
        message.status = "approved"
        message.approved_by = approved_by
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def reject(self, message: Message) -> Message:
        message.status = "rejected"
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def mark_sent(
        self,
        message: Message,
        idempotency_key: str,
        esp_message_id: Optional[str] = None,
        esp_provider: Optional[str] = None,
        to_email: Optional[str] = None,
    ) -> Message:
        from datetime import datetime, timezone

        message.status = "sent"
        message.idempotency_key = idempotency_key
        message.sent_at = datetime.now(timezone.utc)
        if esp_message_id:
            message.esp_message_id = esp_message_id
        if esp_provider:
            message.esp_provider = esp_provider
        if to_email:
            message.to_email = to_email
        await self.session.commit()
        await self.session.refresh(message)
        return message
