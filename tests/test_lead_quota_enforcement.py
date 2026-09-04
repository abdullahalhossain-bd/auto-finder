"""Regression tests for lead-cap enforcement and free rolling-24h quota."""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.plan_limits import PlanLimitExceeded, get_plan_caps  # noqa: E402
from app.services import usage_service  # noqa: E402


class FakeSyncSession:
    def __init__(self, plan):
        self.org = SimpleNamespace(plan=plan)
        self.executed = []

    def get(self, model, organization_id):
        return self.org

    def execute(self, statement, params=None):
        self.executed.append((statement, params))
        return SimpleNamespace()


class FakeAsyncSession:
    def __init__(self, plan):
        self.org = SimpleNamespace(plan=plan)

    async def get(self, model, organization_id):
        return self.org


def test_trial_remaining_capacity_uses_rolling_24h(monkeypatch):
    session = FakeSyncSession("trial")
    monkeypatch.setattr(usage_service, "_trial_leads_used_sync", lambda *_: 24)
    assert usage_service.get_remaining_lead_capacity_sync(session, uuid4()) == 1


def test_trial_remaining_capacity_is_zero_at_25(monkeypatch):
    session = FakeSyncSession("trial")
    monkeypatch.setattr(usage_service, "_trial_leads_used_sync", lambda *_: 25)
    assert usage_service.get_remaining_lead_capacity_sync(session, uuid4()) == 0


def test_trial_usage_increment_does_not_double_count_pending_leads():
    """The discovery transaction checks quota before adding pending Lead rows."""
    session = FakeSyncSession("trial")
    # This guard is intentionally a no-op for trial because discovery already
    # reserved the slots in-memory and will commit the new Lead rows together.
    usage_service._assert_lead_increment_allowed_sync(session, uuid4(), 25, 1)


def test_starter_and_pro_caps_are_monthly():
    assert get_plan_caps("starter")["max_leads_per_month"] == 500
    assert get_plan_caps("pro")["max_leads_per_month"] == 5000
    assert "max_leads_per_24h" not in get_plan_caps("starter")
    assert "max_leads_per_24h" not in get_plan_caps("pro")


def test_async_trial_guard_is_noop_after_discovery_reservation():
    session = FakeAsyncSession("trial")
    asyncio.run(usage_service._assert_lead_increment_allowed_async(session, uuid4(), 25, 1))


def test_async_starter_guard_blocks_monthly_cap():
    session = FakeAsyncSession("starter")
    try:
        asyncio.run(usage_service._assert_lead_increment_allowed_async(session, uuid4(), 500, 1))
    except PlanLimitExceeded as exc:
        assert exc.code == "LEAD_CAP_REACHED"
    else:
        raise AssertionError("Expected LEAD_CAP_REACHED")


def test_advisory_lock_is_transaction_scoped_and_org_specific():
    session = FakeSyncSession("trial")
    organization_id = uuid4()
    usage_service.acquire_lead_quota_lock_sync(session, organization_id)
    assert len(session.executed) == 1
    statement, params = session.executed[0]
    assert "pg_advisory_xact_lock" in str(statement)
    assert isinstance(params["lock_key"], int)
    assert -(2**63) <= params["lock_key"] <= 2**63 - 1


def test_advisory_lock_key_is_stable():
    organization_id = uuid4()
    assert usage_service._organization_advisory_lock_key(organization_id) == usage_service._organization_advisory_lock_key(organization_id)
