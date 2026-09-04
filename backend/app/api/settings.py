"""Settings: sending identity (Section 18)."""

from __future__ import annotations

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.repositories.membership_repository import MembershipRepository
from app.services.audit_service import write_audit
from app.services.sending_identity_service import (
    SendingIdentityError,
    assign_platform_subdomain,
    create_or_update_identity,
    dns_records_hint,
    get_primary_identity,
    mark_verified,
    unpause_sending,
)


router = APIRouter(prefix="/settings", tags=["settings"])


class SendingIdentityUpsert(BaseModel):
    from_name: str = Field("Outreach", max_length=120)
    from_address: Optional[str] = Field(None, max_length=255)
    verified_domain: Optional[str] = Field(None, max_length=255)
    use_platform_subdomain: bool = False


class SendingIdentityVerify(BaseModel):
    """Mark verified manually, or set live_dns=true to query public DNS TXT (free)."""

    spf_verified: bool = True
    dkim_verified: bool = True
    live_dns: bool = False
    dkim_selector: Optional[str] = None


class SendingIdentityRead(BaseModel):
    id: str
    from_name: str
    from_address: str
    verified_domain: str
    spf_verified: bool
    dkim_verified: bool
    sending_paused: bool
    pause_reason: Optional[str] = None
    bounce_count: int
    complaint_count: int
    sent_count: int
    dns_hint: Optional[dict] = None
    can_send: bool


async def _require_owner(
    db: AsyncSession,
    current: CurrentUser,
) -> None:
    m = await MembershipRepository(db).get(
        current.organization_id,
        user_id=current.user_id,
    )

    if m is None or m.role != "owner":
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Owner role required",
                }
            },
        )


@router.get(
    "/sending-identity",
    response_model=SendingIdentityRead | dict,
)
async def get_sending_identity(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    row = await get_primary_identity(
        db,
        current.organization_id,
    )

    if row is None:
        return {
            "configured": False,
            "can_send": False,
            "message": "No sending identity yet",
        }

    return SendingIdentityRead(
        id=str(row.id),
        from_name=row.from_name,
        from_address=row.from_address,
        verified_domain=row.verified_domain,
        spf_verified=row.spf_verified,
        dkim_verified=row.dkim_verified,
        sending_paused=row.sending_paused,
        pause_reason=row.pause_reason,
        bounce_count=row.bounce_count,
        complaint_count=row.complaint_count,
        sent_count=row.sent_count,
        dns_hint=dns_records_hint(row.verified_domain),
        can_send=bool(
            row.spf_verified
            and row.dkim_verified
            and not row.sending_paused
        ),
    )


@router.post(
    "/sending-identity",
    response_model=SendingIdentityRead,
)
async def upsert_sending_identity(
    body: SendingIdentityUpsert,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    await _require_owner(db, current)

    if body.use_platform_subdomain:
        row = await assign_platform_subdomain(
            db,
            current.organization_id,
            from_name=body.from_name,
        )
    else:
        if not body.from_address or not body.verified_domain:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": (
                            "from_address and verified_domain required "
                            "unless use_platform_subdomain=true"
                        ),
                    }
                },
            )

        row = await create_or_update_identity(
            db,
            organization_id=current.organization_id,
            from_name=body.from_name,
            from_address=body.from_address,
            verified_domain=body.verified_domain,
        )

    return SendingIdentityRead(
        id=str(row.id),
        from_name=row.from_name,
        from_address=row.from_address,
        verified_domain=row.verified_domain,
        spf_verified=row.spf_verified,
        dkim_verified=row.dkim_verified,
        sending_paused=row.sending_paused,
        pause_reason=row.pause_reason,
        bounce_count=row.bounce_count,
        complaint_count=row.complaint_count,
        sent_count=row.sent_count,
        dns_hint=dns_records_hint(row.verified_domain),
        can_send=bool(
            row.spf_verified
            and row.dkim_verified
            and not row.sending_paused
        ),
    )


@router.post(
    "/sending-identity/verify",
    response_model=SendingIdentityRead,
)
async def verify_sending_identity(
    body: SendingIdentityVerify,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """Mark SPF/DKIM verified (after DNS/ESP confirmation). Owner only."""

    await _require_owner(db, current)

    try:
        row = await mark_verified(
            db,
            current.organization_id,
            spf=body.spf_verified,
            dkim=body.dkim_verified,
            live_dns=body.live_dns,
            dkim_selector=body.dkim_selector,
        )

        await write_audit(
            db,
            action="sending_identity.verify",
            organization_id=current.organization_id,
            user_id=current.user_id,
            resource_type="sending_identity",
            resource_id=str(row.id),
            meta={
                "spf": body.spf_verified,
                "dkim": body.dkim_verified,
            },
        )

        await db.commit()

    except SendingIdentityError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                }
            },
        ) from exc

    return SendingIdentityRead(
        id=str(row.id),
        from_name=row.from_name,
        from_address=row.from_address,
        verified_domain=row.verified_domain,
        spf_verified=row.spf_verified,
        dkim_verified=row.dkim_verified,
        sending_paused=row.sending_paused,
        pause_reason=row.pause_reason,
        bounce_count=row.bounce_count,
        complaint_count=row.complaint_count,
        sent_count=row.sent_count,
        dns_hint=dns_records_hint(row.verified_domain),
        can_send=bool(
            row.spf_verified
            and row.dkim_verified
            and not row.sending_paused
        ),
    )


