"""GET /usage — plan caps and live usage."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.message import Message
from app.models.organization import Organization
from app.models.subscription import Subscription
from app.services.plan_limits import (
    PAID_FEATURES,
    get_plan_caps,
    has_feature,
    is_paid_plan,
    normalize_plan,
)
from app.services.usage_service import current_period, get_usage_row_async

router = APIRouter(tags=["usage"])


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _rolling_24h_start() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=24)


@router.get("/usage")
async def get_usage(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    org = await db.get(Organization, current.organization_id)
    plan = normalize_plan(org.plan if org else "trial")
    caps = get_plan_caps(plan)
    month_start = _month_start()
    period = current_period()

    campaigns = (
        await db.execute(
            select(func.count())
            .select_from(Campaign)
            .where(
                Campaign.organization_id == current.organization_id,
                Campaign.created_at >= month_start,
            )
        )
    ).scalar_one()

    sub = (
        await db.execute(
            select(Subscription).where(Subscription.organization_id == current.organization_id)
        )
    ).scalar_one_or_none()
    sub_status = sub.status if sub else "trialing"
    paid = is_paid_plan(plan, sub_status)

    # Trial/free lead usage is a rolling 24-hour window. Paid plans remain monthly.
    if plan == "trial":
        quota_start = _rolling_24h_start()
        leads = (
            await db.execute(
                select(func.count())
                .select_from(Lead)
                .join(Campaign, Lead.campaign_id == Campaign.id)
                .where(
                    Campaign.organization_id == current.organization_id,
                    Lead.created_at >= quota_start,
                )
            )
        ).scalar_one()
        lead_limit = int(caps["max_leads_per_24h"])
        quota_window = "rolling_24h"

        # When exhausted, tell the UI exactly when the oldest counted lead
        # leaves the rolling window. Otherwise there is no single reset time.
        oldest_recent = (
            await db.execute(
                select(func.min(Lead.created_at))
                .select_from(Lead)
                .join(Campaign, Lead.campaign_id == Campaign.id)
                .where(
                    Campaign.organization_id == current.organization_id,
                    Lead.created_at >= quota_start,
                )
            )
        ).scalar_one_or_none()
        quota_resets_at = (
            (oldest_recent + timedelta(hours=24)).isoformat()
            if int(leads) >= lead_limit and oldest_recent is not None
            else None
        )
    else:
        leads = (
            await db.execute(
                select(func.count())
                .select_from(Lead)
                .join(Campaign, Lead.campaign_id == Campaign.id)
                .where(
                    Campaign.organization_id == current.organization_id,
                    Lead.created_at >= month_start,
                )
            )
        ).scalar_one()
        lead_limit = int(caps["max_leads_per_month"])
        quota_window = "monthly"
        quota_resets_at = None

    messages_sent = (
        await db.execute(
            select(func.count())
            .select_from(Message)
            .join(Lead, Message.lead_id == Lead.id)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .where(
                Campaign.organization_id == current.organization_id,
                Message.status == "sent",
                Message.sent_at >= month_start,
            )
        )
    ).scalar_one()

    materialised = await get_usage_row_async(db, current.organization_id, period)
    counters = {
        "campaigns_count": int(materialised.campaigns_count) if materialised else None,
        "leads_count": int(materialised.leads_count) if materialised else None,
        "messages_sent_count": int(materialised.messages_sent_count) if materialised else None,
        "llm_calls_count": int(materialised.llm_calls_count) if materialised else 0,
    }

    leads_i = int(leads)
    lead_remaining = max(0, lead_limit - leads_i)
    lead_percent = round((leads_i / lead_limit) * 100, 1) if lead_limit else 0.0

    return {
        "plan": plan,
        "subscription_status": sub_status,
        "is_paid": paid,
        "period": period,
        "period_start": month_start.isoformat(),
        "usage": {
            "campaigns": int(campaigns),
            "leads": leads_i,
            "messages_sent": int(messages_sent),
            "llm_calls": counters["llm_calls_count"] or 0,
        },
        "leads_used": leads_i,
        "leads_limit": lead_limit,
        "leads_remaining": lead_remaining,
        "leads_quota_window": quota_window,
        "quota_resets_at": quota_resets_at,
        "percent_used": lead_percent,
        "quota_label": (
            f"{leads_i} / {lead_limit} Leads Used"
            if quota_window == "monthly"
            else f"{leads_i} / {lead_limit} Leads Used (24h)"
        ),
        "materialised": counters,
        "caps": caps,
        "remaining": {
            "campaigns": max(0, int(caps["max_campaigns_per_month"]) - int(campaigns)),
            "leads": lead_remaining,
        },
        "features": {f: has_feature(plan, f, sub_status) for f in sorted(PAID_FEATURES)},
    }
