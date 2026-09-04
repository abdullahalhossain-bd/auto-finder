"""Regression tests for hard monthly lead-cap enforcement."""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.plan_limits import PlanLimitExceeded, get_plan_caps  # noqa: E402
from app.services.usage_service import (  # noqa: E402
    _assert_lead_increment_allowed_async,
    _assert_lead_increment_allowed_sync,
)


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


def test_trial_allows_increment_inside_cap():
    session = FakeSyncSession("trial")
    _assert_lead_increment_allowed_sync(session, uuid4(), 24, 1)


def test_trial_blocks_increment_over_cap():
    session = FakeSyncSession("trial")
    try:
        _assert_lead_increment_allowed_sync(session, uuid4(), 25, 1)
    except PlanLimitExceeded as exc:
        assert exc.code == "LEAD_CAP_REACHED"
    else:
        raise AssertionError("Expected LEAD_CAP_REACHED")


def test_starter_and_pro_caps_are_higher():
    assert get_plan_caps("starter")["max_leads_per_month"] == 500
    assert get_plan_caps("pro")["max_leads_per_month"] == 5000


def test_async_guard_blocks_over_cap():
    session = FakeAsyncSession("starter")
    try:
        asyncio.run(_assert_lead_increment_allowed_async(session, uuid4(), 500, 1))
    except PlanLimitExceeded as exc:
        assert exc.code == "LEAD_CAP_REACHED"
    else:
        raise AssertionError("Expected LEAD_CAP_REACHED")
