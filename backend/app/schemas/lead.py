from datetime import datetime
from typing import Optional, Any, List
from uuid import UUID
from pydantic import BaseModel, Field


class LeadRead(BaseModel):
    id: UUID
    campaign_id: UUID
    business_id: UUID
    opportunity_score: Optional[float] = None
    score_breakdown: Optional[dict[str, Any]] = None
    stage: str
    confidence_summary: Optional[dict[str, Any]] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Nested business / contact info for list & table views
    business_name: Optional[str] = None
    business_category: Optional[str] = None
    business_city: Optional[str] = None
    business_address: Optional[str] = None
    business_phone: Optional[str] = None
    business_website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website_url: Optional[str] = None
    source: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    score_tier: Optional[str] = None
    score_tier_label: Optional[str] = None

    model_config = {"from_attributes": True}


class LeadUpdate(BaseModel):
    stage: Optional[str] = None
    notes: Optional[str] = None


class LeadList(BaseModel):
    items: list[LeadRead]
    total: int


def enrich_lead_read(lead) -> LeadRead:
    """Attach business/contact fields + score tier for API responses."""
    from app.services.plan_limits import score_tier

    data = LeadRead.model_validate(lead)
    biz = getattr(lead, "business", None)
    if biz is not None:
        data.business_name = biz.name
        data.business_category = biz.category
        data.phone = biz.phone
        data.website_url = biz.website_url
        data.source = biz.source
        data.rating = biz.rating
        data.review_count = biz.review_count
        # city from address tail or source_data
        if biz.address:
            parts = [p.strip() for p in biz.address.split(",") if p.strip()]
            data.business_city = parts[-2] if len(parts) >= 2 else parts[-1] if parts else None
        sd = biz.source_data or {}
        if not data.business_city:
            data.business_city = sd.get("city") or sd.get("town")
        # email from contacts if loaded
        contacts = getattr(biz, "contacts", None) or []
        for c in contacts:
            et = (getattr(c, "type", None) or "").lower()
            val = getattr(c, "value", None)
            if not val:
                continue
            if et == "email" or "@" in str(val):
                data.email = str(val)
            elif et == "phone" and not data.phone:
                data.phone = str(val)
    tier = score_tier(data.opportunity_score)
    data.score_tier = tier["tier"]
    data.score_tier_label = tier["label"]
    # source from score_breakdown data_sources if missing
    if not data.source and isinstance(data.score_breakdown, dict):
        srcs = data.score_breakdown.get("data_sources") or []
        if srcs:
            data.source = srcs[0]
    return data
