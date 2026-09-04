"""Referral codes & rewards API."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.services.referral_service import get_or_create_referral_code, referral_dashboard

router = APIRouter(prefix="/referrals", tags=["referrals"])


@router.get("/me")
async def my_referral(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    data = await referral_dashboard(
        db, current.organization_id, current.user_id
    )
    await db.commit()
    return data


@router.post("/code")
async def ensure_code(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    row = await get_or_create_referral_code(
        db,
        organization_id=current.organization_id,
        user_id=current.user_id,
    )
    await db.commit()
    return {"code": row.code}
