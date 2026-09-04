from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser
from app.repositories.lead_repository import LeadRepository
from app.schemas.lead import LeadRead, LeadList, LeadUpdate
from app.services.audit_service import write_audit
from app.schemas.message import MessageGenerateRequest, MessageRead, MessageGenerateQueued

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=LeadList)
async def list_leads(
    campaign_id: UUID = Query(...),
    stage: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    repo = LeadRepository(db)
    items, total = await repo.list_by_campaign(
        campaign_id=campaign_id,
        organization_id=current.organization_id,
        stage=stage,
        limit=limit,
        offset=offset,
    )
    result = []
    for lead in items:
        data = LeadRead.model_validate(lead)
        if lead.business:
            data.business_name = lead.business.name
            data.business_category = lead.business.category
        result.append(data)
    return LeadList(items=result, total=total)


@router.get("/{lead_id}", response_model=LeadRead)
async def get_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    repo = LeadRepository(db)
    lead = await repo.get_by_id(lead_id, current.organization_id)
    if not lead:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Lead not found"}},
        )
    data = LeadRead.model_validate(lead)
    if lead.business:
        data.business_name = lead.business.name
        data.business_category = lead.business.category
    return data


@router.patch("/{lead_id}", response_model=LeadRead)
async def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    repo = LeadRepository(db)
    lead = await repo.get_by_id(lead_id, current.organization_id)
    if not lead:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Lead not found"}},
        )
    if payload.stage:
        lead = await repo.update_stage(lead, payload.stage)
    if payload.notes is not None:
        lead.notes = payload.notes
        await db.commit()
        await db.refresh(lead)
    return LeadRead.model_validate(lead)


@router.post(
    "/{lead_id}/messages",
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_message_for_lead(
    lead_id: UUID,
    payload: MessageGenerateRequest = MessageGenerateRequest(),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """
    Template + LLM personalization for this lead.
    Default: enqueue Celery job (202). async_mode=false runs inline and returns MessageRead.
    Message always lands in pending_approval — never auto-sent.
    """
    from app.core.sync_db import get_sync_session
    from app.services.message_generation_service import generate_message_for_lead_sync

    repo = LeadRepository(db)
    lead = await repo.get_by_id(lead_id, current.organization_id)
    if not lead:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Lead not found"}},
        )

    # AI Auto Message is a paid feature
    from app.services.plan_limits import PaidFeatureRequired, assert_paid_feature
    try:
        await assert_paid_feature(db, current.organization_id, "ai_auto_message")
    except PaidFeatureRequired as exc:
        raise HTTPException(
            status_code=402,
            detail={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "feature": exc.feature,
                }
            },
        ) from exc

    # Async (preferred): queue worker
    if payload.async_mode:
        try:
            from app.workers.tasks import generate_message_task

            job = generate_message_task.delay(
                str(lead_id),
                str(current.organization_id),
                str(payload.contact_id) if payload.contact_id else None,
                payload.service_offered,
            )
            return MessageGenerateQueued(
                job_id=job.id,
                status="queued",
                lead_id=lead_id,
            )
        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                "Celery unavailable — generating message inline for lead %s", lead_id
            )

    # Inline / fallback
    sync = get_sync_session()
    try:
        msg = generate_message_for_lead_sync(
            sync,
            lead_id=lead_id,
            organization_id=current.organization_id,
            contact_id=payload.contact_id,
            service_offered=payload.service_offered,
        )
        return MessageRead.model_validate(msg)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": str(exc)}},
        ) from exc
    finally:
        sync.close()


# --- Canonical stage machine (API_REFERENCE) ---

ALLOWED_STAGES = {
    "new",
    "contacted",
    "follow_up",
    "replied",
    "interested",
    "won",
    "lost",
    "disqualified",
    "do_not_contact",
}

# Simplified allowed transitions (Stage 1)
STAGE_TRANSITIONS: dict[str, set[str]] = {
    "new": {"contacted", "disqualified", "do_not_contact", "lost"},
    "contacted": {"follow_up", "replied", "interested", "lost", "disqualified", "do_not_contact"},
    "follow_up": {"replied", "interested", "lost", "disqualified", "do_not_contact", "contacted"},
    "replied": {"interested", "won", "lost", "follow_up", "do_not_contact"},
    "interested": {"won", "lost", "follow_up", "do_not_contact"},
    "won": set(),
    "lost": {"new"},
    "disqualified": set(),
    "do_not_contact": set(),
}


