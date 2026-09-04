"""UsageLimitService — quota checks before lead generation."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.plan_limits import (
    PlanLimitExceeded,
    assert_lead_capacity,
    check_lead_limit,
)


class UsageLimitService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def check_lead_limit(self, organization_id: UUID) -> dict[str, Any]:
        """Snapshot of lead quota. Raises if at limit when enforcing create."""
        return await check_lead_limit(self.session, organization_id)

    async def assert_can_generate_leads(
        self, organization_id: UUID, additional: int = 1
    ) -> dict[str, Any]:
        snap = await check_lead_limit(self.session, organization_id)
        if snap["at_limit"] or additional > snap["leads_remaining"]:
            raise PlanLimitExceeded(
                "LEAD_CAP_REACHED",
                f"Lead quota exhausted: {snap['leads_used']}/{snap['leads_limit']} used. "
                f"Upgrade to generate more leads.",
            )
        await assert_lead_capacity(self.session, organization_id, additional=additional)
        return snap
