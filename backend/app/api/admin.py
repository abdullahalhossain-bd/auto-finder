"""
Platform Admin API — superuser only (PLATFORM_ADMIN_EMAILS).

GET  /admin/me              — am I platform admin?
GET  /admin/overview        — platform KPIs
GET  /admin/organizations   — list orgs
GET  /admin/organizations/{id}
PATCH /admin/organizations/{id}  — plan / soft-delete / restore
GET  /admin/users
GET  /admin/audit-logs
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_platform_admin, _admin_emails
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.membership import Membership
from app.models.message import Message
from app.models.organization import Organization
from app.models.subscription import Subscription
from app.models.user import User
from app.models.audit_log import AuditLog
from app.services.audit_service import write_audit
from app.services.plan_limits import get_plan_caps, normalize_plan

router = APIRouter(prefix="/admin", tags=["admin"])


class OrgPatch(BaseModel):
    plan: Optional[str] = Field(None, description="trial | starter | pro")
    name: Optional[str] = None
    soft_delete: Optional[bool] = None  # true = set deleted_at, false = clear


class OrgOut(BaseModel):
    id: str
    name: str
    plan: str
    deleted_at: Optional[str] = None
    created_at: Optional[str] = None
    members: int = 0
    campaigns: int = 0
    leads: int = 0
    subscription_status: Optional[str] = None


@router.get("/me")
async def admin_me(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Non-throwing check for UI nav visibility."""
    result = await db.execute(select(User).where(User.id == current.user_id))
    user = result.scalar_one_or_none()
    emails = _admin_emails()
    is_admin = bool(user and emails and (user.email or "").lower() in emails)
    return {
        "is_platform_admin": is_admin,
        "email": user.email if user else None,
        "admin_configured": bool(emails),
    }