@router.post("/{lead_id}/stage", response_model=LeadRead)
async def set_lead_stage(
    lead_id: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """Canonical stage transition with validation."""
    stage = (payload or {}).get("stage")
    notes = (payload or {}).get("notes")
    if not stage or stage not in ALLOWED_STAGES:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "INVALID_STAGE",
                    "message": f"stage must be one of: {sorted(ALLOWED_STAGES)}",
                }
            },
        )
    repo = LeadRepository(db)
    lead = await repo.get_by_id(lead_id, current.organization_id)
    if not lead:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Lead not found"}},
        )
    current_stage = lead.stage or "new"
    allowed = STAGE_TRANSITIONS.get(current_stage, ALLOWED_STAGES)
    if stage != current_stage and stage not in allowed:
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "INVALID_TRANSITION",
                    "message": f"Cannot move from '{current_stage}' to '{stage}'",
                }
            },
        )
    lead = await repo.update_stage(lead, stage)
    if notes is not None:
        lead.notes = notes
        await db.commit()
        await db.refresh(lead)
    data = LeadRead.model_validate(lead)
    if lead.business:
        data.business_name = lead.business.name
        data.business_category = lead.business.category
    return data


@router.post("/{lead_id}/disqualify", response_model=LeadRead)
async def disqualify_lead(
    lead_id: UUID,
    payload: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """Mark lead disqualified (terminal). Optional reason stored in notes."""
    repo = LeadRepository(db)
    lead = await repo.get_by_id(lead_id, current.organization_id)
    if not lead:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Lead not found"}},
        )
    reason = (payload or {}).get("reason")
    lead = await repo.update_stage(lead, "disqualified")
    if reason:
        lead.notes = ((lead.notes or "") + f"\n[disqualified] {reason}").strip()
        await db.commit()
        await db.refresh(lead)
    data = LeadRead.model_validate(lead)
    if lead.business:
        data.business_name = lead.business.name
        data.business_category = lead.business.category
    return data


@router.post("/{lead_id}/do-not-contact", response_model=LeadRead)
async def do_not_contact_lead(
    lead_id: UUID,
    payload: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """
    Terminal stage + suppression side-effect for business phone/email contacts.
    """
    from sqlalchemy import select
    from app.models.contact import Contact
    from app.models.suppression import SuppressionList
    from app.models.business import Business

    repo = LeadRepository(db)
    lead = await repo.get_by_id(lead_id, current.organization_id)
    if not lead:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Lead not found"}},
        )

    lead = await repo.update_stage(lead, "do_not_contact")
    reason = (payload or {}).get("reason") or "do_not_contact"

    # Suppress all known contacts on the business
    if lead.business_id:
        contacts = (
            await db.execute(select(Contact).where(Contact.business_id == lead.business_id))
        ).scalars().all()
        for c in contacts:
            val = (c.value or "").strip().lower()
            if not val:
                continue
            exists = await db.execute(
                select(SuppressionList).where(
                    SuppressionList.organization_id == current.organization_id,
                    SuppressionList.contact_value == val,
                )
            )
            if exists.scalar_one_or_none() is None:
                db.add(
                    SuppressionList(
                        organization_id=current.organization_id,
                        contact_value=val,
                        reason=reason,
                    )
                )
        # Also suppress website host? skip — contact values only
        biz = lead.business
        if biz and biz.phone:
            ph = biz.phone.strip().lower()
            exists = await db.execute(
                select(SuppressionList).where(
                    SuppressionList.organization_id == current.organization_id,
                    SuppressionList.contact_value == ph,
                )
            )
            if exists.scalar_one_or_none() is None:
                db.add(
                    SuppressionList(
                        organization_id=current.organization_id,
                        contact_value=ph,
                        reason=reason,
                    )
                )

    await write_audit(
        db,
        action="lead.do_not_contact",
        organization_id=current.organization_id,
        user_id=current.user_id,
        resource_type="lead",
        resource_id=str(lead.id),
        meta={"reason": reason},
    )
    await db.commit()
    await db.refresh(lead)
    data = LeadRead.model_validate(lead)
    if lead.business:
        data.business_name = lead.business.name
        data.business_category = lead.business.category
    return data
