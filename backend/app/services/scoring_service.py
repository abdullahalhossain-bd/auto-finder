"""
Lead Scoring Service
- 100% rule-based
- LLM never modifies the score
"""

from typing import Dict, Any, Optional


class ScoringService:
    """Calculate Opportunity Score using deterministic rules."""

    def calculate_score(
        self,
        has_website: bool,
        website_weak: bool,
        review_count: Optional[int],
        has_booking: bool,
        confidence: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Returns score + breakdown.
        Only uses Verified / Likely signals.
        """
        score = 0.0
        breakdown = []

        # Signal 1: No or weak website
        if not has_website:
            score += 40
            breakdown.append({"signal": "no_website", "points": 40})
        elif website_weak:
            score += 25
            breakdown.append({"signal": "weak_website", "points": 25})

        # Signal 2: High reviews + no booking
        if review_count and review_count >= 50 and not has_booking:
            score += 35
            breakdown.append({"signal": "high_reviews_no_booking", "points": 35})
        elif review_count and review_count >= 20 and not has_booking:
            score += 20
            breakdown.append({"signal": "medium_reviews_no_booking", "points": 20})

        # Small bonus for data confidence
        if confidence.get("phone") == "verified":
            score += 5
            breakdown.append({"signal": "verified_phone", "points": 5})

        final = min(score, 100)
        from app.services.plan_limits import score_tier

        tier = score_tier(final)
        return {
            "opportunity_score": final,
            "breakdown": breakdown,
            "tier": tier["tier"],
            "tier_label": tier["label"],
        }
