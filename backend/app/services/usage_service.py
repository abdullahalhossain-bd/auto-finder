"""
Monthly usage counters write-path (usage table).

Free stack only — Postgres row upsert, no paid analytics.
Lead quota is enforced again at this write boundary so discovery workers
cannot commit more leads than the organization's plan allows.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import select
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


def _assert_lead_increment_allowed_sync(
    session: Session,
    organization_id: UUID,
    current_count: int,
    amount: int,
) -> None:
    if amount <= 0:
        return
    org = session.get(Organization, organization_id)
    if org is None:
        raise PlanLimitExceeded("ORG_NOT_FOUND", "Organization not found")
    plan = normalize_plan(org.plan)
    cap = int(get_plan_caps(plan)["max_leads_per_month"])
    if current_count + amount > cap:
        raise PlanLimitExceeded(
            "LEAD_CAP_REACHED",
            f"Your {plan} plan allows {cap} leads per month.",
        )


async def _assert_lead_increment_allowed_async(
    session: AsyncSession,
    organization_id: UUID,
    current_count: int,
    amount: int,
) -> None:
    if amount <= 0:
        return
    org = await session.get(Organization, organization_id)
    if org is None:
        raise PlanLimitExceeded("ORG_NOT_FOUND", "Organization not found")
    plan = normalize_plan(org.plan)
    cap = int(get_plan_caps(plan)["max_leads_per_month"])
    if current_count + amount > cap:
        raise PlanLimitExceeded(
            "LEAD_CAP_REACHED",
            f"Your {plan} plan allows {cap} leads per month.",
        )


async def increment_usage_async(
    session: AsyncSession,
    organization_id: UUID,
    counter: CounterName,
    amount: int = 1,
    *,
    period: Optional[str] = None,
) -> None:
    if amount <= 0:
        return
    period = period or current_period()
    result = await session.execute(
        select(Usage).where(
            Usage.organization_id == organization_id,
            Usage.period == period,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = Usage(
            organization_id=organization_id,
            period=period,
            campaigns_count=0,
            leads_count=0,
            messages_sent_count=0,
            llm_calls_count=0,
        )
        session.add(row)
        await session.flush()
    if counter == "leads_count":
        await _assert_lead_increment_allowed_async(
            session, organization_id, int(row.leads_count or 0), amount
        )
    _bump(row, counter, amount)
    await session.flush()


def increment_usage_sync(
    session: Session,
    organization_id: UUID,
    counter: CounterName,
    amount: int = 1,
    *,
    period: Optional[str] = None,
) -> None:
    if amount <= 0:
        return
    period = period or current_period()
    row = (
        session.execute(
            select(Usage).where(
                Usage.organization_id == organization_id,
                Usage.period == period,
            )
        )
        .scalars()
        .first()
    )
    if row is None:
        row = Usage(
            organization_id=organization_id,
            period=period,
            campaigns_count=0,
            leads_count=0,
            messages_sent_count=0,
            llm_calls_count=0,
        )
        session.add(row)
        session.flush()
    if counter == "leads_count":
        _assert_lead_increment_allowed_sync(
            session, organization_id, int(row.leads_count or 0), amount
        )
    _bump(row, counter, amount)
    session.flush()


async def get_usage_row_async(
    session: AsyncSession, organization_id: UUID, period: Optional[str] = None
) -> Optional[Usage]:
    period = period or current_period()
    result = await session.execute(
        select(Usage).where(
            Usage.organization_id == organization_id,
            Usage.period == period,
        )
    )
    return result.scalar_one_or_none()
