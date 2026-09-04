"""
Plan / trial volume caps + subscription status enforcement
(CODING_STANDARDS rule 13 — not UI-only).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

PLAN_CAPS = {
    "trial": {"max_campaigns_per_month": 1, "max_leads_per_month": 25},
    "starter": {"max_campaigns_per_month": 10, "max_leads_per_month": 500},
    "pro": {"max_campaigns_per_month": 50, "max_leads_per_month": 5000},
}


class PlanLimitExceeded(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def get_plan_caps(plan: Optional[str]) -> dict:
    return dict(PLAN_CAPS.get((plan or "trial").lower(), PLAN_CAPS["trial"]))


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def assert_subscription_allows_writes(session, organization_id: UUID) -> None:
    """Block campaign creation when subscription is past_due / cancelled / trial expired."""
    from sqlalchemy import select

    from app.models.subscription import Subscription

    result = await session.execute(
        select(Subscription).where(Subscription.organization_id == organization_id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        # Legacy orgs without a row — allow with trial caps only
        return

    if sub.status in ("past_due", "cancelled"):
        raise PlanLimitExceeded(
            "SUBSCRIPTION_INACTIVE",
            f"Your subscription is '{sub.status}'. Update billing before creating campaigns.",
        )

    if sub.status == "trialing" and sub.trial_end is not None:
        end = sub.trial_end
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if end < datetime.now(timezone.utc):
            raise PlanLimitExceeded(
                "TRIAL_EXPIRED",
                "Your trial has ended. Subscribe to Starter or Pro to continue.",
            )


async def assert_can_create_campaign(session, organization_id: UUID) -> None:
    from sqlalchemy import func, select

    from app.models.campaign import Campaign
    from app.models.organization import Organization

    await assert_subscription_allows_writes(session, organization_id)

    org = await session.get(Organization, organization_id)
    if org is None:
        raise PlanLimitExceeded("ORG_NOT_FOUND", "Organization not found")
    if getattr(org, "deleted_at", None) is not None:
        raise PlanLimitExceeded("ORG_DELETED", "This organization has been deleted.")

    plan = (org.plan or "trial").lower()
    caps = PLAN_CAPS.get(plan, PLAN_CAPS["trial"])
    since = _month_start()

    count = (
        await session.execute(
            select(func.count())
            .select_from(Campaign)
            .where(
                Campaign.organization_id == organization_id,
                Campaign.created_at >= since,
            )
        )
    ).scalar_one()

    if int(count) >= int(caps["max_campaigns_per_month"]):
        raise PlanLimitExceeded(
            "CAMPAIGN_CAP_REACHED",
            f"Your {plan} plan allows {caps['max_campaigns_per_month']} campaign(s) per month. "
            f"Upgrade or wait until next billing period.",
        )


async def assert_lead_capacity(session, organization_id: UUID, additional: int = 1) -> None:
    from sqlalchemy import func, select

    from app.models.campaign import Campaign
    from app.models.lead import Lead
    from app.models.organization import Organization

    await assert_subscription_allows_writes(session, organization_id)

    org = await session.get(Organization, organization_id)
    if org is None:
        raise PlanLimitExceeded("ORG_NOT_FOUND", "Organization not found")
    plan = (org.plan or "trial").lower()
    caps = PLAN_CAPS.get(plan, PLAN_CAPS["trial"])
    since = _month_start()

    count = (
        await session.execute(
            select(func.count())
            .select_from(Lead)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .where(
                Campaign.organization_id == organization_id,
                Lead.created_at >= since,
            )
        )
    ).scalar_one()

    if int(count) + additional > int(caps["max_leads_per_month"]):
        raise PlanLimitExceeded(
            "LEAD_CAP_REACHED",
            f"Your {plan} plan allows {caps['max_leads_per_month']} leads per month.",
        )


async def assert_can_send_outbound(session, organization_id: UUID) -> None:
    """
    Gate outbound email (approve + worker).
    Blocks past_due / cancelled / expired trial — same rules as campaign writes.
    """
    await assert_subscription_allows_writes(session, organization_id)


def assert_can_send_outbound_sync(session, organization_id: UUID) -> None:
    """Sync variant for Celery worker / outreach_service."""
    from sqlalchemy import select
    from datetime import datetime, timezone

    from app.models.subscription import Subscription

    result = session.execute(
        select(Subscription).where(Subscription.organization_id == organization_id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        return

    if sub.status in ("past_due", "cancelled"):
        raise PlanLimitExceeded(
            "SUBSCRIPTION_INACTIVE",
            f"Your subscription is '{sub.status}'. Update billing before sending.",
        )

    if sub.status == "trialing" and sub.trial_end is not None:
        end = sub.trial_end
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if end < datetime.now(timezone.utc):
            raise PlanLimitExceeded(
                "TRIAL_EXPIRED",
                "Your trial has ended. Subscribe to Starter or Pro to continue sending.",
            )
