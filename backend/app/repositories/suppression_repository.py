from typing import Optional, Sequence
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.suppression import SuppressionList


class SuppressionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_suppressed(self, organization_id: UUID, contact_value: str) -> bool:
        result = await self.session.execute(
            select(SuppressionList).where(
                SuppressionList.organization_id == organization_id,
                SuppressionList.contact_value == contact_value.lower().strip(),
            )
        )
        return result.scalar_one_or_none() is not None

    async def add(
        self, organization_id: UUID, contact_value: str, reason: Optional[str] = None
    ) -> SuppressionList:
        entry = SuppressionList(
            organization_id=organization_id,
            contact_value=contact_value.lower().strip(),
            reason=reason,
        )
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def list_by_org(
        self, organization_id: UUID, limit: int = 100, offset: int = 0
    ) -> tuple[Sequence[SuppressionList], int]:
        count_result = await self.session.execute(
            select(func.count()).select_from(SuppressionList).where(
                SuppressionList.organization_id == organization_id
            )
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(SuppressionList)
            .where(SuppressionList.organization_id == organization_id)
            .order_by(SuppressionList.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all(), total
