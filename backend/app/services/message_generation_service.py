"""
Orchestrates template + LLM personalization for a lead.
Creates a Message in pending_approval with subject/body/rationale metadata.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.business import Business
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.message import Message
from app.models.website_audit import WebsiteAudit
from app.services.llm_service import (
    PersonalizeResult,
    build_business_facts_from_lead,
    get_llm_service,
    llm_endpoint_info,
)

logger = logging.getLogger(__name__)


def _default_service_from_campaign(campaign: Optional[Campaign]) -> str:
    if not campaign:
        return "websites and online booking"
    params = campaign.structured_params or {}
    # NL filters sometimes encode service intent
    service = params.get("service") or params.get("service_offered")
    if service:
        return str(service)
    signals = (params.get("filters") or {})
    if signals.get("no_website"):
        return "professional websites"
    if signals.get("no_booking"):
        return "online booking systems"
    return "websites and online booking"


def generate_message_for_lead_sync(
    session: Session,
    *,
    lead_id: UUID,
    organization_id: UUID,
    contact_id: Optional[UUID] = None,
    service_offered: Optional[str] = None,
    template: Optional[str] = None,
    provider: str = "ollama",
    api_key: Optional[str] = None,
) -> Message:
    """
    Sync generation for Celery or inline fallback.
    Loads lead+business+audit, calls LLM gateway, inserts Message(pending_approval).
    """
    lead = session.execute(
        select(Lead)
        .where(Lead.id == lead_id)
        .options(
            selectinload(Lead.business).selectinload(Business.website_audits),
            selectinload(Lead.campaign),
        )
    ).scalar_one_or_none()
    if lead is None:
        raise ValueError("Lead not found")

    campaign = lead.campaign
    if campaign is None or campaign.organization_id != organization_id:
        raise ValueError("Lead not found in organization")

    business = lead.business
    if business is None:
        raise ValueError("Lead has no business")

    audit_row = None
    if business.website_audits:
        audit_row = sorted(
            business.website_audits,
            key=lambda a: a.crawled_at or a.created_at,
            reverse=True,
        )[0]
    audit_dict: Dict[str, Any] = {}
    if audit_row:
        audit_dict = {
            "has_ssl": audit_row.has_ssl,
            "has_viewport": audit_row.has_viewport,
            "booking_vendor_detected": audit_row.booking_vendor_detected,
            "http_status": audit_row.http_status,
        }

    city = None
    if campaign.structured_params:
        city = campaign.structured_params.get("city")

    facts = build_business_facts_from_lead(
        name=business.name,
        category=business.category,
        address=business.address,
        website_url=business.website_url,
        phone=business.phone,
        score_breakdown=lead.score_breakdown,
        website_audit=audit_dict,
        city=city,
    )
    service = service_offered or _default_service_from_campaign(campaign)

    # Always go through configured gateway (LLM_LOCAL / LLM_MODEL / LLM_REMOTE_URL)
    llm = get_llm_service(provider=provider, api_key=api_key)
    try:
        info = llm_endpoint_info()
        logger.info(
            "message.generate via llm local=%s model=%s url=%s",
            info.get("llm_local"),
            info.get("model"),
            info.get("chat_url"),
        )
    except Exception:
        pass
    result: PersonalizeResult = llm.personalize_message_sync(
        business_facts=facts,
        service_offered=service,
        template=template,
    )
    from app.services.usage_service import increment_usage_sync
    # Count gateway call (Ollama free or template still counts as a personalize attempt)
    increment_usage_sync(session, organization_id, "llm_calls_count")

    # Store generation metadata in content prefix is avoided; use subject + optional note in last fields
    message = Message(
        lead_id=lead.id,
        contact_id=contact_id,
        content=result.body,
        subject=result.subject,
        status="pending_approval",
        ai_rationale=result.rationale,
        generation_provider=result.provider,
    )
    session.add(message)
    session.commit()
    session.refresh(message)

    logger.info(
        "message.generated lead=%s message=%s provider=%s fallback=%s latency_ms=%s",
        lead_id,
        message.id,
        result.provider,
        result.used_fallback,
        result.latency_ms,
    )
    # Attach transient attrs for API response (not columns)
    message._generation_meta = {  # type: ignore[attr-defined]
        "provider": result.provider,
        "used_fallback": result.used_fallback,
        "rationale": result.rationale,
        "latency_ms": result.latency_ms,
        "prompt_version": result.prompt_version,
        "facts_used": result.facts_used,
    }
    return message
