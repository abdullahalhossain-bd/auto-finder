"""Organization member invites (Stage 2 polish)."""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.security import hash_password
from app.models.membership import Membership
from app.models.org_invite import OrgInvite
from app.models.user import User
from app.repositories.membership_repository import MembershipRepository
from app.services.audit_service import write_audit

logger = logging.getLogger(__name__)
router = APIRouter(tags=["invites"])


class InviteCreate(BaseModel):
    email: EmailStr
    role: str = Field("member", pattern="^(member|owner)$")


class InviteRead(BaseModel):
    id: UUID
    email: str
    role: str
    status: str
    expires_at: datetime

    model_config = {"from_attributes": True}


class InviteAccept(BaseModel):
    token: str
    password: Optional[str] = Field(None, min_length=8)
    # If user already exists, password not required — just login token path uses accept while authenticated optional


async def _require_owner(db: AsyncSession, current: CurrentUser) -> None:
    m = await MembershipRepository(db).get(current.organization_id, user_id=current.user_id)
    if m is None or m.role != "owner":
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "FORBIDDEN", "message": "Owner role required"}},
        )


@router.post("/organizations/me/invites", response_model=dict, status_code=201)
async def create_invite(
    body: InviteCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    await _require_owner(db, current)
    email = body.email.lower().strip()
    existing = (
        await db.execute(
            select(OrgInvite).where(
                OrgInvite.organization_id == current.organization_id,
                OrgInvite.email == email,
                OrgInvite.status == "pending",
            )
        )
    ).scalar_one_or_none()
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(days=7)

    if existing:
        existing.token_hash = token_hash
        existing.expires_at = expires
        existing.role = body.role if body.role in ("member", "owner") else "member"
        row = existing
    else:
        row = OrgInvite(
            organization_id=current.organization_id,
            email=email,
            role=body.role if body.role in ("member", "owner") else "member",
            token_hash=token_hash,
            invited_by=current.user_id,
            status="pending",
            expires_at=expires,
        )
        db.add(row)

    await write_audit(
        db,
        action="org.invite_created",
        organization_id=current.organization_id,
        user_id=current.user_id,
        meta={"email": email, "role": row.role},
    )
    await db.commit()
    await db.refresh(row)
    # Free path: log token (console). Production would email via ESP.
    logger.info("org invite token for %s: %s", email, token)
    return {
        "id": str(row.id),
        "email": row.email,
        "role": row.role,
        "status": row.status,
        "expires_at": row.expires_at.isoformat(),
        "invite_token_dev": token,  # only useful with console; strip in strict prod if desired
        "message": "Invite created. Token logged server-side (ESP_PROVIDER=console).",
    }


@router.get("/organizations/me/invites", response_model=list[InviteRead])
async def list_invites(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    await _require_owner(db, current)
    rows = (
        await db.execute(
            select(OrgInvite).where(OrgInvite.organization_id == current.organization_id)
        )
    ).scalars().all()
    return [InviteRead.model_validate(r) for r in rows]


@router.post("/invites/accept", response_model=dict)
async def accept_invite(
    body: InviteAccept,
    db: AsyncSession = Depends(get_db),
):
    """Accept invite: creates user if needed + membership."""
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    row = (
        await db.execute(select(OrgInvite).where(OrgInvite.token_hash == token_hash))
    ).scalar_one_or_none()
    if row is None or row.status != "pending":
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Invite invalid"}},
        )
    exp = row.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        row.status = "expired"
        await db.commit()
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "EXPIRED", "message": "Invite expired"}},
        )

    user = (
        await db.execute(select(User).where(User.email == row.email))
    ).scalar_one_or_none()
    if user is None:
        if not body.password:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": {
                        "code": "PASSWORD_REQUIRED",
                        "message": "New users must set a password when accepting",
                    }
                },
            )
        user = User(email=row.email, password_hash=hash_password(body.password))
        db.add(user)
        await db.flush()

    existing_m = (
        await db.execute(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.organization_id == row.organization_id,
            )
        )
    ).scalar_one_or_none()
    if existing_m is None:
        db.add(
            Membership(
                user_id=user.id,
                organization_id=row.organization_id,
                role=row.role,
            )
        )
    row.status = "accepted"
    row.accepted_at = datetime.now(timezone.utc)
    await write_audit(
        db,
        action="org.invite_accepted",
        organization_id=row.organization_id,
        user_id=user.id,
        meta={"email": row.email},
    )
    await db.commit()
    return {"ok": True, "organization_id": str(row.organization_id), "email": row.email}


@router.delete("/organizations/me/invites/{invite_id}", response_model=dict)
async def revoke_invite(
    invite_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    await _require_owner(db, current)
    row = await db.get(OrgInvite, invite_id)
    if row is None or row.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Not found"}})
    row.status = "revoked"
    await db.commit()
    return {"status": "revoked", "id": str(invite_id)}
