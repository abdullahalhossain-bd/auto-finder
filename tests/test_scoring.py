"""Rule-based scoring unit tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.scoring_service import ScoringService  # noqa: E402


def test_no_website_scores_high():
    s = ScoringService()
    result = s.calculate_score(
        has_website=False,
        website_weak=False,
        review_count=None,
        has_booking=False,
        confidence={},
    )
    assert result["opportunity_score"] >= 40
    assert any(b["signal"] == "no_website" for b in result["breakdown"])


def test_reviews_without_booking():
    s = ScoringService()
    result = s.calculate_score(
        has_website=True,
        website_weak=False,
        review_count=60,
        has_booking=False,
        confidence={},
    )
    assert result["opportunity_score"] >= 35
    assert any("no_booking" in b["signal"] for b in result["breakdown"])


def test_missing_reviews_not_penalized():
    s = ScoringService()
    result = s.calculate_score(
        has_website=True,
        website_weak=False,
        review_count=None,
        has_booking=True,
        confidence={},
    )
    assert result["opportunity_score"] == 0


def test_score_capped_at_100():
    s = ScoringService()
    result = s.calculate_score(
        has_website=False,
        website_weak=True,
        review_count=100,
        has_booking=False,
        confidence={"phone": "verified"},
    )
    assert result["opportunity_score"] <= 100
