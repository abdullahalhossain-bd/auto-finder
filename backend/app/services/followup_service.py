"""
Follow-up scheduling (Stage 1: max 1 per parent message).

Free stack only: template body, Celery + Redis, existing ESP on later approve.
When due, creates a *new* Message in pending_approval — never auto-sends.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger, log_event
from app.models.campaign import Campaign
from app.models.followup import Followup
from app.models.lead import Lead
from app.models.message import Message
from app.models.suppression import SuppressionList

logger = get_logger(__name__)

DEFAULT_DELAY_DAYS = 3
MAX_DELAY_DAYS = 30

FOLLOWUP_TEMPLATE = """Hi {name},

Just following up on my earlier note about helping with {service}.
Happy to share a quick idea if useful — no pressure either way.

Best regards
"""


class FollowupError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def schedule_followup(
    session: AsyncSession,
    *,
    organization_id: UUID,
    message_id: UUID,
    delay_days: int = DEFAULT_DELAY_DAYS,
    scheduled_at: Optional[datetime] = None,
) -> Followup:
    """
    Schedule at most one follow-up for a *sent* parent message.
    """
    msg = await session.get(Message, message_id)
    if msg is None:
        raise FollowupError("NOT_FOUND", "Message not found")

    lead = await session.get(Lead, msg.lead_id)
    if lead is None:
        raise FollowupError("NOT_FOUND", "Lead not found")
    camp = await session.get(Campaign, lead.campaign_id)
    if camp is None or camp.organization_id != organization_id:
        raise FollowupError("NOT_FOUND", "Message not found")

    if msg.status != "sent":
        raise FollowupError(
            "INVALID_STATUS",
            "Follow-up can only be scheduled after the original message is sent.",
        )

    if lead.stage in ("do_not_contact", "disqualified", "won", "lost"):
        raise FollowupError(
            "LEAD_CLOSED",
            f"Cannot schedule follow-up for lead in stage '{lead.stage}'.",
        )

    existing = (
        await session.execute(select(Followup).where(Followup.message_id == message_id))
    ).scalar_one_or_none()
    if existing and existing.status in ("scheduled", "sent", "processed"):
        raise FollowupError(
            "ALREADY_EXISTS",
            "A follow-up is already scheduled or completed for this message (max 1).",
        )

    if scheduled_at is None:
        days = max(1, min(int(delay_days or DEFAULT_DELAY_DAYS), MAX_DELAY_DAYS))
        scheduled_at = _utcnow() + timedelta(days=days)
    elif scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

    if scheduled_at <= _utcnow():
        raise FollowupError("INVALID_TIME", "scheduled_at must be in the future")

    row = Followup(
        organization_id=organization_id,
        lead_id=lead.id,
        message_id=message_id,
        status="scheduled",
        scheduled_at=scheduled_at,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    log_event(
        "followup.scheduled",
        organization_id=str(organization_id),
        message_id=str(message_id),
        followup_id=str(row.id),
        scheduled_at=scheduled_at.isoformat(),
    )
    return row


async def cancel_followup(
    session: AsyncSession,
    *,
    organization_id: UUID,
    followup_id: UUID,
) -> Followup:
    row = await session.get(Followup, followup_id)
    if row is None or row.organization_id != organization_id:
        raise FollowupError("NOT_FOUND", "Follow-up not found")
    if row.status != "scheduled":
        raise FollowupError("INVALID_STATUS", f"Cannot cancel status '{row.status}'")
    row.status = "cancelled"
    await session.commit()
    await session.refresh(row)
    log_event("followup.cancelled", followup_id=str(row.id))
    return row


def _recipient_suppressed(session: Session, organization_id: UUID, email: Optional[str]) -> bool:
    if not email:
        return False
    val = email.strip().lower()
    found = (
        session.execute(
            select(SuppressionList).where(
                SuppressionList.organization_id == organization_id,
                SuppressionList.contact_value == val,
            )
        )
        .scalars()
        .first()
    )
    return found is not None


def process_due_followups_sync(session: Session, *, limit: int = 50) -> dict:
    """
    Pick due scheduled follow-ups and create pending_approval messages (template).
    Free: no paid LLM required.
    """
    now = _utcnow()
    rows = (
        session.execute(
            select(Followup)
            .where(
                Followup.status == "scheduled",
                Followup.scheduled_at <= now,
            )
            .order_by(Followup.scheduled_at.asc())
            .limit(limit)
        )
        .scalars()
        .all()
    )

    created = 0
    skipped = 0
    for fu in rows:
        parent = session.get(Message, fu.message_id)
        lead = session.get(Lead, fu.lead_id)
        if parent is None or lead is None:
            fu.status = "skipped"
            skipped += 1
            continue
        if lead.stage in ("do_not_contact", "disqualified"):
            fu.status = "skipped"
            skipped += 1
            continue
        if parent.to_email and _recipient_suppressed(session, fu.organization_id, parent.to_email):
            fu.status = "skipped"
            skipped += 1
            continue

        name = "there"
        if lead.business and getattr(lead.business, "name", None):
            name = lead.business.name
        else:
            # lazy load business
            from app.models.business import Business

            biz = session.get(Business, lead.business_id)
            if biz and biz.name:
                name = biz.name

        body = FOLLOWUP_TEMPLATE.format(name=name, service="your online presence")
        subject = f"Following up — {name}" if name != "there" else "Following up"
        provider = "template_followup"
        rationale = "Scheduled follow-up (template; requires human approval)"

        # Prefer configured LLM (same gateway as initial outreach)
        try:
            from app.services.llm_service import get_llm_service, build_business_facts_from_lead

            biz = None
            if lead.business_id:
                from app.models.business import Business as BizModel
                biz = session.get(BizModel, lead.business_id)
            facts = build_business_facts_from_lead(
                name=name if name != "there" else (biz.name if biz else None),
                category=biz.category if biz else None,
                address=biz.address if biz else None,
                website_url=biz.website_url if biz else None,
                phone=biz.phone if biz else None,
                score_breakdown=lead.score_breakdown,
                website_audit=None,
                city=None,
            )
            llm = get_llm_service()
            result = llm.personalize_message_sync(
                business_facts=facts,
                service_offered="your online presence",
                template=FOLLOWUP_TEMPLATE,
            )
            if result and not result.used_fallback:
                body = result.body
                subject = result.subject or subject
                provider = result.provider or "ollama"
                rationale = result.rationale or "Scheduled follow-up (LLM; requires human approval)"
            elif result:
                body = result.body or body
                subject = result.subject or subject
                provider = "template_followup"
                rationale = result.rationale or rationale
            from app.services.usage_service import increment_usage_sync
            increment_usage_sync(session, fu.organization_id, "llm_calls_count")
        except Exception as exc:
            log_event(
                "followup.llm_fallback",
                followup_id=str(fu.id),
                error=str(exc)[:200],
            )

        child = Message(
            lead_id=lead.id,
            contact_id=parent.contact_id,
            content=body,
            subject=subject,
            status="pending_approval",
            to_email=parent.to_email,
            generation_provider=provider,
            ai_rationale=rationale,
        )
        session.add(child)
        session.flush()

        fu.status = "processed"
        fu.sent_at = now  # "processed at"
        if lead.stage in ("new", "contacted"):
            lead.stage = "follow_up"
        created += 1
        log_event(
            "followup.processed",
            followup_id=str(fu.id),
            new_message_id=str(child.id),
            organization_id=str(fu.organization_id),
        )

    session.commit()
    return {"processed": created, "skipped": skipped, "examined": len(rows)}
