"""Unit tests for business deduplication — no DB required."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.dedupe import (  # noqa: E402
    compute_dedupe_key,
    dedupe_record_list,
    merge_business_records,
    normalize_name,
    normalize_phone,
)


def test_normalize_name_strips_noise():
    assert "barber" in normalize_name("Joe's Barber Shop LLC")
    assert normalize_name("  Café  ") == normalize_name("Cafe")


def test_normalize_phone_last_digits():
    assert normalize_phone("+48 12 345-67-89")[-9:] == normalize_phone("123456789")[-9:]


def test_dedupe_key_same_place():
    k1 = compute_dedupe_key("Joe Barber", 50.0647, 19.9450, None)
    k2 = compute_dedupe_key("Joe Barber", 50.0648, 19.9451, "+48111")
    assert k1 == k2


def test_dedupe_record_list_merges_reviews():
    rows = dedupe_record_list(
        [
            {"name": "Joe Barber", "latitude": 50.06, "longitude": 19.94},
            {
                "name": "Joe Barber",
                "latitude": 50.0601,
                "longitude": 19.9401,
                "review_count": 55,
                "rating": 4.5,
            },
            {"name": "Other", "latitude": 51.0, "longitude": 20.0},
        ]
    )
    assert len(rows) == 2
    joe = next(r for r in rows if "joe" in (r.get("name") or "").lower())
    assert joe.get("review_count") == 55


def test_merge_prefers_filled_fields():
    a = {"name": "A", "phone": None, "website_url": "https://a.test"}
    b = {"name": "A", "phone": "+100", "website_url": None, "review_count": 10}
    m = merge_business_records(a, b)
    assert m["phone"] == "+100"
    assert m["website_url"] == "https://a.test"
    assert m["review_count"] == 10
