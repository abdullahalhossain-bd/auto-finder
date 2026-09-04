"""Plan cap table is defined and consistent."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.plan_limits import PLAN_CAPS, get_plan_caps  # noqa: E402


def test_trial_stricter_than_starter():
    trial = get_plan_caps("trial")
    starter = get_plan_caps("starter")
    assert trial["max_campaigns_per_month"] <= starter["max_campaigns_per_month"]
    assert trial["max_leads_per_month"] <= starter["max_leads_per_month"]


def test_unknown_plan_defaults_trial():
    assert get_plan_caps("nope") == PLAN_CAPS["trial"]
