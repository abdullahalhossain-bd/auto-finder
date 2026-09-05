"""
Outreach / send pipeline.

Non-negotiable rules:
1. Refuse unless message.status == "approved"
2. Re-check suppression list at send time
3. Mandatory unsubscribe link (inject if missing)
4. Enforce daily/weekly per-org caps
5. Idempotent — row-lock the message before sending so concurrent workers
   cannot both observe the same approved unsent message
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.business import Business
from app.models.campaign import Campaign
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.message import Message
from app.models.suppression import SuppressionList
from app.services.esp_client import ensure_unsubscribe_link, get_esp_client

logger = logging.getLogger(__name__)


class SendBlockedError(Exception):
    """Raised when a safety check blocks the send."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _public_base_url() -> str:
    settings = get_settings()
    url = getattr(settings, "PUBLIC_APP_URL", "") or ""
    if url:
        return url.rstrip("/")
    origins = settings.allowed_origins_list
    if origins:
        return origins[0].rstrip("/")
    return "http://localhost:8000"


def build_unsubscribe_url(token: str) -> str:
    return f"{_public_base_url()}/api/v1/unsubscribe?token={token}"


def resolve_recipient_email(session: Session, message: Message, lead: Lead) -> tuple[str, Optional[UUID]]:
    if message.contact_id:
        contact = session.get(Contact, message.contact_id)
        if contact and contact.type == "email" and contact.value:
            return contact.value.lower().strip(), contact.id

    business = lead.business
    if business is not None:
        contacts = session.execute(
            select(Contact).where(Contact.business_id == business.id, Contact.type == "email")
        ).scalars().all()
        if contacts:
            c = contacts[0]
            return c.value.lower().strip(), c.id

    raise SendBlockedError("NO_RECIPIENT", "No email contact found for this lead/business. Attach a contact_id or add an email contact.")


def _is_suppressed(session: Session, organization_id: UUID, email: str) -> bool:
    row = session.execute(
        select(SuppressionList.id).where(
            SuppressionList.organization_id == organization_id,
            SuppressionList.contact_value == email.lower().strip(),
        )
    ).scalar_one_or_none()
    return row is not None


def _count_sends_since(session: Session, organization_id: UUID, since: datetime) -> int:
    q = (
        select(func.count())
        .select_from(Message)
        .join(Lead, Message.lead_id == Lead.id)
        .join(Campaign, Lead.campaign_id == Campaign.id)
        .where(
            Campaign.organization_id == organization_id,
            Message.status == "sent",
            Message.sent_at.is_not(None),
            Message.sent_at >= since,
        )
    )
    return int(session.execute(q).scalar_one() or 0)


def _check_volume_caps(session: Session, organization_id: UUID) -> None:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - __import__("datetime").timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    daily = _count_sends_since(session, organization_id, day_start)
    if daily >= settings.ESP_DAILY_SEND_CAP_PER_ORG:
        raise SendBlockedError("DAILY_CAP", f"Daily send cap ({settings.ESP_DAILY_SEND_CAP_PER_ORG}) reached for this organization")
    weekly = _count_sends_since(session, organization_id, week_start)
    if weekly >= settings.ESP_WEEKLY_SEND_CAP_PER_ORG:
        raise SendBlockedError("WEEKLY_CAP", f"Weekly send cap ({settings.ESP_WEEKLY_SEND_CAP_PER_ORG}) reached for this organization")


def _default_from_address(organization_id: UUID) -> tuple[str, str]:
    settings = get_settings()
    domain = settings.ESP_PLATFORM_SENDING_ROOT_DOMAIN or "mail.localhost"
    short = str(organization_id).replace("-", "")[:8]
    from_email = f"outreach@{short}.{domain}" if domain != "mail.localhost" else f"noreply@{domain}"
    if getattr(settings, "ESP_PROVIDER", "console") in ("console", "smtp"):
        from_email = getattr(settings, "ESP_FROM_EMAIL", None) or "noreply@localhost"
    from_name = getattr(settings, "ESP_FROM_NAME", None) or "Outreach"
    return from_name, from_email


