"""Sending identity verification + abuse pause (Section 18)."""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging_config import log_event
from app.models.sending_identity import SendingIdentity


class SendingIdentityError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


async def get_primary_identity(
    session: AsyncSession, organization_id: UUID
) -> Optional[SendingIdentity]:
    result = await session.execute(
        select(SendingIdentity)
        .where(SendingIdentity.organization_id == organization_id)
        .order_by(SendingIdentity.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def get_primary_identity_sync(
    session: Session, organization_id: UUID
) -> Optional[SendingIdentity]:
    return (
        session.execute(
            select(SendingIdentity)
            .where(SendingIdentity.organization_id == organization_id)
            .order_by(SendingIdentity.created_at.asc())
            .limit(1)
        )
        .scalars()
        .first()
    )


async def create_or_update_identity(
    session: AsyncSession,
    *,
    organization_id: UUID,
    from_name: str,
    from_address: str,
    verified_domain: str,
) -> SendingIdentity:
    existing = await get_primary_identity(session, organization_id)
    domain = verified_domain.strip().lower()
    addr = from_address.strip().lower()
    if "@" in addr and not domain:
        domain = addr.split("@", 1)[1]

    if existing:
        existing.from_name = from_name.strip() or existing.from_name
        existing.from_address = addr
        existing.verified_domain = domain
        # Changing identity resets verification (must re-check DNS)
        existing.spf_verified = False
        existing.dkim_verified = False
        await session.commit()
        await session.refresh(existing)
        return existing

    row = SendingIdentity(
        organization_id=organization_id,
        from_name=from_name.strip() or "Outreach",
        from_address=addr,
        verified_domain=domain,
        spf_verified=False,
        dkim_verified=False,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def assign_platform_subdomain(
    session: AsyncSession, organization_id: UUID, from_name: str = "Outreach"
) -> SendingIdentity:
    """Assign isolated subdomain of ESP_PLATFORM_SENDING_ROOT_DOMAIN."""
    settings = get_settings()
    root = (settings.ESP_PLATFORM_SENDING_ROOT_DOMAIN or "mail.localhost").strip().lower()
    short = str(organization_id).replace("-", "")[:8]
    domain = f"{short}.{root}"
    from_address = f"outreach@{domain}"
    return await create_or_update_identity(
        session,
        organization_id=organization_id,
        from_name=from_name,
        from_address=from_address,
        verified_domain=domain,
    )


async def mark_verified(
    session: AsyncSession,
    organization_id: UUID,
    *,
    spf: Optional[bool] = None,
    dkim: Optional[bool] = None,
    live_dns: bool = False,
    dkim_selector: Optional[str] = None,
) -> SendingIdentity:
    """
    Mark SPF/DKIM verified.
    If live_dns=True, query public DNS TXT (free resolver / dnspython) and set flags from result.
    """
    row = await get_primary_identity(session, organization_id)
    if row is None:
        raise SendingIdentityError("NOT_FOUND", "No sending identity configured")

    dns_meta = None
    if live_dns:
        from app.core.config import get_settings
        from app.services.dns_verify import verify_domain_dns

        settings = get_settings()
        selector = dkim_selector or getattr(settings, "DKIM_SELECTOR", None) or "default"
        dns_meta = verify_domain_dns(row.verified_domain, dkim_selector=selector)
        row.spf_verified = bool(dns_meta.get("spf_verified"))
        row.dkim_verified = bool(dns_meta.get("dkim_verified"))
    else:
        if spf is not None:
            row.spf_verified = bool(spf)
        if dkim is not None:
            row.dkim_verified = bool(dkim)

    await session.commit()
    await session.refresh(row)
    log_event(
        "sending_identity.verified",
        organization_id=str(organization_id),
        spf_verified=row.spf_verified,
        dkim_verified=row.dkim_verified,
        live_dns=live_dns,
        dns=dns_meta,
    )
    return row


def assert_can_send_sync(session: Session, organization_id: UUID) -> SendingIdentity:
    """
    Called inside send worker. Raises SendingIdentityError if blocked.
    """
    row = get_primary_identity_sync(session, organization_id)
    if row is None:
        raise SendingIdentityError(
            "SENDING_IDENTITY_REQUIRED",
            "Configure and verify a sending identity before sending.",
        )
    if row.sending_paused:
        raise SendingIdentityError(
            "SENDING_PAUSED",
            row.pause_reason
            or "Sending is paused due to bounce/complaint rates. Contact support.",
        )
    if not (row.spf_verified and row.dkim_verified):
        raise SendingIdentityError(
            "SENDING_IDENTITY_UNVERIFIED",
            "SPF and DKIM must both be verified before sending.",
        )
    return row


def record_send_sync(session: Session, identity: SendingIdentity) -> None:
    identity.sent_count = int(identity.sent_count or 0) + 1
    session.flush()


def record_bounce_or_complaint_sync(
    session: Session,
    organization_id: UUID,
    *,
    kind: str,
) -> Optional[SendingIdentity]:
    """
    Increment counters; auto-pause if thresholds crossed (CODING_STANDARDS #14).
    kind: 'bounce' | 'complaint'
    """
    settings = get_settings()
    row = get_primary_identity_sync(session, organization_id)
    if row is None:
        return None

    if kind == "complaint":
        row.complaint_count = int(row.complaint_count or 0) + 1
    else:
        row.bounce_count = int(row.bounce_count or 0) + 1

    sent = max(int(row.sent_count or 0), 1)
    bounce_rate = float(row.bounce_count) / float(sent)
    complaint_rate = float(row.complaint_count) / float(sent)
    bounce_th = float(getattr(settings, "ESP_BOUNCE_RATE_PAUSE_THRESHOLD", 0.05))
    complaint_th = float(getattr(settings, "ESP_COMPLAINT_RATE_PAUSE_THRESHOLD", 0.001))

    # Only evaluate after a minimum sample
    if sent >= 20:
        if bounce_rate >= bounce_th:
            row.sending_paused = True
            row.pause_reason = (
                f"Auto-paused: bounce rate {bounce_rate:.2%} >= threshold {bounce_th:.2%}"
            )
            log_event(
                "sending.auto_paused",
                organization_id=str(organization_id),
                reason="bounce_rate",
                bounce_rate=round(bounce_rate, 4),
                sent_count=sent,
            )
        elif complaint_rate >= complaint_th:
            row.sending_paused = True
            row.pause_reason = (
                f"Auto-paused: complaint rate {complaint_rate:.4%} >= threshold {complaint_th:.4%}"
            )
            log_event(
                "sending.auto_paused",
                organization_id=str(organization_id),
                reason="complaint_rate",
                complaint_rate=round(complaint_rate, 6),
                sent_count=sent,
            )

    session.flush()
    return row


async def record_bounce_or_complaint(
    session: AsyncSession,
    organization_id: UUID,
    *,
    kind: str,
) -> Optional[SendingIdentity]:
    """
    Async counterpart to record_bounce_or_complaint_sync, for use by webhook
    handlers that operate on an AsyncSession.
    Increment counters; auto-pause if thresholds crossed (CODING_STANDARDS #14).
    kind: 'bounce' | 'complaint'
    """
    settings = get_settings()
    row = await get_primary_identity(session, organization_id)
    if row is None:
        return None

    if kind == "complaint":
        row.complaint_count = int(row.complaint_count or 0) + 1
    else:
        row.bounce_count = int(row.bounce_count or 0) + 1

    sent = max(int(row.sent_count or 0), 1)
    bounce_rate = float(row.bounce_count) / float(sent)
    complaint_rate = float(row.complaint_count) / float(sent)
    bounce_th = float(getattr(settings, "ESP_BOUNCE_RATE_PAUSE_THRESHOLD", 0.05))
    complaint_th = float(getattr(settings, "ESP_COMPLAINT_RATE_PAUSE_THRESHOLD", 0.001))

    # Only evaluate after a minimum sample
    if sent >= 20:
        if bounce_rate >= bounce_th:
            row.sending_paused = True
            row.pause_reason = (
                f"Auto-paused: bounce rate {bounce_rate:.2%} >= threshold {bounce_th:.2%}"
            )
            log_event(
                "sending.auto_paused",
                organization_id=str(organization_id),
                reason="bounce_rate",
                bounce_rate=round(bounce_rate, 4),
                sent_count=sent,
            )
        elif complaint_rate >= complaint_th:
            row.sending_paused = True
            row.pause_reason = (
                f"Auto-paused: complaint rate {complaint_rate:.4%} >= threshold {complaint_th:.4%}"
            )
            log_event(
                "sending.auto_paused",
                organization_id=str(organization_id),
                reason="complaint_rate",
                complaint_rate=round(complaint_rate, 6),
                sent_count=sent,
            )

    await session.flush()
    return row


def dns_records_hint(domain: str) -> dict[str, Any]:
    """UI helper — records the org should publish (not live DNS lookup)."""
    settings = get_settings()
    root = (settings.ESP_PLATFORM_SENDING_ROOT_DOMAIN or "mail.yourplatform.com").strip()
    selector = getattr(settings, "DKIM_SELECTOR", None) or "default"
    return {
        "domain": domain,
        "spf": f"v=spf1 include:_spf.{root} ~all",
        "dkim": (
            f"Publish the DKIM TXT from your ESP at "
            f"{selector}._domainkey.{domain} (or the selector your ESP shows)."
        ),
        "dmarc": f"v=DMARC1; p=none; rua=mailto:dmarc@{domain}",
        "note": (
            "After publishing SPF + DKIM (and ideally DMARC), call "
            "POST /settings/sending-identity/verify with live_dns=true. "
            "Sending requires SPF and DKIM verified; DMARC improves deliverability."
        ),
    }


async def unpause_sending(
    session: AsyncSession,
    organization_id: UUID,
    *,
    require_verified: bool = True,
) -> SendingIdentity:
    """
    Owner action: clear auto-pause after fixing reputation / DNS.
    Does not reset bounce/complaint counters (audit trail).
    """
    row = await get_primary_identity(session, organization_id)
    if row is None:
        raise SendingIdentityError("NOT_FOUND", "No sending identity configured")
    if require_verified and not (row.spf_verified and row.dkim_verified):
        raise SendingIdentityError(
            "SENDING_IDENTITY_UNVERIFIED",
            "Verify SPF and DKIM before unpausing sends.",
        )
    row.sending_paused = False
    row.pause_reason = None
    await session.commit()
    await session.refresh(row)
    log_event(
        "sending.unpaused",
        organization_id=str(organization_id),
        sent_count=int(row.sent_count or 0),
        bounce_count=int(row.bounce_count or 0),
        complaint_count=int(row.complaint_count or 0),
    )
    return row