@router.get("/overview")
async def admin_overview(
    _: CurrentUser = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.demo.adapters import is_demo_mode

    if is_demo_mode():
        # DEMO_MODE: the buyer-facing admin panel should reflect a mature,
        # multi-tenant platform — not the handful of rows that actually
        # exist in a freshly-seeded demo database. These figures are the
        # same labeled simulated numbers used by /demo/admin/overview.
        real_orgs = (
            await db.execute(select(func.count()).select_from(Organization))
        ).scalar_one()
        return {
            "organizations": 128,
            "organizations_active": 121,
            "organizations_deleted": 7,
            "users": 214,
            "campaigns": 890,
            "leads": 18420,
            "messages_sent": 6230,
            "plans": {"trial": 160, "starter": 38, "pro": 16},
            "demo_mode": True,
            "note": (
                "DEMO DATA — simulated platform scale for buyer walkthrough. "
                f"This environment currently has {real_orgs} real organization(s)."
            ),
        }

    orgs = (await db.execute(select(func.count()).select_from(Organization))).scalar_one()
    users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    campaigns = (await db.execute(select(func.count()).select_from(Campaign))).scalar_one()
    leads = (await db.execute(select(func.count()).select_from(Lead))).scalar_one()
    messages_sent = (
        await db.execute(
            select(func.count()).select_from(Message).where(Message.status == "sent")
        )
    ).scalar_one()
    deleted_orgs = (
        await db.execute(
            select(func.count())
            .select_from(Organization)
            .where(Organization.deleted_at.is_not(None))
        )
    ).scalar_one()

    # plan breakdown
    plan_rows = (
        await db.execute(
            select(Organization.plan, func.count())
            .where(Organization.deleted_at.is_(None))
            .group_by(Organization.plan)
        )
    ).all()
    plans = {str(p): int(c) for p, c in plan_rows}

    return {
        "organizations": int(orgs),
        "organizations_active": int(orgs) - int(deleted_orgs),
        "organizations_deleted": int(deleted_orgs),
        "users": int(users),
        "campaigns": int(campaigns),
        "leads": int(leads),
        "messages_sent": int(messages_sent),
        "plans": plans,
    }


@router.get("/organizations")
async def list_organizations(
    q: Optional[str] = Query(None),
    plan: Optional[str] = Query(None),
    include_deleted: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: CurrentUser = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    base = select(Organization)
    if not include_deleted:
        base = base.where(Organization.deleted_at.is_(None))
    if plan:
        base = base.where(Organization.plan == plan.lower())
    if q:
        like = f"%{q.strip()}%"
        base = base.where(Organization.name.ilike(like))

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    rows = (
        await db.execute(
            base.order_by(Organization.created_at.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()

    items: list[dict[str, Any]] = []
    for org in rows:
        members = (
            await db.execute(
                select(func.count())
                .select_from(Membership)
                .where(Membership.organization_id == org.id)
            )
        ).scalar_one()
        camps = (
            await db.execute(
                select(func.count())
                .select_from(Campaign)
                .where(Campaign.organization_id == org.id)
            )
        ).scalar_one()
        leads_c = (
            await db.execute(
                select(func.count())
                .select_from(Lead)
                .join(Campaign, Lead.campaign_id == Campaign.id)
                .where(Campaign.organization_id == org.id)
            )
        ).scalar_one()
        sub = (
            await db.execute(
                select(Subscription).where(Subscription.organization_id == org.id)
            )
        ).scalar_one_or_none()
        items.append(
            {
                "id": str(org.id),
                "name": org.name,
                "plan": org.plan,
                "deleted_at": org.deleted_at.isoformat() if org.deleted_at else None,
                "created_at": org.created_at.isoformat() if org.created_at else None,
                "members": int(members),
                "campaigns": int(camps),
                "leads": int(leads_c),
                "subscription_status": sub.status if sub else None,
                "caps": get_plan_caps(org.plan),
            }
        )
    return {"items": items, "total": int(total)}


@router.get("/organizations/{org_id}")
async def get_organization(
    org_id: UUID,
    _: CurrentUser = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Org not found"}})

    mems = (
        await db.execute(
            select(Membership, User)
            .join(User, User.id == Membership.user_id)
            .where(Membership.organization_id == org_id)
        )
    ).all()
    members = [
        {
            "user_id": str(u.id),
            "email": u.email,
            "role": m.role,
        }
        for m, u in mems
    ]
    sub = (
        await db.execute(select(Subscription).where(Subscription.organization_id == org_id))
    ).scalar_one_or_none()

    return {
        "id": str(org.id),
        "name": org.name,
        "plan": org.plan,
        "deleted_at": org.deleted_at.isoformat() if org.deleted_at else None,
        "created_at": org.created_at.isoformat() if org.created_at else None,
        "members": members,
        "subscription": {
            "plan_id": sub.plan_id,
            "status": sub.status,
            "stripe_customer_id": sub.stripe_customer_id,
            "trial_end": sub.trial_end.isoformat() if sub and sub.trial_end else None,
        }
        if sub
        else None,
        "caps": get_plan_caps(org.plan),
    }


@router.patch("/organizations/{org_id}")
async def patch_organization(
    org_id: UUID,
    body: OrgPatch,
    current: CurrentUser = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Org not found"}})

    changes: dict[str, Any] = {}
    if body.name is not None and body.name.strip():
        org.name = body.name.strip()
        changes["name"] = org.name

    if body.plan is not None:
        plan = body.plan.lower().strip()
        if plan == "free":
            plan = "trial"
        if plan not in ("trial", "starter", "pro"):
            raise HTTPException(
                400,
                detail={
                    "error": {
                        "code": "INVALID_PLAN",
                        "message": "plan must be trial, starter, or pro",
                    }
                },
            )
        org.plan = plan
        changes["plan"] = plan
        # Keep subscription row in sync for limits
        sub = (
            await db.execute(select(Subscription).where(Subscription.organization_id == org_id))
        ).scalar_one_or_none()
        if sub:
            sub.plan_id = plan
            if plan in ("starter", "pro") and sub.status in ("trialing", "cancelled"):
                sub.status = "active"
            if plan == "trial" and sub.status == "active":
                sub.status = "trialing"

    if body.soft_delete is True:
        org.deleted_at = datetime.now(timezone.utc)
        changes["deleted_at"] = org.deleted_at.isoformat()
    elif body.soft_delete is False:
        org.deleted_at = None
        changes["deleted_at"] = None

    await write_audit(
        db,
        action="admin.org.patch",
        organization_id=org_id,
        user_id=current.user_id,
        resource_type="organization",
        resource_id=str(org_id),
        meta=changes,
    )
    await db.commit()
    await db.refresh(org)

    return {
        "id": str(org.id),
        "name": org.name,
        "plan": org.plan,
        "deleted_at": org.deleted_at.isoformat() if org.deleted_at else None,
        "changes": changes,
    }


@router.get("/users")
async def list_users(
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: CurrentUser = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    base = select(User)
    if q:
        base = base.where(User.email.ilike(f"%{q.strip()}%"))
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            base.order_by(User.created_at.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()

    admin_set = _admin_emails()
    items = []
    for u in rows:
        mem_count = (
            await db.execute(
                select(func.count())
                .select_from(Membership)
                .where(Membership.user_id == u.id)
            )
        ).scalar_one()
        items.append(
            {
                "id": str(u.id),
                "email": u.email,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "memberships": int(mem_count),
                "is_platform_admin": (u.email or "").lower() in admin_set,
            }
        )
    return {"items": items, "total": int(total)}


@router.get("/audit-logs")
async def list_audit_logs(
    organization_id: Optional[UUID] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: CurrentUser = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    base = select(AuditLog)
    if organization_id:
        base = base.where(AuditLog.organization_id == organization_id)
    if action:
        base = base.where(AuditLog.action.ilike(f"%{action}%"))
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            base.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": str(r.id),
                "organization_id": str(r.organization_id) if r.organization_id else None,
                "user_id": str(r.user_id) if r.user_id else None,
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "meta": r.meta,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "total": int(total),
    }
