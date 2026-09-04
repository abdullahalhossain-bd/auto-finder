import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.membership import Membership


class MembershipRepository:
    """
    Per FINAL_SYSTEM_SPEC.md Section 2: every repository method that reads
    or writes organization-owned data takes organization_id as a mandatory
    first parameter, enforced here rather than only at the API layer.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, organization_id: uuid.UUID, *, user_id: uuid.UUID, role: str
    ) -> Membership:
        membership = Membership(user_id=user_id, organization_id=organization_id, role=role)
        self._session.add(membership)
        await self._session.flush()
        return membership

    async def get(
        self, organization_id: uuid.UUID, *, user_id: uuid.UUID
    ) -> Membership | None:
        stmt = select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(self, *, user_id: uuid.UUID) -> list[Membership]:
        """
        The one intentional exception to the organization_id-first rule:
        finding *which* orgs a user belongs to has no organization_id to
        scope by yet (that's what this query determines). Used only at
        login to pick the user's default org for the access token.
        """
        stmt = select(Membership).where(Membership.user_id == user_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
