"""Soft-delete filters helpers + hard-purge of old soft-deleted rows (free, local)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.logging_config import log_event
from app.models.campaign import Campaign
from app.models.organization import Organization
from app.models.lead import Lead
from app.models.message import Message


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def soft_delete_campaign(session: AsyncSession, campaign: Campaign) -> Campaign:
    campaign.deleted_at = utcnow()
    # Cascade soft-delete leads under campaign
    leads = (
        await session.execute(select(Lead).where(Lead.campaign_id == campaign.id, Lead.deleted_at.is_(None)))
    ).scalars().all()
    for lead in leads:
        lead.deleted_at = campaign.deleted_at
        msgs = (
            await session.execute(
                select(Message).where(Message.lead_id == lead.id, Message.deleted_at.is_(None))
            )
        ).scalars().all()
        for m in msgs:
            m.deleted_at = campaign.deleted_at
    await session.commit()
    await session.refresh(campaign)
    return campaign


async def soft_delete_message(session: AsyncSession, message: Message) -> Message:
    message.deleted_at = utcnow()
    await session.commit()
    await session.refresh(message)
    return message


def hard_purge_sync(session: Session, *, older_than_days: int = 30) -> dict[str, int]:
    """
    Permanently remove rows soft-deleted more than N days ago.
    Order: messages → leads → campaigns (FK-safe).
    """
    cutoff = utcnow() - timedelta(days=older_than_days)
    counts: dict[str, int] = {"messages": 0, "leads": 0, "campaigns": 0, "organizations": 0}

    msgs = (
        session.execute(
            select(Message.id).where(
                Message.deleted_at.is_not(None),
                Message.deleted_at < cutoff,
            )
        )
        .scalars()
        .all()
    )
    if msgs:
        session.execute(delete(Message).where(Message.id.in_(msgs)))
        counts["messages"] = len(msgs)

    leads = (
        session.execute(
            select(Lead.id).where(
                Lead.deleted_at.is_not(None),
                Lead.deleted_at < cutoff,
            )
        )
        .scalars()
        .all()
    )
    if leads:
        # remaining messages for these leads
        session.execute(delete(Message).where(Message.lead_id.in_(leads)))
        session.execute(delete(Lead).where(Lead.id.in_(leads)))
        counts["leads"] = len(leads)

    camps = (
        session.execute(
            select(Campaign.id).where(
                Campaign.deleted_at.is_not(None),
                Campaign.deleted_at < cutoff,
            )
        )
        .scalars()
        .all()
    )
    if camps:
        session.execute(delete(Campaign).where(Campaign.id.in_(camps)))
        counts["campaigns"] = len(camps)

    # Soft-deleted organizations past retention
    orgs = (
        session.execute(
            select(Organization.id).where(
                Organization.deleted_at.is_not(None),
                Organization.deleted_at < cutoff,
            )
        )
        .scalars()
        .all()
    )
    if orgs:
        # memberships cascade via FK ondelete; campaigns already purged if soft-deleted
        session.execute(delete(Organization).where(Organization.id.in_(orgs)))
        counts["organizations"] = len(orgs)

    session.commit()
    log_event(
        "soft_delete.hard_purge",
        older_than_days=older_than_days,
        **counts,
    )
    return counts
