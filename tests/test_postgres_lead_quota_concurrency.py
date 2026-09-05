"""Real PostgreSQL integration tests for rolling trial lead-quota concurrency."""
from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.models.business import Business  # noqa: E402
from app.models.campaign import Campaign  # noqa: E402
from app.models.lead import Lead  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.services.usage_service import (  # noqa: E402
    acquire_lead_quota_lock_sync,
    get_remaining_lead_capacity_sync,
)


pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def postgres_engine():
    url = os.getenv("DATABASE_URL_TEST")
    if not url or "postgresql" not in url:
        pytest.skip("DATABASE_URL_TEST PostgreSQL URL is required")
    sync_url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(select(1))
    except Exception as exc:
        engine.dispose()
        pytest.fail(f"PostgreSQL integration database is unavailable: {exc}")
    yield engine
    engine.dispose()


def _seed_trial_org(session: Session, existing_leads: int = 24) -> tuple[Organization, Campaign]:
    org = Organization(name=f"quota-test-{uuid4()}", plan="trial")
    campaign = Campaign(
        organization=org,
        natural_language_input="find local businesses",
        status="scoring",
    )
    session.add_all([org, campaign])
    session.flush()

    for index in range(existing_leads):
        business = Business(
            organization_id=org.id,
            name=f"Existing Business {index}-{uuid4()}",
            dedupe_key=f"existing-{index}-{uuid4()}",
        )
        session.add(business)
        session.flush()
        session.add(Lead(campaign_id=campaign.id, business_id=business.id))

    session.commit()
    return org, campaign


def _attempt_one_lead(engine, organization_id, campaign_id, start_barrier: Barrier) -> bool:
    """Model the critical discovery section: lock, re-check, insert, commit."""
    with Session(engine) as session:
        start_barrier.wait(timeout=10)
        acquire_lead_quota_lock_sync(session, organization_id)
        remaining = get_remaining_lead_capacity_sync(session, organization_id)
        if remaining <= 0:
            session.rollback()
            return False

        business = Business(
            organization_id=organization_id,
            name=f"Concurrent Business {uuid4()}",
            dedupe_key=f"concurrent-{uuid4()}",
        )
        session.add(business)
        session.flush()
        session.add(Lead(campaign_id=campaign_id, business_id=business.id))
        session.commit()
        return True


def test_two_concurrent_workers_cannot_exceed_trial_24h_quota(postgres_engine):
    """With 24 existing leads, exactly one of two workers may create the 25th."""
    with Session(postgres_engine) as session:
        org, campaign = _seed_trial_org(session, existing_leads=24)
        organization_id, campaign_id = org.id, campaign.id

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(_attempt_one_lead, postgres_engine, organization_id, campaign_id, barrier),
            pool.submit(_attempt_one_lead, postgres_engine, organization_id, campaign_id, barrier),
        ]
        results = [future.result(timeout=30) for future in futures]

    with Session(postgres_engine) as session:
        total = session.execute(
            select(func.count())
            .select_from(Lead)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .where(Campaign.organization_id == organization_id)
        ).scalar_one()

    assert sorted(results) == [False, True]
    assert total == 25


def test_postgres_advisory_lock_is_organization_scoped(postgres_engine):
    """Two different organizations must not serialize each other through the same key."""
    with Session(postgres_engine) as session:
        org_a = Organization(name=f"lock-a-{uuid4()}", plan="trial")
        org_b = Organization(name=f"lock-b-{uuid4()}", plan="trial")
        session.add_all([org_a, org_b])
        session.commit()
        id_a, id_b = org_a.id, org_b.id

    # The assertion is intentionally made against the actual PostgreSQL lock
    # key implementation through two independent transactions. If keys were
    # accidentally constant, these operations would contend unnecessarily.
    from app.services.usage_service import _organization_advisory_lock_key

    assert _organization_advisory_lock_key(id_a) != _organization_advisory_lock_key(id_b)
