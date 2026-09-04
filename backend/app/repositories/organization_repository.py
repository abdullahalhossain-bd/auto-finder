import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization


class OrganizationRepository:
    """
    Organizations are the tenant boundary itself, so lookups here are by the
    org's own id — there is no "outer" organization_id to scope by. Callers
    (the auth API) are responsible for only ever looking up the org(s) a
    user's memberships actually grant access to.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, name: str, plan: str = "trial") -> Organization:
        org = Organization(name=name, plan=plan)
        self._session.add(org)
        await self._session.flush()
        return org

    async def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        return await self._session.get(Organization, organization_id)
