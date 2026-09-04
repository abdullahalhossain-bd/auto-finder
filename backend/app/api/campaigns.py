from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser
from app.repositories.campaign_repository import CampaignRepository
from app.services.campaign_service import CampaignService
from app.schemas.campaign import CampaignCreate, CampaignRead, CampaignList, CampaignUpdate
from app.services.plan_limits import PlanLimitExceeded, assert_can_create_campaign, assert_lead_capacity
from app.core.logging_config import log_event

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    try:
        await assert_can_create_campaign(db, current.organization_id)
        # Free plan: hard 40-lead monthly cap before starting generation
        await assert_lead_capacity(db, current.organization_id, additional=1)
    except PlanLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": exc.code, "message": exc.message}},
        ) from exc

    repo = CampaignRepository(db)
    campaign = await repo.create(
        organization_id=current.organization_id,
        natural_language_input=payload.natural_language_input,
    )
    service = CampaignService(db)
    campaign = await service.parse_and_update_params(campaign)
    # Merge client structured_params (industry/city/sources) without dropping parser output
    if payload.structured_params:
        merged = dict(campaign.structured_params or {})
        merged.update(payload.structured_params)
        campaign = await repo.update(campaign, structured_params=merged)
    return campaign


@router.get("", response_model=CampaignList)
async def list_campaigns(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    repo = CampaignRepository(db)
    items, total = await repo.list_by_org(current.organization_id, limit=limit, offset=offset)
    return CampaignList(items=list(items), total=total)


@router.get("/{campaign_id}", response_model=CampaignRead)
async def get_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    repo = CampaignRepository(db)
    campaign = await repo.get_by_id(campaign_id, current.organization_id)
    if not campaign:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Campaign not found"}},
        )
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignRead)
async def update_campaign(
    campaign_id: UUID,
    payload: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    repo = CampaignRepository(db)
    campaign = await repo.get_by_id(campaign_id, current.organization_id)
    if not campaign:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Campaign not found"}},
        )
    updated = await repo.update(campaign, **payload.model_dump(exclude_unset=True))
    return updated


@router.post("/{campaign_id}/start", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def start_campaign_discovery(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """
    Enqueue discovery + scoring as a Celery job.
    Returns immediately with status=discovering — does NOT block on Overpass.
    Poll GET /campaigns/{id} until status is ready_for_review | failed | cancelled.
    """
    repo = CampaignRepository(db)
    campaign = await repo.get_by_id(campaign_id, current.organization_id)
    if not campaign:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Campaign not found"}},
        )
    if campaign.status not in ("draft", "paused", "failed", "ready_for_review"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_STATE",
                    "message": f"Cannot start campaign in status: {campaign.status}",
                }
            },
        )
    if not campaign.structured_params:
        # First time this campaign is started: parse NL → structured params.
        # (If structured_params already exists — including a user's manual
        # PATCH correction — we respect it as-is rather than overwriting it.)
        service = CampaignService(db)
        campaign = await service.parse_and_update_params(campaign)

    params = campaign.structured_params or {}
    missing = [field for field in ("city", "business_type") if not params.get(field)]
    if missing:
        # Do NOT enqueue a Celery job or flip status to "discovering" for a
        # campaign we already know can't run — that just produces a
        # confusing "failed" campaign later. Tell the user now, precisely.
        missing_label = " and ".join(missing)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": (
                        f"Could not determine {missing_label} from your campaign "
                        f"description. Please edit the campaign to clearly state "
                        f"{missing_label} (e.g. \"restaurants in Chicago\") and try again."
                    ),
                    "missing_fields": missing,
                    "structured_params": params,
                }
            },
        )

    await repo.update(campaign, status="discovering")
    log_event(
        "discovery.enqueued",
        campaign_id=str(campaign.id),
        organization_id=str(current.organization_id),
        user_id=str(current.user_id),
    )

    job_id = None
    queued = False
    try:
        from app.workers.tasks import run_campaign_discovery

        async_result = run_campaign_discovery.delay(
            str(campaign.id),
            str(current.organization_id),
        )
        job_id = async_result.id
        queued = True
        from app.models.job import Job
        job_row = Job(
            organization_id=current.organization_id,
            type="discovery.run_campaign",
            status="queued",
            celery_task_id=job_id,
        )
        db.add(job_row)
        await db.commit()
        await db.refresh(job_row)
        job_id = str(job_row.id)  # return DB job id for GET /jobs/{id}

    except Exception:
        # Redis/Celery down — last-resort inline (still better than silent failure)
        import logging

        logging.getLogger(__name__).exception(
            "Celery unavailable — running discovery inline for campaign %s",
            campaign.id,
        )
        service = CampaignService(db)
        result = await service.run_discovery(campaign)
        return {
            "campaign_id": str(campaign.id),
            "status": "ready_for_review" if "error" not in result else "failed",
            "queued": False,
            "inline_fallback": True,
            "result": result,
        }

    return {
        "campaign_id": str(campaign.id),
        "status": "discovering",
        "queued": queued,
        "job_id": job_id,
        "message": "Discovery started in background. Poll GET /campaigns/{id} for status.",
    }


@router.post("/{campaign_id}/cancel", response_model=dict)
async def cancel_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """Cancel a campaign; in-flight worker checks status and stops writing new leads."""
    repo = CampaignRepository(db)
    campaign = await repo.get_by_id(campaign_id, current.organization_id)
    if not campaign:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Campaign not found"}},
        )
    await repo.update(campaign, status="cancelled")
    return {"status": "cancelled", "campaign_id": str(campaign_id)}


@router.get("/{campaign_id}/leads", response_model=dict)
async def list_campaign_leads(
    campaign_id: UUID,
    stage: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """API_REFERENCE: list leads nested under campaign."""
    from app.repositories.lead_repository import LeadRepository
    from app.schemas.lead import LeadRead

    repo = CampaignRepository(db)
    campaign = await repo.get_by_id(campaign_id, current.organization_id)
    if not campaign:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Campaign not found"}},
        )
    lead_repo = LeadRepository(db)
    items, total = await lead_repo.list_by_campaign(
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
            data.business_address = lead.business.address
            data.business_phone = lead.business.phone
            data.business_website = lead.business.website_url
        result.append(data)
    return {"items": result, "total": total}


@router.delete("/{campaign_id}", response_model=dict)
async def delete_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """Soft-delete campaign + nested leads/messages."""
    from app.services.soft_delete_service import soft_delete_campaign
    from app.services.audit_service import write_audit

    repo = CampaignRepository(db)
    campaign = await repo.get_by_id(campaign_id, current.organization_id)
    if not campaign:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Campaign not found"}},
        )
    await soft_delete_campaign(db, campaign)
    await write_audit(
        db,
        action="campaign.soft_delete",
        organization_id=current.organization_id,
        user_id=current.user_id,
        resource_type="campaign",
        resource_id=str(campaign_id),
    )
    await db.commit()
    return {"status": "deleted", "id": str(campaign_id)}