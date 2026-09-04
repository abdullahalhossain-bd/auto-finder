"""
Campaign orchestration service.
API path only does NL parse + status transitions.
Heavy work (discovery / audit / score) runs in Celery via discovery_pipeline.
"""
from typing import Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.repositories.campaign_repository import CampaignRepository
from app.services.nl_parser_service import NLParserService


class CampaignService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.campaign_repo = CampaignRepository(session)
        self.nl_parser = NLParserService()

    async def parse_and_update_params(self, campaign: Campaign) -> Campaign:
        """Parse NL input and store structured params (fast, stays in request)."""
        params = self.nl_parser.parse(campaign.natural_language_input)
        return await self.campaign_repo.update(campaign, structured_params=params)

    async def mark_discovering(self, campaign: Campaign) -> Campaign:
        return await self.campaign_repo.update(campaign, status="discovering")

    async def run_discovery(self, campaign: Campaign) -> Dict[str, Any]:
        """
        DEPRECATED for request path. Kept for tests / emergency fallback.
        Prefer enqueue_discovery_job() from the API layer.
        """
        from app.core.sync_db import get_sync_session
        from app.services.discovery_pipeline import run_discovery_pipeline_sync

        # Bridge: run sync pipeline in a separate sync session to avoid
        # mixing async session state. Still blocks the caller — only use
        # when Celery is unavailable.
        sync = get_sync_session()
        try:
            return run_discovery_pipeline_sync(sync, campaign.id)
        finally:
            sync.close()
            # Refresh campaign from async session
            await self.session.refresh(campaign)
