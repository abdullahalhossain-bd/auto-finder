"""
ESP webhooks (bounce / complaint) and public unsubscribe endpoint.

Unsubscribe is public (token-based) — no JWT required.
Bounce webhook is provider-specific; currently supports Resend-style payloads
and a generic JSON shape for console/testing.
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.message import Message
from app.models.suppression import SuppressionList

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


class UnsubscribeResponse(BaseModel):
    ok: bool
    message: str


@router.get("/unsubscribe", response_model=UnsubscribeResponse)
@router.post("/unsubscribe", response_model=UnsubscribeResponse)
async def unsubscribe(
    token: str = Query(..., min_length=8),
    db: AsyncSession = Depends(get_db),
):
    """
    Public one-click / link unsubscribe.
    Adds the message's to_email to the org suppression list and marks message replied path cancelled.
    """
    result = await db.execute(
        select(Message).where(Message.unsubscribe_token == token)
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Invalid unsubscribe token"}},
        )

    email = (message.to_email or "").lower().strip()
    if not email:
        return UnsubscribeResponse(ok=True, message="Already processed or no email on record")

    # Resolve organization via lead → campaign
    from app.models.lead import Lead
    from app.models.campaign import Campaign

    lead_row = await db.execute(select(Lead).where(Lead.id == message.lead_id))
    lead = lead_row.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Lead missing"}})

    camp_row = await db.execute(select(Campaign).where(Campaign.id == lead.campaign_id))
    campaign = camp_row.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Campaign missing"}})

    # Idempotent suppression insert
    existing = await db.execute(
        select(SuppressionList).where(
            SuppressionList.organization_id == campaign.organization_id,
            SuppressionList.contact_value == email,
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(
            SuppressionList(
                organization_id=campaign.organization_id,
                contact_value=email,
                reason="unsubscribed",
            )
        )

    # Mark lead do_not_contact is optional — suppression is the hard block
    await db.commit()
    logger.info("Unsubscribe processed for %s (message %s)", email, message.id)
    return UnsubscribeResponse(
        ok=True,
        message="You have been unsubscribed. You will not receive further messages from this sender.",
    )


class GenericEspEvent(BaseModel):
    """Generic bounce/complaint event for console tests and simple providers."""
    type: str = Field(..., description="bounce | complaint | delivered")
    esp_message_id: Optional[str] = None
    email: Optional[str] = None
    reason: Optional[str] = None


@router.post("/webhooks/esp")
async def esp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Provider-agnostic ESP webhook.
    Accepts Resend-style JSON ({"type": "email.bounced", "data": {...}})
    or generic GenericEspEvent.
    """
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION_ERROR", "message": "Invalid JSON"}},
        )

    event_type, esp_id, email, reason = _parse_esp_payload(payload)
    logger.info("ESP webhook type=%s esp_id=%s email=%s", event_type, esp_id, email)

    message: Optional[Message] = None
    if esp_id:
        row = await db.execute(select(Message).where(Message.esp_message_id == esp_id))
        message = row.scalar_one_or_none()
    if message is None and email:
        row = await db.execute(
            select(Message)
            .where(Message.to_email == email.lower().strip(), Message.status == "sent")
            .order_by(Message.sent_at.desc())
            .limit(1)
        )
        message = row.scalar_one_or_none()

    if message is None:
        # Acknowledge so provider does not retry forever
        return {"ok": True, "matched": False}

    if event_type in ("bounce", "email.bounced", "bounced"):
        message.status = "bounced"
        await _suppress_from_message(db, message, reason or "bounced")
        await _record_abuse_metric(db, message, kind="bounce")
    elif event_type in ("complaint", "email.complained", "complained"):
        message.status = "bounced"
        await _suppress_from_message(db, message, reason or "complained")
        await _record_abuse_metric(db, message, kind="complaint")
    elif event_type in ("delivered", "email.delivered"):
        pass  # already sent
    else:
        logger.info("Unhandled ESP event type: %s", event_type)

    await db.commit()
    return {"ok": True, "matched": True, "message_id": str(message.id), "status": message.status}


def _parse_esp_payload(payload: dict[str, Any]) -> tuple[str, Optional[str], Optional[str], Optional[str]]:
    # Resend: {"type": "email.bounced", "data": {"email_id": "...", "to": ["a@b.com"], ...}}
    if "type" in payload and "data" in payload and isinstance(payload["data"], dict):
        data = payload["data"]
        esp_id = data.get("email_id") or data.get("id")
        to = data.get("to")
        email = None
        if isinstance(to, list) and to:
            email = to[0] if isinstance(to[0], str) else to[0].get("email")
        elif isinstance(to, str):
            email = to
        return str(payload["type"]), esp_id, email, data.get("reason") or data.get("bounce_type")

    # Generic
    return (
        str(payload.get("type") or "unknown"),
        payload.get("esp_message_id"),
        payload.get("email"),
        payload.get("reason"),
    )