def send_approved_message(session: Session, message_id: UUID) -> Message:
    """Authoritative send path. Re-validates every safety rule inside this function."""
    # Critical idempotency hardening: serialize concurrent workers on the
    # exact Message row. The lock remains held until commit, so a second
    # worker cannot send the same approved message while the first is in flight.
    message = session.execute(
        select(Message)
        .where(Message.id == message_id)
        .with_for_update()
        .options(
            selectinload(Message.lead).selectinload(Lead.business).selectinload(Business.contacts),
            selectinload(Message.lead).selectinload(Lead.campaign),
        )
    ).scalar_one_or_none()

    if message is None:
        raise SendBlockedError("NOT_FOUND", f"Message {message_id} not found")
    if message.status != "approved":
        raise SendBlockedError("NOT_APPROVED", f"Refusing to send: status is '{message.status}', expected 'approved'")
    if message.sent_at is not None or message.status == "sent":
        logger.info("Message %s already sent — idempotent no-op", message_id)
        return message

    lead = message.lead
    if lead is None:
        raise SendBlockedError("NO_LEAD", "Message has no associated lead")
    campaign = lead.campaign
    if campaign is None:
        raise SendBlockedError("NO_CAMPAIGN", "Lead has no campaign")
    organization_id = campaign.organization_id

    from app.services.sending_identity_service import SendingIdentityError, assert_can_send_sync, record_send_sync
    from app.services.plan_limits import PlanLimitExceeded, assert_can_send_outbound_sync
    try:
        assert_can_send_outbound_sync(session, organization_id)
    except PlanLimitExceeded as exc:
        raise SendBlockedError(exc.code, exc.message) from exc
    try:
        identity = assert_can_send_sync(session, organization_id)
    except SendingIdentityError as exc:
        raise SendBlockedError(exc.code, exc.message) from exc

    to_email, contact_id = resolve_recipient_email(session, message, lead)
    if contact_id and not message.contact_id:
        message.contact_id = contact_id
    if _is_suppressed(session, organization_id, to_email):
        raise SendBlockedError("SUPPRESSED_CONTACT", f"Contact {to_email} is on the organization suppression list")

    _check_volume_caps(session, organization_id)

    if not message.unsubscribe_token:
        message.unsubscribe_token = secrets.token_urlsafe(32)
    unsub_url = build_unsubscribe_url(message.unsubscribe_token)
    body = ensure_unsubscribe_link(message.content, unsub_url)
    subject = message.subject or _default_subject(lead)
    from_name, from_email = identity.from_name, identity.from_address
    html_body = _text_to_simple_html(body)
    text_body = body
    headers = {"List-Unsubscribe": f"<{unsub_url}>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"}

    client = get_esp_client()
    result = client.send(to_email=to_email, from_email=from_email, from_name=from_name, subject=subject, html_body=html_body, text_body=text_body, headers=headers)
    if not result.success:
        message.last_send_error = (result.error or "unknown ESP error")[:1000]
        session.commit()
        raise SendBlockedError("ESP_FAILED", result.error or "ESP send failed")

    now = datetime.now(timezone.utc)
    message.status = "sent"
    message.sent_at = now
    message.content = body
    message.esp_message_id = result.provider_message_id
    message.esp_provider = result.provider
    message.to_email = to_email
    if not message.idempotency_key:
        message.idempotency_key = f"send-{message.id}"
    message.last_send_error = None
    if lead.stage in ("new", "disqualified"):
        lead.stage = "contacted"

    record_send_sync(session, identity)
    from app.services.usage_service import increment_usage_sync
    increment_usage_sync(session, organization_id, "messages_sent_count")
    session.commit()
    session.refresh(message)
    logger.info("Message %s sent via %s to %s (esp_id=%s)", message.id, result.provider, to_email, result.provider_message_id)
    return message


def _default_subject(lead: Lead) -> str:
    name = lead.business.name if lead.business and lead.business.name else ""
    return f"Quick idea for {name}" if name else "Quick idea for your business"


def _text_to_simple_html(text: str) -> str:
    import html as html_mod
    import re
    escaped = html_mod.escape(text)
    escaped = re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', escaped)
    return "<html><body><pre style='font-family:sans-serif;white-space:pre-wrap'>" + escaped + "</pre></body></html>"