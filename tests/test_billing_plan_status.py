"""Subscription status blocks — pure logic helpers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.plan_limits import PLAN_CAPS, get_plan_caps  # noqa: E402


def test_paid_plans_have_higher_caps():
    assert get_plan_caps("pro")["max_leads_per_month"] > get_plan_caps("starter")["max_leads_per_month"]
    assert get_plan_caps("starter")["max_campaigns_per_month"] > get_plan_caps("trial")["max_campaigns_per_month"]


def test_plan_caps_keys_stable():
    for plan in ("trial", "starter", "pro"):
        caps = get_plan_caps(plan)
        assert "max_campaigns_per_month" in caps
        assert "max_leads_per_month" in caps
