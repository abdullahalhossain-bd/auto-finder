from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.lead import enrich_lead_read


def test_lead_api_exposes_website_intelligence_and_business_fields():
    lead = SimpleNamespace(
        id=uuid4(),
        campaign_id=uuid4(),
        business_id=uuid4(),
        opportunity_score=82.0,
        score_breakdown={
            "rules": [{"signal": "weak_website", "points": 25}],
            "website_intelligence": {
                "schema_version": 2,
                "quality_score": 55,
                "weak_reasons": ["no_cta"],
                "booking_vendor": None,
                "seo": {"missing_description": True},
            },
        },
        stage="new",
        confidence_summary={"website": "verified"},
        notes=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        business=SimpleNamespace(
            name="Acme Dental",
            category="Dentist",
            phone="+123456789",
            website_url="https://acme.example",
            source="osm",
            rating=4.8,
            review_count=120,
            address="123 Main St, Austin, TX",
            source_data={"city": "Austin"},
            contacts=[],
        ),
    )

    data = enrich_lead_read(lead)

    assert data.business_name == "Acme Dental"
    assert data.business_city == "Austin"
    assert data.website_url == "https://acme.example"
    assert data.review_count == 120
    assert data.score_tier == "hot"
    assert data.score_tier_label == "Hot Opportunity"
    assert data.score_breakdown["website_intelligence"]["quality_score"] == 55
    assert data.score_breakdown["website_intelligence"]["weak_reasons"] == ["no_cta"]
