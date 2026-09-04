from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class SuppressionCreate(BaseModel):
    contact_value: str = Field(..., min_length=3, max_length=255)
    reason: Optional[str] = None


class SuppressionRead(BaseModel):
    id: UUID
    organization_id: UUID
    contact_value: str
    reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
