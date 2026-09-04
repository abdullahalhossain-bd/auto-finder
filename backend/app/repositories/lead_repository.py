from typing import Optional, Sequence
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lead import Lead
from app.models.business import Business
from app.models.contact import Contact


class LeadRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, lead_id: UUID, organization_id: UUID) -> Optional[Lead]:
        result = await self.session.execute(
            select(Lead)
            .join(Lead.campaign)
            .where(
                Lead.id == lead_id,
                Lead.campaign.has(organization_id=organization_id),
                Lead.deleted_at.is_(None),
            )
            .options(selectinload(Lead.business).selectinload(Business.contacts), selectinload(Lead.messages))
        )
        return result.scalar_one_or_none()

    async def list_by_campaign(
        self,
        campaign_id: UUID,
        organization_id: UUID,
        stage: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[Lead], int]:
        base = (
            select(Lead)
            .join(Lead.campaign)
            .where(
                Lead.campaign_id == campaign_id,
                Lead.campaign.has(organization_id=organization_id),
                Lead.deleted_at.is_(None),
            )
        )
        if stage:
            base = base.where(Lead.stage == stage)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_q)).scalar_one()

        result = await self.session.execute(
            base.options(selectinload(Lead.business).selectinload(Business.contacts))
            .order_by(Lead.opportunity_score.desc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all(), total

    async def update_stage(self, lead: Lead, stage: str) -> Lead:
        lead.stage = stage
        await self.session.commit()
        await self.session.refresh(lead)
        return lead
