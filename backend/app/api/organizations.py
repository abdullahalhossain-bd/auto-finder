"""
Organization endpoints: me, export, soft-delete (Section 21).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.logging_config import log_event
from app.models.business import Business
from app.models.campaign import Campaign
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.message import Message
from app.models.suppression import SuppressionList
from app.repositories.membership_repository import MembershipRepository
from app.repositories.organization_repository import OrganizationRepository
from app.services.audit_service import write_audit

router = APIRouter(prefix="/organizations", tags=["organizations"])


class OrganizationMeResponseSchema(BaseModel):
    id: str
    name: str
    plan: str
    deleted_at: str | None = None


async def _require_owner(db: AsyncSession, current: CurrentUser) -> None:
    m = await MembershipRepository(db).get(current.organization_id, user_id=current.user_id)
    if m is None or m.role != "owner":
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "FORBIDDEN", "message": "Owner role required"}},
        )


@router.get("/me", response_model=OrganizationMeResponseSchema)
async def get_my_organization(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> OrganizationMeResponseSchema:
    org = await OrganizationRepository(session).get_by_id(current_user.organization_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Organization not found"}},
        )
    return OrganizationMeResponseSchema(
        id=str(org.id),
        name=org.name,
        plan=org.plan,
        deleted_at=org.deleted_at.isoformat() if getattr(org, "deleted_at", None) else None,
    )


@router.get("/me/export")
async def export_organization(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Downloadable JSON bundle of org campaigns/leads/messages (owner)."""
    await _require_owner(session, current_user)
    org_id = current_user.organization_id
    org = await OrganizationRepository(session).get_by_id(org_id)
    if org is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Not found"}})

    campaigns = (
        await session.execute(select(Campaign).where(Campaign.organization_id == org_id))
    ).scalars().all()
    campaign_ids = [c.id for c in campaigns]

    leads = []
    if campaign_ids:
        leads = (
            await session.execute(select(Lead).where(Lead.campaign_id.in_(campaign_ids)))
        ).scalars().all()
    lead_ids = [l.id for l in leads]
    messages = []
    if lead_ids:
        messages = (
            await session.execute(select(Message).where(Message.lead_id.in_(lead_ids)))
        ).scalars().all()
    suppression = (
        await session.execute(
            select(SuppressionList).where(SuppressionList.organization_id == org_id)
        )
    ).scalars().all()

    bundle: dict[str, Any] = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "organization": {"id": str(org.id), "name": org.name, "plan": org.plan},
        "campaigns": [
            {
                "id": str(c.id),
                "status": c.status,
                "natural_language_input": c.natural_language_input,
                "structured_params": c.structured_params,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in campaigns
        ],
        "leads": [
            {
                "id": str(l.id),
                "campaign_id": str(l.campaign_id),
                "business_id": str(l.business_id),
                "stage": l.stage,
                "opportunity_score": l.opportunity_score,
                "score_breakdown": l.score_breakdown,
            }
            for l in leads
        ],
        "messages": [
            {
                "id": str(m.id),
                "lead_id": str(m.lead_id),
                "status": m.status,
                "subject": m.subject,
                "content": m.content,
                "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            }
            for m in messages
        ],
        "suppression_list": [
            {
                "contact_value": s.contact_value,
                "reason": s.reason,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in suppression
        ],
    }
    log_event("organization.exported", organization_id=str(org_id), user_id=str(current_user.user_id))
    body = json.dumps(bundle, ensure_ascii=False, indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="org-{org_id}-export.json"'
        },
    )


@router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_organization(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Soft-delete organization (owner). Hard-delete of related data is scheduled
    operationally after ~30 days (Section 21).
    """
    await _require_owner(session, current_user)
    org = await OrganizationRepository(session).get_by_id(current_user.organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Not found"}})
    if org.deleted_at is not None:
        return {"status": "already_deleted", "deleted_at": org.deleted_at.isoformat()}

    org.deleted_at = datetime.now(timezone.utc)
    await write_audit(
        session,
        action="organization.soft_delete",
        organization_id=org.id,
        user_id=current_user.user_id,
        resource_type="organization",
        resource_id=str(org.id),
    )
    await session.commit()
    log_event(
        "organization.soft_deleted",
        organization_id=str(org.id),
        user_id=str(current_user.user_id),
    )
    return {
        "status": "deleted",
        "deleted_at": org.deleted_at.isoformat(),
        "message": "Organization soft-deleted. Data retained ~30 days for recovery, then purged.",
    }
