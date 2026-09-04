"""GET /usage — plan caps vs current month (live counts + materialised usage row)."""
from datetime import datetime, timezone

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
    score_tier,
)
from app.services.subscription_service import SubscriptionService
from app.services.usage_service import current_period, get_usage_row_async

router = APIRouter(tags=["usage"])


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


@router.get("/usage")
async def get_usage(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    org = await db.get(Organization, current.organization_id)
    plan = normalize_plan(org.plan if org else "free")
    caps = get_plan_caps(plan)
    since = _month_start()
    period = current_period()

    campaigns = (
        await db.execute(
            select(func.count())
            .select_from(Campaign)
            .where(
                Campaign.organization_id == current.organization_id,
                Campaign.created_at >= since,
            )
        )
    ).scalar_one()

    leads = (
        await db.execute(
            select(func.count())
            .select_from(Lead)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .where(
                Campaign.organization_id == current.organization_id,
                Lead.created_at >= since,
            )
        )
    ).scalar_one()

    messages_sent = (
        await db.execute(
            select(func.count())
            .select_from(Message)
            .join(Lead, Message.lead_id == Lead.id)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .where(
                Campaign.organization_id == current.organization_id,
                Message.status == "sent",
                Message.sent_at >= since,
            )
        )
    ).scalar_one()

    sub = (
        await db.execute(
            select(Subscription).where(Subscription.organization_id == current.organization_id)
        )
    ).scalar_one_or_none()

    materialised = await get_usage_row_async(db, current.organization_id, period)
    counters = {
        "campaigns_count": int(materialised.campaigns_count) if materialised else None,
        "leads_count": int(materialised.leads_count) if materialised else None,
        "messages_sent_count": int(materialised.messages_sent_count) if materialised else None,
        "llm_calls_count": int(materialised.llm_calls_count) if materialised else 0,
    }

    leads_i = int(leads)
    lead_limit = int(caps["max_leads_per_month"])
    lead_remaining = max(0, lead_limit - leads_i)
    lead_percent = round((leads_i / lead_limit) * 100, 1) if lead_limit else 0.0
    sub_status = sub.status if sub else "trialing"
    paid = is_paid_plan(plan, sub_status)

    return {
        "plan": plan,
        "subscription_status": sub_status,
        "is_paid": paid,
        "period": period,
        "period_start": since.isoformat(),
        "usage": {
            "campaigns": int(campaigns),
            "leads": leads_i,
            "messages_sent": int(messages_sent),
            "llm_calls": counters["llm_calls_count"] or 0,
        },
        # Explicit quota UX fields (do not confuse with generation progress)
        "leads_used": leads_i,
        "leads_limit": lead_limit,
        "leads_remaining": lead_remaining,
        "percent_used": lead_percent,
        "quota_label": f"{leads_i} / {lead_limit} Leads Used",
        "materialised": counters,
        "caps": caps,
        "remaining": {
            "campaigns": max(0, int(caps["max_campaigns_per_month"]) - int(campaigns)),
            "leads": lead_remaining,
        },
        "features": {f: has_feature(plan, f, sub_status) for f in sorted(PAID_FEATURES)},
    }
