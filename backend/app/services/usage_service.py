"""
Monthly usage counters write-path (usage table).

Free stack only — Postgres row upsert, no paid analytics.
Free/trial lead quota is enforced from actual Lead.created_at rows in a
rolling 24-hour window before discovery creates leads. Paid plans keep the
monthly usage-counter enforcement at this write boundary.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.usage import Usage
from app.models.organization import Organization
from app.services.plan_limits import PlanLimitExceeded, get_plan_caps, normalize_plan

logger = get_logger(__name__)

CounterName = Literal[
    "campaigns_count",
    "leads_count",
    "messages_sent_count",
    "llm_calls_count",
]


def current_period(now: Optional[datetime] = None) -> str:
    dt = now or datetime.now(timezone.utc)
    return f"{dt.year:04d}-{dt.month:02d}"


def _bump(row: Usage, counter: CounterName, amount: int) -> None:
    setattr(row, counter, int(getattr(row, counter) or 0) + amount)


def _organization_advisory_lock_key(organization_id: UUID) -> int:
    """Stable signed 64-bit PostgreSQL advisory-lock key for an organization."""
    digest = hashlib.blake2b(str(organization_id).encode("ascii"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=True)


def acquire_lead_quota_lock_sync(session: Session, organization_id: UUID) -> None:
    """Serialize lead-quota check + lead inserts for one organization.

    The lock is transaction-scoped and therefore releases automatically on
    commit/rollback. It intentionally lives in the same transaction as the
    discovery lead inserts, preventing two concurrent workers from both seeing
    the same remaining rolling-24h capacity and exceeding the free quota.
    """
    key = _organization_advisory_lock_key(organization_id)
    session.execute(text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": key})


def _trial_leads_used_sync(session: Session, organization_id: UUID) -> int:
    from app.models.campaign import Campaign
    from app.models.lead import Lead
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return int(session.execute(
        select(func.count()).select_from(Lead).join(Campaign, Lead.campaign_id == Campaign.id).where(
            Campaign.organization_id == organization_id, Lead.created_at >= since
        )
    ).scalar_one())


async def _trial_leads_used_async(session: AsyncSession, organization_id: UUID) -> int:
    from app.models.campaign import Campaign
    from app.models.lead import Lead
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return int((await session.execute(
        select(func.count()).select_from(Lead).join(Campaign, Lead.campaign_id == Campaign.id).where(
            Campaign.organization_id == organization_id, Lead.created_at >= since
        )
    )).scalar_one())


def get_remaining_lead_capacity_sync(session: Session, organization_id: UUID, *, period: Optional[str] = None) -> int:
    """Return remaining lead capacity using the plan's actual quota window."""
    org = session.get(Organization, organization_id)
    if org is None:
        raise PlanLimitExceeded("ORG_NOT_FOUND", "Organization not found")
    plan = normalize_plan(org.plan)
    caps = get_plan_caps(plan)
    if plan == "trial":
        return max(0, int(caps["max_leads_per_24h"]) - _trial_leads_used_sync(session, organization_id))
    period = period or current_period()
    row = session.execute(select(Usage).where(Usage.organization_id == organization_id, Usage.period == period)).scalars().first()
    used = int(row.leads_count or 0) if row else 0
    return max(0, int(caps["max_leads_per_month"]) - used)


def _assert_lead_increment_allowed_sync(session: Session, organization_id: UUID, current_count: int, amount: int) -> None:
    if amount <= 0:
        return
    org = session.get(Organization, organization_id)
    if org is None:
        raise PlanLimitExceeded("ORG_NOT_FOUND", "Organization not found")
    plan = normalize_plan(org.plan)
    caps = get_plan_caps(plan)
    # Trial quota is checked before discovery writes and decremented in-memory
    # per created lead. Do not re-count those same pending leads here.
    if plan == "trial":
        return
    cap = int(caps["max_leads_per_month"])
    if current_count + amount > cap:
        raise PlanLimitExceeded("LEAD_CAP_REACHED", f"Your {plan} plan allows {cap} leads per month.")


async def _assert_lead_increment_allowed_async(session: AsyncSession, organization_id: UUID, current_count: int, amount: int) -> None:
    if amount <= 0:
        return
    org = await session.get(Organization, organization_id)
    if org is None:
        raise PlanLimitExceeded("ORG_NOT_FOUND", "Organization not found")
    plan = normalize_plan(org.plan)
    caps = get_plan_caps(plan)
    if plan == "trial":
        return
    cap = int(caps["max_leads_per_month"])
    if current_count + amount > cap:
        raise PlanLimitExceeded("LEAD_CAP_REACHED", f"Your {plan} plan allows {cap} leads per month.")


async def increment_usage_async(session: AsyncSession, organization_id: UUID, counter: CounterName, amount: int = 1, *, period: Optional[str] = None) -> None:
    if amount <= 0:
        return
    period = period or current_period()
    result = await session.execute(select(Usage).where(Usage.organization_id == organization_id, Usage.period == period))
    row = result.scalar_one_or_none()
    if row is None:
        row = Usage(organization_id=organization_id, period=period, campaigns_count=0, leads_count=0, messages_sent_count=0, llm_calls_count=0)
        session.add(row)
        await session.flush()
    if counter == "leads_count":
        await _assert_lead_increment_allowed_async(session, organization_id, int(row.leads_count or 0), amount)
    _bump(row, counter, amount)
    await session.flush()


def increment_usage_sync(session: Session, organization_id: UUID, counter: CounterName, amount: int = 1, *, period: Optional[str] = None) -> None:
    if amount <= 0:
        return
    period = period or current_period()
    row = session.execute(select(Usage).where(Usage.organization_id == organization_id, Usage.period == period)).scalars().first()
    if row is None:
        row = Usage(organization_id=organization_id, period=period, campaigns_count=0, leads_count=0, messages_sent_count=0, llm_calls_count=0)
        session.add(row)
        session.flush()
    if counter == "leads_count":
        _assert_lead_increment_allowed_sync(session, organization_id, int(row.leads_count or 0), amount)
    _bump(row, counter, amount)
    session.flush()


async def get_usage_row_async(session: AsyncSession, organization_id: UUID, period: Optional[str] = None) -> Optional[Usage]:
    period = period or current_period()
    result = await session.execute(select(Usage).where(Usage.organization_id == organization_id, Usage.period == period))
    return result.scalar_one_or_none()
