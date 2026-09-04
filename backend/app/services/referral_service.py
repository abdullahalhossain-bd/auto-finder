"""
Referral / invite rewards.

Signup with a code → invitee + inviter get bonus lead credits.
When invitee first becomes paid (starter/pro) → inviter gets larger bonus once.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging_config import log_event
from app.models.referral import OrganizationCredit, ReferralCode, ReferralRedemption


def _reward_signup_inviter() -> int:
    return int(getattr(get_settings(), "REFERRAL_SIGNUP_INVITER_LEADS", 15) or 15)


def _reward_signup_invitee() -> int:
    return int(getattr(get_settings(), "REFERRAL_SIGNUP_INVITEE_LEADS", 10) or 10)


def _reward_paid_inviter() -> int:
    return int(getattr(get_settings(), "REFERRAL_PAID_INVITER_LEADS", 40) or 40)


def _gen_code() -> str:
    # Short human-shareable code
    return secrets.token_urlsafe(6).upper().replace("-", "").replace("_", "")[:10]


async def get_or_create_referral_code(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
) -> ReferralCode:
    result = await session.execute(
        select(ReferralCode).where(ReferralCode.organization_id == organization_id)
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    for _ in range(8):
        code = _gen_code()
        exists = await session.execute(
            select(ReferralCode).where(ReferralCode.code == code)
        )
        if exists.scalar_one_or_none() is None:
            row = ReferralCode(
                organization_id=organization_id,
                owner_user_id=user_id,
                code=code,
            )
            session.add(row)
            await session.flush()
            return row
    raise RuntimeError("Could not allocate referral code")


async def get_credits(session: AsyncSession, organization_id: UUID) -> OrganizationCredit:
    result = await session.execute(
        select(OrganizationCredit).where(
            OrganizationCredit.organization_id == organization_id
        )
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    row = OrganizationCredit(
        organization_id=organization_id, bonus_leads=0, bonus_campaigns=0
    )
    session.add(row)
    await session.flush()
    return row


async def add_bonus_leads(
    session: AsyncSession, organization_id: UUID, amount: int
) -> OrganizationCredit:
    if amount <= 0:
        return await get_credits(session, organization_id)
    credits = await get_credits(session, organization_id)
    credits.bonus_leads = int(credits.bonus_leads or 0) + amount
    await session.flush()
    return credits


async def effective_lead_limit(
    session: AsyncSession, organization_id: UUID, base_limit: int
) -> int:
    credits = await get_credits(session, organization_id)
    return int(base_limit) + int(credits.bonus_leads or 0)


async def apply_referral_on_register(
    session: AsyncSession,
    *,
    referral_code: str,
    new_organization_id: UUID,
    new_user_id: UUID,
) -> Optional[dict[str, Any]]:
    code = (referral_code or "").strip().upper()
    if not code:
        return None

    result = await session.execute(
        select(ReferralCode).where(ReferralCode.code == code)
    )
    ref = result.scalar_one_or_none()
    if ref is None:
        return {"ok": False, "reason": "invalid_code"}

    if ref.organization_id == new_organization_id:
        return {"ok": False, "reason": "self_referral"}

    # already redeemed for this org?
    existing = await session.execute(
        select(ReferralRedemption).where(
            ReferralRedemption.referred_organization_id == new_organization_id
        )
    )
    if existing.scalar_one_or_none():
        return {"ok": False, "reason": "already_redeemed"}

    inviter_amt = _reward_signup_inviter()
    invitee_amt = _reward_signup_invitee()

    redemption = ReferralRedemption(
        referral_code_id=ref.id,
        referrer_organization_id=ref.organization_id,
        referred_organization_id=new_organization_id,
        referred_user_id=new_user_id,
        status="signup",
        inviter_reward_leads=inviter_amt,
        invitee_reward_leads=invitee_amt,
        paid_reward_granted=False,
    )
    session.add(redemption)
    ref.signup_count = int(ref.signup_count or 0) + 1

    await add_bonus_leads(session, ref.organization_id, inviter_amt)
    await add_bonus_leads(session, new_organization_id, invitee_amt)

    log_event(
        "referral.signup_reward",
        referrer_org=str(ref.organization_id),
        referred_org=str(new_organization_id),
        code=code,
        inviter_leads=inviter_amt,
        invitee_leads=invitee_amt,
    )
    return {
        "ok": True,
        "code": code,
        "inviter_reward_leads": inviter_amt,
        "invitee_reward_leads": invitee_amt,
    }


async def grant_paid_referral_reward(
    session: AsyncSession, referred_organization_id: UUID
) -> Optional[dict[str, Any]]:
    """Call when an org first becomes paid (starter/pro active)."""
    result = await session.execute(
        select(ReferralRedemption).where(
            ReferralRedemption.referred_organization_id == referred_organization_id
        )
    )
    red = result.scalar_one_or_none()
    if red is None or red.paid_reward_granted:
        return None

    amount = _reward_paid_inviter()
    await add_bonus_leads(session, red.referrer_organization_id, amount)
    red.paid_reward_granted = True
    red.paid_at = datetime.now(timezone.utc)
    red.status = "paid"

    ref = await session.get(ReferralCode, red.referral_code_id)
    if ref:
        ref.successful_referrals = int(ref.successful_referrals or 0) + 1

    log_event(
        "referral.paid_reward",
        referrer_org=str(red.referrer_organization_id),
        referred_org=str(referred_organization_id),
        leads=amount,
    )
    return {"ok": True, "inviter_reward_leads": amount}


async def referral_dashboard(
    session: AsyncSession, organization_id: UUID, user_id: UUID
) -> dict[str, Any]:
    code_row = await get_or_create_referral_code(
        session, organization_id=organization_id, user_id=user_id
    )
    credits = await get_credits(session, organization_id)
    settings = get_settings()
    public = (getattr(settings, "PUBLIC_APP_URL", None) or "http://localhost:5173").rstrip("/")
    # Prefer frontend URL for share link
    share_base = public.replace(":8000", ":5173") if ":8000" in public else public

    redemptions = (
        await session.execute(
            select(ReferralRedemption)
            .where(ReferralRedemption.referrer_organization_id == organization_id)
            .order_by(ReferralRedemption.created_at.desc())
            .limit(50)
        )
    ).scalars().all()

    return {
        "code": code_row.code,
        "share_url": f"{share_base}/register?ref={code_row.code}",
        "signup_count": int(code_row.signup_count or 0),
        "successful_paid_referrals": int(code_row.successful_referrals or 0),
        "bonus_leads": int(credits.bonus_leads or 0),
        "bonus_campaigns": int(credits.bonus_campaigns or 0),
        "rewards": {
            "signup_inviter_leads": _reward_signup_inviter(),
            "signup_invitee_leads": _reward_signup_invitee(),
            "paid_inviter_leads": _reward_paid_inviter(),
        },
        "history": [
            {
                "status": r.status,
                "inviter_reward_leads": r.inviter_reward_leads,
                "invitee_reward_leads": r.invitee_reward_leads,
                "paid_reward_granted": r.paid_reward_granted,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in redemptions
        ],
    }
