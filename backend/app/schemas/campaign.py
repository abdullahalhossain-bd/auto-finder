from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field


class CampaignCreate(BaseModel):
    natural_language_input: str = Field(..., min_length=10, max_length=2000)
    structured_params: Optional[dict[str, Any]] = None


class CampaignUpdate(BaseModel):
    structured_params: Optional[dict[str, Any]] = None
    status: Optional[str] = None


class CampaignRead(BaseModel):
    id: UUID
    organization_id: UUID
    natural_language_input: str
    structured_params: Optional[dict[str, Any]] = None
    status: str
    total_leads_found: int
    qualified_leads: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignList(BaseModel):
    items: list[CampaignRead]
    total: int
