from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """Manual draft (user-written)."""
    lead_id: UUID
    content: str = Field(..., min_length=10)
    contact_id: Optional[UUID] = None
    subject: Optional[str] = Field(None, max_length=300)


class MessageGenerateRequest(BaseModel):
    """AI generation request for a lead."""
    contact_id: Optional[UUID] = None
    service_offered: Optional[str] = Field(
        None,
        max_length=200,
        description="What you offer, e.g. 'website redesign' or 'online booking'",
    )
    async_mode: bool = Field(
        True,
        description="If true, enqueue Celery job and return 202; if false, generate inline",
    )


class MessageUpdate(BaseModel):
    content: Optional[str] = None
    subject: Optional[str] = None


class MessageRead(BaseModel):
    id: UUID
    lead_id: UUID
    contact_id: Optional[UUID] = None
    content: str
    subject: Optional[str] = None
    status: str
    approved_by: Optional[UUID] = None
    sent_at: Optional[datetime] = None
    esp_message_id: Optional[str] = None
    esp_provider: Optional[str] = None
    to_email: Optional[str] = None
    last_send_error: Optional[str] = None
    ai_rationale: Optional[str] = None
    generation_provider: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageGenerateQueued(BaseModel):
    job_id: Optional[str] = None
    status: str = "queued"
    lead_id: UUID
    message: str = "Generation started. Poll messages for this lead or approval queue."

class MessageApprove(BaseModel):
    """Approve a message for sending."""
    pass
