"""Inbox replies (Stage 1: messages marked replied)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.message import Message
from app.repositories.message_repository import MessageRepository
from app.schemas.message import MessageRead

router = APIRouter(tags=["inbox"])


@router.get("/inbox/replies", response_model=list[MessageRead])
async def list_replies(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """Messages with status=replied for the current organization."""
    stmt = (
        select(Message)
        .join(Lead, Message.lead_id == Lead.id)
        .join(Campaign, Lead.campaign_id == Campaign.id)
        .where(
            Campaign.organization_id == current.organization_id,
            Message.status == "replied",
        )
        .order_by(Message.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows)


@router.post("/messages/{message_id}/mark-replied", response_model=MessageRead)
async def mark_message_replied(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """Human marks a conversation as replied (inbound path Stage 1)."""
    repo = MessageRepository(db)
    message = await repo.get_by_id(message_id, current.organization_id)
    if not message:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Message not found"}},
        )
    if message.status not in ("sent", "approved", "replied"):
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "INVALID_STATUS",
                    "message": f"Cannot mark replied from status: {message.status}",
                }
            },
        )
    message.status = "replied"
    # Advance lead stage if still early
    lead_row = await db.execute(select(Lead).where(Lead.id == message.lead_id))
    lead = lead_row.scalar_one_or_none()
    if lead and lead.stage in ("new", "contacted", "follow_up"):
        lead.stage = "replied"
    await db.commit()
    await db.refresh(message)
    return message
