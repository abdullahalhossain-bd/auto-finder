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

    def get(self, model, organization_id):
        return self.org


class FakeAsyncSession:
    def __init__(self, plan):
        self.org = SimpleNamespace(plan=plan)

    async def get(self, model, organization_id):
        return self.org


def test_trial_allows_increment_inside_rolling_24h_cap(monkeypatch):
    session = FakeSyncSession("trial")
    monkeypatch.setattr(usage_service, "_trial_leads_used_sync", lambda *_: 24)
    usage_service._assert_lead_increment_allowed_sync(session, uuid4(), 999, 1)


def test_trial_blocks_increment_over_rolling_24h_cap(monkeypatch):
    session = FakeSyncSession("trial")
    monkeypatch.setattr(usage_service, "_trial_leads_used_sync", lambda *_: 25)
    try:
        usage_service._assert_lead_increment_allowed_sync(session, uuid4(), 0, 1)
    except PlanLimitExceeded as exc:
        assert exc.code == "LEAD_CAP_REACHED"
        assert "24 hours" in exc.message
    else:
        raise AssertionError("Expected LEAD_CAP_REACHED")


def test_trial_capacity_is_independent_of_monthly_usage_counter(monkeypatch):
    session = FakeSyncSession("trial")
    monkeypatch.setattr(usage_service, "_trial_leads_used_sync", lambda *_: 2)
    usage_service._assert_lead_increment_allowed_sync(session, uuid4(), 1000, 23)


def test_starter_and_pro_caps_are_monthly():
    assert get_plan_caps("starter")["max_leads_per_month"] == 500
    assert get_plan_caps("pro")["max_leads_per_month"] == 5000
    assert "max_leads_per_24h" not in get_plan_caps("starter")
    assert "max_leads_per_24h" not in get_plan_caps("pro")


def test_async_trial_guard_uses_rolling_24h(monkeypatch):
    session = FakeAsyncSession("trial")
    async def fake_used(*_):
        return 25
    monkeypatch.setattr(usage_service, "_trial_leads_used_async", fake_used)
    try:
        asyncio.run(usage_service._assert_lead_increment_allowed_async(session, uuid4(), 0, 1))
    except PlanLimitExceeded as exc:
        assert exc.code == "LEAD_CAP_REACHED"
    else:
        raise AssertionError("Expected LEAD_CAP_REACHED")


def test_async_starter_guard_blocks_monthly_cap():
    session = FakeAsyncSession("starter")
    try:
        asyncio.run(usage_service._assert_lead_increment_allowed_async(session, uuid4(), 500, 1))
    except PlanLimitExceeded as exc:
        assert exc.code == "LEAD_CAP_REACHED"
    else:
        raise AssertionError("Expected LEAD_CAP_REACHED")
