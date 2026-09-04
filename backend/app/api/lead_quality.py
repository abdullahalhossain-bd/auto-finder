"""
Lead quality & provenance export — competitive proof layer.

Google gives you a map pin. We give you fitness signals + exportable audit trail.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.models.business import Business
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.message import Message
from app.repositories.lead_repository import LeadRepository
from app.schemas.lead import enrich_lead_read

router = APIRouter(tags=["lead-quality"])


@router.get("/leads/quality-metrics")
async def lead_quality_metrics(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """
    Publishable-style snapshot for one org.
    Not vanity 'AI score' — coverage of contact + stage outcomes.
    """
    org_id = current.organization_id

    total = (
        await db.execute(
            select(func.count())
            .select_from(Lead)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .where(Campaign.organization_id == org_id, Lead.deleted_at.is_(None))
        )
    ).scalar_one()

    # Leads with phone on business
    with_phone = (
        await db.execute(
            select(func.count())
            .select_from(Lead)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .join(Business, Lead.business_id == Business.id)
            .where(
                Campaign.organization_id == org_id,
                Lead.deleted_at.is_(None),
                Business.phone.isnot(None),
                Business.phone != "",
            )
        )
    ).scalar_one()

    with_website = (
        await db.execute(
            select(func.count())
            .select_from(Lead)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .join(Business, Lead.business_id == Business.id)
            .where(
                Campaign.organization_id == org_id,
                Lead.deleted_at.is_(None),
                Business.website_url.isnot(None),
                Business.website_url != "",
            )
        )
    ).scalar_one()

    strong = (
        await db.execute(
            select(func.count())
            .select_from(Lead)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .where(
                Campaign.organization_id == org_id,
                Lead.deleted_at.is_(None),
                Lead.opportunity_score >= 65,
            )
        )
    ).scalar_one()

    contacted = (
        await db.execute(
            select(func.count())
            .select_from(Lead)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .where(
                Campaign.organization_id == org_id,
                Lead.deleted_at.is_(None),
                Lead.stage.in_(
                    ("contacted", "follow_up", "replied", "interested", "won")
                ),
            )
        )
    ).scalar_one()

    replied = (
        await db.execute(
            select(func.count())
            .select_from(Lead)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .where(
                Campaign.organization_id == org_id,
                Lead.deleted_at.is_(None),
                Lead.stage.in_(("replied", "interested", "won")),
            )
        )
    ).scalar_one()

    sent_msgs = (
        await db.execute(
            select(func.count())
            .select_from(Message)
            .join(Lead, Message.lead_id == Lead.id)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .where(
                Campaign.organization_id == org_id,
                Message.status == "sent",
            )
        )
    ).scalar_one()

    t = int(total) or 0

    def pct(n: int) -> float:
        return round((int(n) / t) * 100, 1) if t else 0.0

    return {
        "organization_id": str(org_id),
        "as_of": datetime.now(timezone.utc).isoformat(),
        "totals": {
            "leads": t,
            "with_phone": int(with_phone),
            "with_website": int(with_website),
            "strong_fit_score_ge_65": int(strong),
            "contacted": int(contacted),
            "replied_or_later": int(replied),
            "messages_sent": int(sent_msgs),
        },
        "rates": {
            "phone_coverage_pct": pct(with_phone),
            "website_present_pct": pct(with_website),
            "strong_fit_pct": pct(strong),
            "contacted_pct": pct(contacted),
            "reply_pct_of_leads": pct(replied),
            "reply_pct_of_contacted": (
                round((int(replied) / int(contacted)) * 100, 1) if int(contacted) else 0.0
            ),
        },
        "method": {
            "scoring": "rule_based_opportunity_fit_v1",
            "not": "google_maps_ranking_or_llm_score",
            "note": "Use these rates in sales conversations; they beat feature lists.",
        },
    }


@router.get("/leads/export.csv")
async def export_leads_csv(
    campaign_id: Optional[UUID] = Query(None),
    stage: Optional[str] = Query(None),
    limit: int = Query(2000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """
    Provenance-rich CSV — not a bare Places dump.
    Includes score, tier, source, phone, website, breakdown signals.
    """
    repo = LeadRepository(db)
    if campaign_id is not None:
        items, _ = await repo.list_by_campaign(
            campaign_id=campaign_id,
            organization_id=current.organization_id,
            stage=stage,
            limit=limit,
            offset=0,
        )
    else:
        items, _ = await repo.list_by_org(
            organization_id=current.organization_id,
            stage=stage,
            limit=limit,
            offset=0,
        )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "lead_id",
            "business_name",
            "category",
            "city",
            "phone",
            "email",
            "website_url",
            "source",
            "rating",
            "review_count",
            "opportunity_score",
            "score_tier",
            "stage",
            "score_signals",
            "campaign_id",
            "exported_at",
        ]
    )
    now = datetime.now(timezone.utc).isoformat()
    for lead in items:
        row = enrich_lead_read(lead)
        signals = ""
        if isinstance(row.score_breakdown, dict):
            rules = row.score_breakdown.get("rules") or []
            if isinstance(rules, list):
                signals = ";".join(
                    f"{r.get('signal', '')}:{r.get('points', '')}"
                    for r in rules
                    if isinstance(r, dict)
                )
        writer.writerow(
            [
                str(row.id),
                row.business_name or "",
                row.business_category or "",
                row.business_city or "",
                row.phone or "",
                row.email or "",
                row.website_url or "",
                row.source or "",
                row.rating if row.rating is not None else "",
                row.review_count if row.review_count is not None else "",
                row.opportunity_score if row.opportunity_score is not None else "",
                row.score_tier_label or row.score_tier or "",
                row.stage,
                signals,
                str(row.campaign_id),
                now,
            ]
        )

    buf.seek(0)
    filename = f"leads-export-{current.organization_id}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
