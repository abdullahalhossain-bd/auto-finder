"""
Billing API — Section 17.

POST /billing/subscribe  (owner) → Stripe Checkout URL
GET  /billing/subscription (member) → current plan/status/caps
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.repositories.membership_repository import MembershipRepository
from app.services.billing_service import (
    BillingError,
    create_billing_portal_session,
    create_checkout_session,
    ensure_trial_subscription,
    get_subscription,
)
from app.services.plan_limits import get_plan_caps

router = APIRouter(prefix="/billing", tags=["billing"])


class SubscribeRequest(BaseModel):
    plan: str = Field(..., description="starter | pro")
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class SubscribeResponse(BaseModel):
    checkout_url: str
    session_id: str
    plan: str


class SubscriptionResponse(BaseModel):
    plan_id: str
    status: str
    stripe_customer_id: Optional[str] = None
    current_period_end: Optional[str] = None
    trial_end: Optional[str] = None
    caps: dict


async def _require_owner(
    db: AsyncSession, current: CurrentUser
) -> None:
    repo = MembershipRepository(db)
    m = await repo.get(current.organization_id, user_id=current.user_id)
    if m is None or m.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Only organization owners can manage billing",
                }
            },
        )


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(
    body: SubscribeRequest,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    await _require_owner(db, current)
    try:
        result = await create_checkout_session(
            db,
            organization_id=current.organization_id,
            user_id=current.user_id,
            plan=body.plan,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
    except BillingError as exc:
        code = 503 if exc.code in ("STRIPE_NOT_CONFIGURED", "DEMO_MODE") else 400
        if exc.code in ("ORG_NOT_FOUND", "USER_NOT_FOUND"):
            code = 404
        raise HTTPException(
            status_code=code,
            detail={"error": {"code": exc.code, "message": exc.message}},
        ) from exc
    return SubscribeResponse(**result)


@router.get("/subscription", response_model=SubscriptionResponse)
async def read_subscription(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    sub = await get_subscription(db, current.organization_id)
    if sub is None:
        sub = await ensure_trial_subscription(db, current.organization_id)
        await db.commit()

    def _iso(dt):
        return dt.isoformat() if dt else None

    return SubscriptionResponse(
        plan_id=sub.plan_id,
        status=sub.status,
        stripe_customer_id=sub.stripe_customer_id,
        current_period_end=_iso(sub.current_period_end),
        trial_end=_iso(sub.trial_end),
        caps=get_plan_caps(sub.plan_id),
    )



class PortalRequest(BaseModel):
    return_url: Optional[str] = None


class PortalResponse(BaseModel):
    portal_url: str


@router.post("/portal", response_model=PortalResponse)
async def billing_portal(
    body: PortalRequest = PortalRequest(),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """Owner-only Stripe Customer Portal (update card, cancel, change plan)."""
    await _require_owner(db, current)
    try:
        result = await create_billing_portal_session(
            db,
            organization_id=current.organization_id,
            return_url=body.return_url,
        )
    except BillingError as exc:
        code = 503 if exc.code in ("STRIPE_NOT_CONFIGURED", "DEMO_MODE") else 400
        if exc.code == "NO_CUSTOMER":
            code = 400
        raise HTTPException(
            status_code=code,
            detail={"error": {"code": exc.code, "message": exc.message}},
        ) from exc
    return PortalResponse(**result)