async def _suppress_from_message(db: AsyncSession, message: Message, reason: str) -> None:
    from app.models.campaign import Campaign
    from app.models.lead import Lead

    email = (message.to_email or "").lower().strip()
    if not email:
        return
    lead_row = await db.execute(select(Lead).where(Lead.id == message.lead_id))
    lead = lead_row.scalar_one_or_none()
    if not lead:
        return
    camp_row = await db.execute(select(Campaign).where(Campaign.id == lead.campaign_id))
    campaign = camp_row.scalar_one_or_none()
    if not campaign:
        return
    existing = await db.execute(
        select(SuppressionList).where(
            SuppressionList.organization_id == campaign.organization_id,
            SuppressionList.contact_value == email,
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(
            SuppressionList(
                organization_id=campaign.organization_id,
                contact_value=email,
                reason=reason,
            )
        )


async def _record_abuse_metric(db: AsyncSession, message: Message, *, kind: str) -> None:
    """Look up the message's organization and record a bounce/complaint against
    its sending identity (auto-pauses sending if thresholds are crossed)."""
    from app.models.campaign import Campaign
    from app.models.lead import Lead
    from app.services.sending_identity_service import record_bounce_or_complaint

    lead_row = await db.execute(select(Lead).where(Lead.id == message.lead_id))
    lead = lead_row.scalar_one_or_none()
    if not lead:
        return
    camp_row = await db.execute(select(Campaign).where(Campaign.id == lead.campaign_id))
    campaign = camp_row.scalar_one_or_none()
    if not campaign:
        return
    await record_bounce_or_complaint(db, campaign.organization_id, kind=kind)


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Stripe billing webhooks (checkout.session.completed, subscription.*, invoice.payment_failed).
    Signature verified via STRIPE_WEBHOOK_SECRET.
    """
    from app.services.billing_service import BillingError, construct_webhook_event, handle_stripe_event

    payload = await request.body()
    sig = request.headers.get("stripe-signature") or request.headers.get("Stripe-Signature") or ""
    try:
        event = construct_webhook_event(payload, sig)
    except BillingError as exc:
        raise HTTPException(
            status_code=400 if exc.code == "INVALID_SIGNATURE" else 503,
            detail={"error": {"code": exc.code, "message": exc.message}},
        ) from exc

    try:
        result = await handle_stripe_event(db, event)
    except Exception as exc:
        logger.exception("stripe webhook handler failed")
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "WEBHOOK_HANDLER_ERROR", "message": str(exc)[:200]}},
        ) from exc
    return result


@router.post("/webhooks/inbound-email")
async def inbound_email_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Generic inbound reply webhook (Resend/Postmark-style or custom).

    Expected JSON (flexible):
      { "type": "email.received", "data": { "from": "...", "to": "...", "in_reply_to": "<esp-id>", "text": "..." } }
      or { "from": "...", "in_reply_to": "...", "text": "..." }

    Matches Message by esp_message_id == in_reply_to OR to_email == from (latest sent).
    Free path: no paid IMAP — ESP pushes webhook.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": {"code": "INVALID_JSON", "message": "Expected JSON"}})

    from app.models.lead import Lead

    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    from_email = (data.get("from") or data.get("from_email") or "").strip().lower()
    # strip "Name <email>"
    if "<" in from_email and ">" in from_email:
        from_email = from_email.split("<", 1)[1].split(">", 1)[0].strip().lower()
    in_reply_to = (data.get("in_reply_to") or data.get("inReplyTo") or data.get("references") or "").strip()
    text = (data.get("text") or data.get("body") or data.get("html") or "")[:2000]

    msg = None
    if in_reply_to:
        # try exact esp id
        clean = in_reply_to.strip("<>")
        result = await db.execute(select(Message).where(Message.esp_message_id == clean))
        msg = result.scalar_one_or_none()
        if msg is None:
            result = await db.execute(select(Message).where(Message.esp_message_id == in_reply_to))
            msg = result.scalar_one_or_none()

    if msg is None and from_email:
        result = await db.execute(
            select(Message)
            .where(Message.to_email == from_email, Message.status == "sent")
            .order_by(Message.sent_at.desc().nullslast())
            .limit(1)
        )
        msg = result.scalar_one_or_none()

    if msg is None:
        return {"ok": True, "matched": False}

    msg.status = "replied"
    lead_row = await db.execute(select(Lead).where(Lead.id == msg.lead_id))
    lead = lead_row.scalar_one_or_none()
    if lead and lead.stage in ("new", "contacted", "follow_up"):
        lead.stage = "replied"
    if text and msg.content and "--- inbound reply ---" not in (msg.content or ""):
        msg.content = (msg.content or "") + "\n\n--- inbound reply ---\n" + text
    await db.commit()
    logger.info("inbound reply matched message %s from %s", msg.id, from_email)
    return {"ok": True, "matched": True, "message_id": str(msg.id), "lead_id": str(msg.lead_id)}