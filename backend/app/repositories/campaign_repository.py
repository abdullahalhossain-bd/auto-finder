from typing import Optional, Sequence
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign


class CampaignRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, organization_id: UUID, natural_language_input: str) -> Campaign:
        campaign = Campaign(
            organization_id=organization_id,
            natural_language_input=natural_language_input,
            status="draft",
        )
        self.session.add(campaign)
        await self.session.flush()
        from app.services.usage_service import increment_usage_async
        await increment_usage_async(
            self.session, organization_id, "campaigns_count"
        )
        await self.session.commit()
        await self.session.refresh(campaign)
        return campaign

    async def get_by_id(self, campaign_id: UUID, organization_id: UUID) -> Optional[Campaign]:
        result = await self.session.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.organization_id == organization_id,
                Campaign.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self, organization_id: UUID, limit: int = 50, offset: int = 0
    ) -> tuple[Sequence[Campaign], int]:
        count_result = await self.session.execute(
            select(func.count()).select_from(Campaign).where(
                Campaign.organization_id == organization_id,
                Campaign.deleted_at.is_(None),
            )
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(Campaign)
            .where(
                Campaign.organization_id == organization_id,
                Campaign.deleted_at.is_(None),
            )
            .order_by(Campaign.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all(), total

    async def update(self, campaign: Campaign, **kwargs) -> Campaign:
        for key, value in kwargs.items():
            if value is not None and hasattr(campaign, key):
                setattr(campaign, key, value)
        await self.session.commit()
        await self.session.refresh(campaign)
        return campaign