# ---------------------------------------------------------------------------
# API credentials (encrypted at rest)
# ---------------------------------------------------------------------------

ALLOWED_PROVIDERS = {
    "google_places",
    "groq",
    "resend",
    "smtp",
}


class ApiCredentialCreate(BaseModel):
    provider: str = Field(
        ...,
        description="google_places | groq | resend | smtp",
    )
    value: str = Field(..., min_length=4)
    label: Optional[str] = None


class ApiCredentialRead(BaseModel):
    id: str
    provider: str
    label: Optional[str] = None
    last4: Optional[str] = None
    created_at: Optional[str] = None


@router.get(
    "/api-credentials",
    response_model=list[ApiCredentialRead],
)
async def list_api_credentials(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.models.api_credential import ApiCredential

    rows = (
        await db.execute(
            select(ApiCredential).where(
                ApiCredential.organization_id
                == current.organization_id
            )
        )
    ).scalars().all()

    return [
        ApiCredentialRead(
            id=str(r.id),
            provider=r.provider,
            label=r.label,
            last4=r.last4,
            created_at=(
                r.created_at.isoformat()
                if r.created_at
                else None
            ),
        )
        for r in rows
    ]


@router.post(
    "/api-credentials",
    response_model=ApiCredentialRead,
    status_code=201,
)
async def create_api_credential(
    body: ApiCredentialCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    await _require_owner(db, current)

    from sqlalchemy import select
    from app.core.crypto import encrypt_secret
    from app.models.api_credential import ApiCredential

    provider = body.provider.strip().lower()

    if provider not in ALLOWED_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "INVALID_PROVIDER",
                    "message": (
                        f"provider must be one of "
                        f"{sorted(ALLOWED_PROVIDERS)}"
                    ),
                }
            },
        )

    existing = (
        await db.execute(
            select(ApiCredential).where(
                ApiCredential.organization_id
                == current.organization_id,
                ApiCredential.provider == provider,
            )
        )
    ).scalar_one_or_none()

    last4 = body.value[-4:]
    enc = encrypt_secret(body.value)

    if existing:
        existing.encrypted_value = enc
        existing.last4 = last4
        existing.label = body.label

        await db.commit()
        await db.refresh(existing)

        row = existing

    else:
        row = ApiCredential(
            organization_id=current.organization_id,
            provider=provider,
            encrypted_value=enc,
            label=body.label,
            last4=last4,
        )

        db.add(row)

        await db.commit()
        await db.refresh(row)

    await write_audit(
        db,
        action="credential.upsert",
        organization_id=current.organization_id,
        user_id=current.user_id,
        resource_type="api_credential",
        resource_id=str(row.id),
        meta={"provider": row.provider},
    )

    await db.commit()

    return ApiCredentialRead(
        id=str(row.id),
        provider=row.provider,
        label=row.label,
        last4=row.last4,
        created_at=(
            row.created_at.isoformat()
            if row.created_at
            else None
        ),
    )


@router.delete(
    "/api-credentials/{credential_id}",
    status_code=200,
)
async def delete_api_credential(
    credential_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    await _require_owner(db, current)

    from app.models.api_credential import ApiCredential

    row = await db.get(
        ApiCredential,
        credential_id,
    )

    if (
        row is None
        or row.organization_id != current.organization_id
    ):
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Credential not found",
                }
            },
        )

    await write_audit(
        db,
        action="credential.delete",
        organization_id=current.organization_id,
        user_id=current.user_id,
        resource_type="api_credential",
        resource_id=str(credential_id),
    )

    await db.delete(row)
    await db.commit()

    return {
        "status": "deleted",
        "id": str(credential_id),
    }


@router.post(
    "/sending-identity/unpause",
    response_model=SendingIdentityRead | dict,
)
async def unpause_sending_identity(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """Owner: clear sending_paused after resolving bounce/complaint issues."""
    await _require_owner(db, current)
    try:
        row = await unpause_sending(db, current.organization_id)
    except SendingIdentityError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": exc.code, "message": exc.message}},
        ) from exc

    await write_audit(
        db,
        action="sending_identity.unpause",
        organization_id=current.organization_id,
        user_id=current.user_id,
        resource_type="sending_identity",
        resource_id=str(row.id),
    )
    await db.commit()

    return SendingIdentityRead(
        id=str(row.id),
        from_name=row.from_name,
        from_address=row.from_address,
        verified_domain=row.verified_domain,
        spf_verified=row.spf_verified,
        dkim_verified=row.dkim_verified,
        sending_paused=row.sending_paused,
        pause_reason=row.pause_reason,
        bounce_count=int(row.bounce_count or 0),
        complaint_count=int(row.complaint_count or 0),
        sent_count=int(row.sent_count or 0),
        dns_hint=dns_records_hint(row.verified_domain),
        can_send=bool(
            row.spf_verified
            and row.dkim_verified
            and not row.sending_paused
        ),
    )
