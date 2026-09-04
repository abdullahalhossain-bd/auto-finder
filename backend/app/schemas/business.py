from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel


class BusinessRead(BaseModel):
    id: UUID
    name: str
    category: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    website_url: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    source_data: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}
