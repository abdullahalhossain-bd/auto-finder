"""
Demo-mode APIs — interactive buyer demo without external services.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.demo.adapters import (
    MockBillingAdapter,
    MockDiscoveryAdapter,
    MockLLMAdapter,
    is_demo_mode,
    start_demo_generation_job,
    tick_demo_generation_job,
)
from app.demo.fixtures import DEMO_ACCOUNTS, demo_customer_reply, filter_demo_businesses
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.user import User
from app.services.billing_service import ensure_trial_subscription

router = APIRouter(prefix="/demo", tags=["demo"])


def _require_demo():
    if not is_demo_mode():
        raise HTTPException(404, detail={"error": {"code": "NOT_DEMO", "message": "Demo endpoints disabled"}})


class DemoLoginBody(BaseModel):
    account: str = Field(..., description="demo.user | demo.pro | demo.admin")


class DemoGenerateBody(BaseModel):
    industry: str = "Restaurant"
    city: str = "Dhaka"
    limit: int = Field(40, ge=1, le=40)


class DemoMessageBody(BaseModel):
    business_name: str
    category: Optional[str] = "Restaurant"
    city: Optional[str] = "Dhaka"
    review_count: Optional[int] = 200
    website_url: Optional[str] = None
    service: Optional[str] = "websites and online booking"


class DemoReplyBody(BaseModel):
    intent: str = Field("positive", pattern="^(positive|later|unsubscribe)$")


class DemoPlanBody(BaseModel):
    plan: str = Field(..., pattern="^(trial|free|starter|pro)$")


@router.get("/status")
async def demo_status():
    s = get_settings()
    return {
        "demo_mode": bool(getattr(s, "DEMO_MODE", False)),
        "label": "DEMO MODE" if is_demo_mode() else "LIVE",
        "accounts": [
            {"id": k, "email": v["email"], "label": v["label"]}
            for k, v in DEMO_ACCOUNTS.items()
        ]
        if is_demo_mode()
        else [],
        "note": "No Google/Facebook/Stripe/AI external calls when demo_mode=true",
    }


@router.post("/login")
async def demo_login(body: DemoLoginBody, db: AsyncSession = Depends(get_db)):
    """One-click buyer accounts. Ensures user+org exist in local DB."""
    _require_demo()
    key = body.account.strip().lower()
    if key not in DEMO_ACCOUNTS:
        raise HTTPException(400, detail={"error": {"code": "UNKNOWN_ACCOUNT", "message": "Use demo.user, demo.pro, or demo.admin"}})
    acc = DEMO_ACCOUNTS[key]
    email = acc["email"]

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=email, password_hash=hash_password(acc["password"]))
        db.add(user)
        await db.flush()
        org = Organization(name=acc["org_name"], plan=acc["plan"] if acc["plan"] != "free" else "trial")
        db.add(org)
        await db.flush()
        db.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
        await ensure_trial_subscription(db, org.id)
        if acc["plan"] in ("starter", "pro"):
            org.plan = acc["plan"]
        await db.commit()
        await db.refresh(user)
        org_id = org.id
    else:
        mem = (
            await db.execute(select(Membership).where(Membership.user_id == user.id))
        ).scalars().first()
        if mem is None:
            raise HTTPException(500, detail={"error": {"code": "NO_MEMBERSHIP", "message": "Demo user missing org"}})
        org_id = mem.organization_id
        # ensure password matches documented demo password
        if not verify_password(acc["password"], user.password_hash):
            user.password_hash = hash_password(acc["password"])
            await db.commit()

    access = create_access_token(user_id=user.id, organization_id=org_id)
    refresh = create_refresh_token(user_id=user.id)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "account": key,
        "email": email,
        "label": acc["label"],
        "is_platform_admin": acc["is_platform_admin"],
        "demo_mode": True,
        "message": "Signed in with demo account — Demo Data only",
    }


@router.post("/generate/start")
async def demo_generate_start(body: DemoGenerateBody, _: CurrentUser = Depends(get_current_user)):
    _require_demo()
    job_id = start_demo_generation_job(
        industry=body.industry, city=body.city, limit=body.limit
    )
    return {"job_id": job_id, "demo_mode": True, "status": "running"}


@router.get("/generate/{job_id}")
async def demo_generate_poll(job_id: str, _: CurrentUser = Depends(get_current_user)):
    _require_demo()
    job = tick_demo_generation_job(job_id)
    if job.get("error"):
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Unknown job"}})
    return job


@router.get("/catalog")
async def demo_catalog(
    industry: str = "Restaurant",
    city: str = "Dhaka",
    limit: int = 40,
    _: CurrentUser = Depends(get_current_user),
):
    _require_demo()
    return MockDiscoveryAdapter().search(industry=industry, city=city, limit=limit)


@router.post("/ai/message")
async def demo_ai_message(body: DemoMessageBody, _: CurrentUser = Depends(get_current_user)):
    _require_demo()
    biz = {
        "name": body.business_name,
        "category": body.category,
        "city": body.city,
        "review_count": body.review_count,
        "website_url": body.website_url,
    }
    return MockLLMAdapter().personalize(biz, body.service or "websites and online booking")


@router.post("/ai/simulate-reply")
async def demo_simulate_reply(body: DemoReplyBody, _: CurrentUser = Depends(get_current_user)):
    _require_demo()
    return MockLLMAdapter().analyze_reply(intent=body.intent)


@router.post("/billing/set-plan")
async def demo_set_plan(
    body: DemoPlanBody,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """Switch plan without Stripe — demo only."""
    _require_demo()
    org = await db.get(Organization, current.organization_id)
    if not org:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Org not found"}})
    plan = body.plan
    if plan == "free":
        plan = "trial"
    org.plan = plan
    await db.commit()
    usage = {
        "trial": (12, 40),
        "starter": (180, 500),
        "pro": (1240, 5000),
    }.get(plan, (12, 40))
    return {
        "demo_mode": True,
        "plan": plan,
        "leads_used": usage[0],
        "leads_limit": usage[1],
        "message": "Plan updated in demo state (no payment gateway).",
    }


@router.get("/admin/overview")
async def demo_admin_overview(_: CurrentUser = Depends(get_current_user)):
    _require_demo()
    return {
        "demo_mode": True,
        "label": "DEMO DATA",
        "organizations": 128,
        "organizations_active": 121,
        "users": 214,
        "free_users": 160,
        "paid_users": 54,
        "campaigns": 890,
        "leads": 18420,
        "messages_sent": 6230,
        "revenue_mrr_usd": 4280,
        "plans": {"trial": 160, "starter": 38, "pro": 16},
        "sources": {"google_maps": 9200, "google_search": 4100, "facebook": 2800, "osm": 2320},
        "activity": [
            {"action": "campaign.completed", "detail": "Horizon Web Studio · Dhaka restaurants", "when": "2m ago"},
            {"action": "plan.upgraded", "detail": "Delta Digital Agency · trial → pro", "when": "18m ago"},
            {"action": "message.approved", "detail": "Sultans Dine Banani outreach", "when": "25m ago"},
        ],
        "note": "Figures are simulated for buyer walkthrough — not live production metrics.",
    }


@router.get("/billing/mock-checkout")
async def demo_checkout(plan: str = "starter"):
    _require_demo()
    return MockBillingAdapter().checkout_url(plan)
