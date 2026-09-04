"""SubscriptionService — plan status & paid feature checks."""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.plan_limits import (
    PAID_FEATURES,
    assert_paid_feature,
    get_plan_caps,
    has_feature,
    is_paid_plan,
    normalize_plan,
)


class SubscriptionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_plan_snapshot(self, organization_id: UUID) -> dict[str, Any]:
        from sqlalchemy import select
        from app.models.organization import Organization
        from app.models.subscription import Subscription

        org = await self.session.get(Organization, organization_id)
        plan = normalize_plan(org.plan if org else "free")
        result = await self.session.execute(
            select(Subscription).where(Subscription.organization_id == organization_id)
        )
        sub = result.scalar_one_or_none()
        status = sub.status if sub else "trialing"
        return {
            "plan": plan,
            "status": status,
            "is_paid": is_paid_plan(plan, status),
            "caps": get_plan_caps(plan),
            "features": {
                f: has_feature(plan, f, status) for f in sorted(PAID_FEATURES)
            },
            "trial_end": sub.trial_end.isoformat() if sub and sub.trial_end else None,
            "current_period_end": (
                sub.current_period_end.isoformat() if sub and sub.current_period_end else None
            ),
        }

    async def check_paid_subscription(self, organization_id: UUID, feature: str) -> None:
        await assert_paid_feature(self.session, organization_id, feature)
